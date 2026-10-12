import java.io.*;
import java.net.*;
import java.nio.ByteBuffer;
import java.nio.channels.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.jar.*;
import org.prosperomc.zip.ZipChannels;
import org.prosperomc.zip.ArchiveFile;

/** Exercise real ZipFS mounts, normal JAR URLs, eviction, writes and concurrency. */
public class ZipFsChannelsFixture {
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[0]);Files.createDirectories(root);
        List<FileSystem> mounts=new ArrayList<>();List<JarFile> jars=new ArrayList<>(),urlJars=new ArrayList<>();
        for(int i=0;i<240;i++) {
            Path jar=root.resolve("mod-"+i+".jar");
            try(JarOutputStream output=new JarOutputStream(Files.newOutputStream(jar))) {
                output.putNextEntry(new JarEntry("assets/data-"+i+".txt"));
                output.write(("resource-"+i).getBytes("UTF-8"));output.closeEntry();
                output.putNextEntry(new JarEntry("empty.txt"));output.closeEntry();
            }
            mounts.add(FileSystems.newFileSystem(jar,(ClassLoader)null));
            jars.add(new JarFile(jar.toFile()));
            JarURLConnection connection=(JarURLConnection)new URL("jar:"+jar.toUri()+"!/assets/data-"+i+".txt").openConnection();
            urlJars.add(connection.getJarFile());
            try(InputStream input=connection.getInputStream()) {
                if(input.read()!=114)throw new AssertionError("JAR URL content changed");
            }
            if(ZipChannels.statistics()[0]>16)throw new AssertionError("ZIP backing limit exceeded");
            if(ArchiveFile.statistics()[0]>16)throw new AssertionError("Cached JAR backing limit exceeded");
        }
        if(ZipChannels.statistics()[0]!=16||ZipChannels.statistics()[3]<224)throw new AssertionError("No actual eviction");
        if(ArchiveFile.statistics()[0]!=16||ArchiveFile.statistics()[3]<224)throw new AssertionError("No actual JAR eviction");
        ExecutorService pool=Executors.newFixedThreadPool(8);List<Future<?>> tasks=new ArrayList<>();
        for(int t=0;t<8;t++) {
            final int offset=t;
            tasks.add(pool.submit(()-> {
                try {
                    for(int k=0;k<480;k++) {
                        int i=(k*37+offset)%240;FileSystem fs=mounts.get(i);
                        String actual=new String(Files.readAllBytes(fs.getPath("/assets/data-"+i+".txt")),"UTF-8");
                        if(!actual.equals("resource-"+i))throw new AssertionError(actual);
                        if(Files.readAllBytes(fs.getPath("/empty.txt")).length!=0)throw new AssertionError();
                        try(InputStream input=jars.get(i).getInputStream(jars.get(i).getJarEntry("assets/data-"+i+".txt"))) {
                            ByteArrayOutputStream data=new ByteArrayOutputStream();int value;
                            while((value=input.read())>=0)data.write(value);
                            if(!new String(data.toByteArray(),"UTF-8").equals("resource-"+i))throw new AssertionError("Concurrent cached JAR read changed");
                        }
                    }
                }catch(Exception error){throw new RuntimeException(error);}
            }));
        }
        for(Future<?> task:tasks)task.get();pool.shutdown();
        // Windows JAR readers deny replacing their open file. Close those
        // readers before exercising ZipFS's ordinary archive replacement.
        for(JarFile jar:jars)jar.close();for(JarFile jar:urlJars)jar.close();
        if(ArchiveFile.statistics()[0]!=0)throw new AssertionError("Closed JARs retained backing files");
        // Writable ZipFS still rebuilds its archive using normal write channels.
        Files.write(mounts.get(0).getPath("/added.txt"),"saved".getBytes("UTF-8"));
        for(FileSystem fs:mounts)fs.close();
        if(ZipChannels.statistics()[0]!=0)throw new AssertionError("Closed mounts retained backing channels");
        try(FileSystem fs=FileSystems.newFileSystem(root.resolve("mod-0.jar"),(ClassLoader)null)) {
            if(!new String(Files.readAllBytes(fs.getPath("/added.txt")),"UTF-8").equals("saved"))throw new AssertionError("ZIP save/reopen failed");
        }
        Path plain=root.resolve("raw.zip");Files.write(plain,new byte[]{1,2,3,4});
        SeekableByteChannel old=ZipChannels.newByteChannel(plain,StandardOpenOption.READ);
        old.position(2);
        List<SeekableByteChannel> channels=new ArrayList<>();
        for(int i=0;i<20;i++)channels.add(ZipChannels.newByteChannel(root.resolve("mod-"+i+".jar"),StandardOpenOption.READ));
        ByteBuffer byteBuffer=ByteBuffer.allocate(1);old.read(byteBuffer);
        if(byteBuffer.get(0)!=3||old.position()!=3)throw new AssertionError("Eviction lost logical position");
        try {old.write(ByteBuffer.allocate(0));throw new AssertionError();}catch(NonWritableChannelException expected){}
        old.close();try{old.read(ByteBuffer.allocate(1));throw new AssertionError();}catch(ClosedChannelException expected){}
        SeekableByteChannel changed=ZipChannels.newByteChannel(plain,StandardOpenOption.READ);
        for(int i=20;i<40;i++)channels.add(ZipChannels.newByteChannel(root.resolve("mod-"+i+".jar"),StandardOpenOption.READ));
        Files.write(plain,new byte[]{9,8,7,6,5});
        try{changed.read(ByteBuffer.allocate(1));throw new AssertionError("Read silently switched to a changed archive");}catch(IOException expected){}
        changed.close();for(SeekableByteChannel channel:channels)channel.close();
        SeekableByteChannel interrupted=ZipChannels.newByteChannel(plain,StandardOpenOption.READ);
        Thread.currentThread().interrupt();
        try {interrupted.read(ByteBuffer.allocate(1));throw new AssertionError("Interrupted read succeeded");}
        catch(ClosedByInterruptException expected) {if(interrupted.isOpen())throw new AssertionError("Interrupted backing stayed open");}
        finally {Thread.interrupted();interrupted.close();}
        if(ZipChannels.statistics()[0]!=0)throw new AssertionError("Channel leak");
        // OPEN_DELETE stays on the JDK's original backing and removal path.
        Path delete=root.resolve("delete.jar");Files.copy(root.resolve("mod-1.jar"),delete);
        try(java.util.zip.ZipFile zip=new java.util.zip.ZipFile(delete.toFile(),java.util.zip.ZipFile.OPEN_READ|java.util.zip.ZipFile.OPEN_DELETE)) {
            if(zip.getEntry("empty.txt")==null)throw new AssertionError("OPEN_DELETE content changed");
        }
        if(Files.exists(delete))throw new AssertionError("OPEN_DELETE did not remove its archive");
        // The pooled subclass must preserve seek/readFully and reject changed
        // files without touching ordinary writable RandomAccessFile instances.
        ArchiveFile archive=new ArchiveFile(plain.toFile(),"r");archive.seek(2);
        List<ArchiveFile> archiveFiles=new ArrayList<>();
        for(int i=0;i<24;i++){ArchiveFile other=new ArchiveFile(root.resolve("mod-"+i+".jar").toFile(),"r");other.length();archiveFiles.add(other);}
        byte[] selected=new byte[2];archive.readFully(selected);
        if(selected[0]!=7||selected[1]!=6||archive.getFilePointer()!=4)throw new AssertionError("JAR pool lost its seek position");
        for(ArchiveFile other:archiveFiles)other.length();
        Files.write(plain,new byte[]{1,2});
        try{archive.read();throw new AssertionError("Changed JAR backing accepted");}catch(IOException expected){}
        archive.close();for(ArchiveFile other:archiveFiles)other.close();
        try(RandomAccessFile writable=new RandomAccessFile(root.resolve("world.dat").toFile(),"rw")){writable.writeLong(42);writable.seek(0);if(writable.readLong()!=42)throw new AssertionError("World write changed");}
        if(ArchiveFile.statistics()[0]!=0)throw new AssertionError("JAR pool leak");
        System.out.println("ZIPFS_CHANNELS_PASS: java="+System.getProperty("java.specification.version")+"; 240 mounts and cached JAR readers; 7680 concurrent reads; 16 ZIP + 16 JAR backing limits; seek/close/changed-file/interrupt guards; OPEN_DELETE; ZIP/world write/save/reopen");
    }
}
