package org.prosperomc.zip;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.*;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;

/** Bounded backing channels for ZipFS; its central directory and Paths stay intact. */
public final class ZipChannels {
    private static final int LIMIT=16;
    private static final LinkedHashMap<ReadChannel,SeekableByteChannel> OPEN=
        new LinkedHashMap<ReadChannel,SeekableByteChannel>(32,0.75f,true);
    private static long opens,evictions;
    private ZipChannels() {}

    public static SeekableByteChannel newByteChannel(Path path,OpenOption... options)throws IOException {
        if(options.length!=1||options[0]!=StandardOpenOption.READ||path.getFileSystem()!=FileSystems.getDefault())
            return Files.newByteChannel(path,options);
        String name=path.getFileName().toString().toLowerCase(Locale.ROOT);
        if(!name.endsWith(".jar")&&!name.endsWith(".zip"))return Files.newByteChannel(path,options);
        synchronized(OPEN) {
            ReadChannel result=new ReadChannel(path.toAbsolutePath().normalize());
            result.backing();
            return result;
        }
    }
    public static long[] statistics() {
        synchronized(OPEN) {return new long[]{OPEN.size(),LIMIT,opens,evictions};}
    }
    private static final class ReadChannel implements SeekableByteChannel {
        private final Path path;
        private final BasicFileAttributes identity;
        private long position;
        private boolean alive=true;
        ReadChannel(Path path)throws IOException {
            this.path=path;identity=Files.readAttributes(path,BasicFileAttributes.class);
            if(!identity.isRegularFile())throw new IOException("ZIP backing is not a regular file: "+path);
        }
        private void check()throws ClosedChannelException {if(!alive)throw new ClosedChannelException();}
        private SeekableByteChannel backing()throws IOException {
            check();
            SeekableByteChannel channel=OPEN.get(this);
            if(channel!=null)return channel;
            if(OPEN.size()>=LIMIT) {
                Iterator<Map.Entry<ReadChannel,SeekableByteChannel>> i=OPEN.entrySet().iterator();
                Map.Entry<ReadChannel,SeekableByteChannel> entry=i.next();
                entry.getValue().close();i.remove();evictions++;
            }
            BasicFileAttributes now=Files.readAttributes(path,BasicFileAttributes.class);
            if(!now.isRegularFile()||identity.size()!=now.size()||!identity.lastModifiedTime().equals(now.lastModifiedTime())||
                !Objects.equals(identity.fileKey(),now.fileKey()))
                throw new IOException("ZIP backing changed while mounted: "+path);
            channel=Files.newByteChannel(path,StandardOpenOption.READ);
            try {channel.position(position);}catch(IOException|RuntimeException error) {channel.close();throw error;}
            OPEN.put(this,channel);opens++;
            return channel;
        }
        public int read(ByteBuffer target)throws IOException {
            synchronized(OPEN) {
                SeekableByteChannel channel=backing();
                try {int count=channel.read(target);position=channel.position();return count;}
                catch(IOException|RuntimeException error) {
                    if(!channel.isOpen()) {alive=false;OPEN.remove(this);}
                    else try {position=channel.position();}catch(IOException positionError){error.addSuppressed(positionError);}
                    throw error;
                }
            }
        }
        public int write(ByteBuffer source)throws IOException {synchronized(OPEN){check();throw new NonWritableChannelException();}}
        public long position()throws IOException {synchronized(OPEN){check();return position;}}
        public SeekableByteChannel position(long next)throws IOException {
            synchronized(OPEN) {
                check();if(next<0)throw new IllegalArgumentException("Negative ZIP channel position");
                SeekableByteChannel channel=OPEN.get(this);
                if(channel!=null)channel.position(next);
                position=next;return this;
            }
        }
        public long size()throws IOException {synchronized(OPEN){return backing().size();}}
        public SeekableByteChannel truncate(long size)throws IOException {synchronized(OPEN){check();throw new NonWritableChannelException();}}
        public boolean isOpen() {synchronized(OPEN){return alive;}}
        public void close()throws IOException {
            synchronized(OPEN) {
                if(!alive)return;
                alive=false;SeekableByteChannel channel=OPEN.remove(this);
                if(channel!=null)channel.close();
            }
        }
    }
}
