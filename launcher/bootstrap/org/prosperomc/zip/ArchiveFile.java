package org.prosperomc.zip;

import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;

/** ZipFile.Source keeps parsed directories and verification; only its READ file is pooled. */
public final class ArchiveFile extends RandomAccessFile {
    private static final int LIMIT=16;
    private static final LinkedHashMap<ArchiveFile,RandomAccessFile> OPEN=new LinkedHashMap<>(32,0.75f,true);
    private static long opens,evictions;
    private final Path path;
    private final BasicFileAttributes identity;
    private long position;
    private boolean alive;
    public ArchiveFile(File file,String mode)throws IOException {
        // The superclass requires a real open. Reserve room, then close this
        // temporary descriptor before Source can use the pooled READ object.
        super(reserve(file,mode),mode);
        super.close();
        path=file.toPath().toAbsolutePath().normalize();
        identity=Files.readAttributes(path,BasicFileAttributes.class);
        if(!identity.isRegularFile())throw new IOException("JAR backing is not a regular file: "+path);
        alive=true;
    }
    private static File reserve(File file,String mode)throws IOException {
        if(!"r".equals(mode))throw new IOException("JAR pool requires a READ backing file");
        synchronized(OPEN){evict();}return file;
    }
    private static void evict()throws IOException {
        if(OPEN.size()<LIMIT)return;
        Iterator<Map.Entry<ArchiveFile,RandomAccessFile>> entries=OPEN.entrySet().iterator();
        Map.Entry<ArchiveFile,RandomAccessFile> entry=entries.next();
        entry.getValue().close();entries.remove();evictions++;
    }
    private void check()throws IOException {if(!alive)throw new IOException("JAR backing file is closed");}
    private RandomAccessFile backing()throws IOException {
        check();RandomAccessFile file=OPEN.get(this);if(file!=null)return file;
        evict();BasicFileAttributes now=Files.readAttributes(path,BasicFileAttributes.class);
        if(!now.isRegularFile()||identity.size()!=now.size()||!identity.lastModifiedTime().equals(now.lastModifiedTime())||
            !Objects.equals(identity.fileKey(),now.fileKey()))throw new IOException("JAR backing changed while open: "+path);
        file=new RandomAccessFile(path.toFile(),"r");
        try{file.seek(position);}catch(IOException error){file.close();throw error;}
        OPEN.put(this,file);opens++;return file;
    }
    public int read()throws IOException {
        synchronized(OPEN){RandomAccessFile file=backing();int result=file.read();position=file.getFilePointer();return result;}
    }
    public int read(byte[] bytes)throws IOException {return read(bytes,0,bytes.length);}
    public int read(byte[] bytes,int offset,int length)throws IOException {
        synchronized(OPEN) {
            RandomAccessFile file=backing();
            try{int result=file.read(bytes,offset,length);position=file.getFilePointer();return result;}
            catch(IOException error){try{position=file.getFilePointer();}catch(IOException other){error.addSuppressed(other);}throw error;}
        }
    }
    public void seek(long next)throws IOException {
        synchronized(OPEN) {
            check();if(next<0)throw new IOException("Negative JAR seek");
            RandomAccessFile file=OPEN.get(this);if(file!=null)file.seek(next);position=next;
        }
    }
    public long getFilePointer()throws IOException {synchronized(OPEN){check();return position;}}
    public long length()throws IOException {synchronized(OPEN){return backing().length();}}
    public void close()throws IOException {
        synchronized(OPEN){if(!alive)return;alive=false;RandomAccessFile file=OPEN.remove(this);if(file!=null)file.close();}
    }
    public void write(int value)throws IOException {throw new IOException("JAR backing is READ only");}
    public void write(byte[] bytes)throws IOException {throw new IOException("JAR backing is READ only");}
    public void write(byte[] bytes,int offset,int length)throws IOException {throw new IOException("JAR backing is READ only");}
    public void setLength(long length)throws IOException {throw new IOException("JAR backing is READ only");}
    public static long[] statistics(){synchronized(OPEN){return new long[]{OPEN.size(),LIMIT,opens,evictions};}}
}
