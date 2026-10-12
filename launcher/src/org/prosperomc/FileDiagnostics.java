package org.prosperomc;

import java.io.*;
import java.nio.channels.SeekableByteChannel;
import java.nio.file.*;
import java.nio.file.attribute.DosFileAttributes;
import java.util.*;
import java.util.jar.JarOutputStream;

/** A bounded writable ZIP probe distinguishes Java/Wine access checks from disk permissions. */
final class FileDiagnostics {
    static void probe(Path root) {
        probeOne(root);
        Path dataDrive=Paths.get("P:\\");
        if(root.toString().replace('\\','/').equalsIgnoreCase("Z:/data/ProsperoMC")&&Files.isDirectory(dataDrive))probeOne(dataDrive);
    }
    private static void probeOne(Path root) {
        Path probe=null;
        try {
            Path directory=FilesUtil.safe(root,"cache/file-probe");Files.createDirectories(directory);
            probe=Files.createTempFile(directory,"writable-",".jar");
            try(JarOutputStream zip=new JarOutputStream(Files.newOutputStream(probe))) {zip.flush();}
            boolean writable=Files.isWritable(probe), actual=false;
            try(SeekableByteChannel channel=Files.newByteChannel(probe,StandardOpenOption.WRITE)) {actual=channel.isOpen();}
            String access="allowed", dos="unknown", store="unknown";
            try {probe.getFileSystem().provider().checkAccess(probe,AccessMode.WRITE);}
            catch(IOException|RuntimeException error) {access=error.getClass().getSimpleName()+": "+error.getMessage();frames("write-access",error);}
            try {dos=Boolean.toString(Files.readAttributes(probe,DosFileAttributes.class).isReadOnly());}
            catch(IOException|RuntimeException error) {dos=error.getClass().getSimpleName()+": "+error.getMessage();}
            try {store=Boolean.toString(Files.getFileStore(probe).isReadOnly());}
            catch(IOException|RuntimeException error) {store=error.getClass().getSimpleName()+": "+error.getMessage();frames("file-store",error);}
            System.out.println("PS5 write-check detail: java="+System.getProperty("java.specification.version")
                +" access="+access+" dosReadOnly="+dos+" storeReadOnly="+store+" legacyCanWrite="+probe.toFile().canWrite());
            capacity(root);
            if(System.getProperty("os.name","").startsWith("Windows")) {
                for(Path volume:new Path[]{probe.getRoot(),Paths.get("C:\\")}) {
                    capacity(volume);
                    try {System.out.println("PS5 volume check: root="+volume+" exists="+Files.exists(volume)
                        +" directory="+Files.isDirectory(volume)+" store="+Files.getFileStore(volume).type());}
                    catch(IOException|RuntimeException error) {System.out.println("PS5 volume check: root="+volume
                        +" exists="+Files.exists(volume)+" directory="+Files.isDirectory(volume)+" error="+error);}
                }
            }
            Map<String,String> environment=Collections.singletonMap("create","false");
            try(FileSystem zip=FileSystems.newFileSystem(java.net.URI.create("jar:"+probe.toUri()),environment)) {
                System.out.println("PS5 file compatibility: isWritable="+writable+" actualWriteOpen="+actual+" zipReadOnly="+zip.isReadOnly());
            }
        } catch(IOException|RuntimeException error) {
            System.out.println("PS5 file compatibility probe: "+error.getClass().getSimpleName()+": "+error.getMessage());
        } finally {
            if(probe!=null)try {Files.deleteIfExists(probe);}catch(IOException ignored){}
        }
    }
    private static void capacity(Path path) {
        try {
            FileStore volume=Files.getFileStore(path);
            System.out.println("PS5 storage capacity: path="+path+" store="+volume
                +" totalBytes="+volume.getTotalSpace()+" usableBytes="+volume.getUsableSpace()
                +" freeBytes="+volume.getUnallocatedSpace()+" legacyUsableBytes="+path.toFile().getUsableSpace());
        } catch(IOException|RuntimeException error) {
            System.out.println("PS5 storage capacity: path="+path+" error="+error);
        }
    }
    private static void frames(String operation,Throwable error) {
        StackTraceElement[] stack=error.getStackTrace();
        for(int i=0;i<Math.min(stack.length,10);++i)System.out.println("PS5 file-check frame: "+operation+" "+stack[i]);
    }
}
