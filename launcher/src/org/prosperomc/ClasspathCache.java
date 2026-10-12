package org.prosperomc;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import java.util.zip.*;

/** Ordinary dependency resources as directories, avoiding retained archive handles. */
final class ClasspathCache {
    static final long MAX_ARCHIVE=256L*1024*1024, MAX_EXPANDED=512L*1024*1024;
    static final int MAX_ENTRIES=50000;
    static final String READY="classpath-cache-v1\n";

    static List<Path> prepare(Path root,List<Path> dependencies) {
        List<Path> result=new ArrayList<Path>();
        for(Path dependency:dependencies)result.add(expand(root,dependency));
        return result;
    }
    static boolean special(String name) {
        String n=name.toLowerCase(Locale.ROOT);
        if(n.equals("fabric.mod.json")||n.equals("quilt.mod.json")||n.equals("mcmod.info")||
           n.equals("meta-inf/mods.toml")||n.equals("meta-inf/neoforge.mods.toml")||
           n.equals("meta-inf/index.list")||n.startsWith("meta-inf/versions/")||n.endsWith(".jar"))return true;
        if(n.startsWith("meta-inf/")&&(n.endsWith(".sf")||n.endsWith(".rsa")||n.endsWith(".dsa")||n.endsWith(".ec")))return true;
        for(String prefix:Arrays.asList("net/fabricmc/loader/","org/quiltmc/loader/","net/minecraft/launchwrapper/",
                "net/minecraftforge/","cpw/mods/fml/","cpw/mods/modlauncher/","org/spongepowered/asm/launch/"))
            if(n.startsWith(prefix))return true;
        return false;
    }
    static boolean protectedManifest(Attributes attributes) {
        for(Object key:attributes.keySet()) {
            String name=key.toString().toLowerCase(Locale.ROOT);
            if(name.startsWith("implementation-")||name.startsWith("specification-"))return true;
        }
        return "true".equalsIgnoreCase(attributes.getValue("Sealed"))||
            "true".equalsIgnoreCase(attributes.getValue("Multi-Release"))||
            attributes.getValue("Class-Path")!=null;
    }
    static List<ZipEntry> entries(ZipFile zip)throws IOException {
        ZipEntry manifest=zip.getEntry("META-INF/MANIFEST.MF");
        if(manifest!=null) {
            if(manifest.getSize()<0||manifest.getSize()>1024*1024)return null;
            Manifest parsed;
            try(InputStream in=zip.getInputStream(manifest)){parsed=new Manifest(in);}
            if(protectedManifest(parsed.getMainAttributes()))return null;
            for(Attributes section:parsed.getEntries().values())if(protectedManifest(section))return null;
        }
        List<ZipEntry> entries=new ArrayList<ZipEntry>();Map<String,String> paths=new HashMap<String,String>();
        Set<String> names=new HashSet<String>();
        long expanded=0;Enumeration<? extends ZipEntry> all=zip.entries();
        while(all.hasMoreElements()) {
            ZipEntry entry=all.nextElement();String name=entry.getName();
            if(entries.size()>=MAX_ENTRIES||name.isEmpty()||name.length()>512||name.indexOf('\\')>=0||
               name.matches("(?s).*[\\x00-\\x1f\\x7f].*")||special(name))return null;
            String trimmed=entry.isDirectory()&&name.endsWith("/")?name.substring(0,name.length()-1):name;
            // Do not normalize away traversal, duplicate entries or Windows case collisions.
            if(name.equalsIgnoreCase("META-INF/MANIFEST.MF")&&!name.equals("META-INF/MANIFEST.MF"))return null;
            for(String part:trimmed.split("/",-1))if(part.isEmpty()||part.equals(".")||part.equals("..")||
                    part.indexOf(':')>=0||part.endsWith(".")||part.endsWith(" ")||
                    part.split("\\.",2)[0].matches("(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])"))return null;
            if(!names.add(trimmed.toLowerCase(Locale.ROOT)))return null;
            String prefix="";
            for(String part:trimmed.split("/")) {
                prefix=prefix.isEmpty()?part:prefix+"/"+part;
                String previous=paths.put(prefix.toLowerCase(Locale.ROOT),prefix);
                if(previous!=null&&!previous.equals(prefix))return null;
            }
            if(entry.getSize()<0||entry.getSize()>64L*1024*1024||entry.getCrc()<0)return null;
            if((expanded+=entry.getSize())>MAX_EXPANDED)return null;
            entries.add(entry);
        }
        return entries;
    }
    static long checksum(Path file)throws IOException {
        CRC32 crc=new CRC32();byte[] bytes=new byte[65536];
        try(InputStream in=Files.newInputStream(file)){int n;while((n=in.read(bytes))>=0)crc.update(bytes,0,n);}
        return crc.getValue();
    }
    static boolean valid(Path target,List<ZipEntry> entries,String hash)throws IOException {
        Path content=FilesUtil.safe(target,"content"), ready=FilesUtil.safe(target,"ready");
        if(!Files.isRegularFile(ready,LinkOption.NOFOLLOW_LINKS)||!FilesUtil.read(ready).equals(READY+hash+"\n"))return false;
        int expected=0;
        for(ZipEntry entry:entries) {
            String name=entry.getName();if(entry.isDirectory())continue;
            Path file=FilesUtil.safe(content,name);++expected;
            if(!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)||Files.size(file)!=entry.getSize()||
                    checksum(file)!=entry.getCrc())return false;
        }
        final int[] actual={0};
        Files.walkFileTree(content,new SimpleFileVisitor<Path>() {
            public FileVisitResult preVisitDirectory(Path path,java.nio.file.attribute.BasicFileAttributes attrs)throws IOException {
                if(Files.isSymbolicLink(path))throw new IOException("Cached classpath link refused");return FileVisitResult.CONTINUE;
            }
            public FileVisitResult visitFile(Path path,java.nio.file.attribute.BasicFileAttributes attrs)throws IOException {
                if(!attrs.isRegularFile()||attrs.isSymbolicLink())throw new IOException("Cached classpath entry refused");
                ++actual[0];return FileVisitResult.CONTINUE;
            }
        });
        return actual[0]==expected;
    }
    static synchronized Path expand(Path root,Path archive) {
        Path temporary=null;
        try {
            Path libraries=FilesUtil.safe(root,"libraries");
            Path original=archive.toAbsolutePath().normalize();
            if(!original.startsWith(libraries)||!Files.isRegularFile(original,LinkOption.NOFOLLOW_LINKS)||
                    !original.getFileName().toString().endsWith(".jar")||Files.size(original)>MAX_ARCHIVE)return archive;
            FilesUtil.safe(libraries,libraries.relativize(original).toString());
            String hash=FilesUtil.hash(original,"SHA-256");
            Path target=FilesUtil.safe(root,"cache/classpath-v1/"+hash);
            try(ZipFile zip=new ZipFile(original.toFile())) {
                List<ZipEntry> entries=entries(zip);if(entries==null)return archive;
                if(Files.isDirectory(target,LinkOption.NOFOLLOW_LINKS)&&valid(target,entries,hash))return target.resolve("content");
                temporary=FilesUtil.safe(root,"cache/classpath-v1/"+hash+".new-"+UUID.randomUUID());
                Path content=FilesUtil.safe(temporary,"content");Files.createDirectories(content);
                byte[] bytes=new byte[65536];long total=0;
                for(ZipEntry entry:entries) {
                    String name=entry.getName();if(entry.isDirectory())continue;
                    Path file=FilesUtil.safe(content,name);Files.createDirectories(file.getParent());
                    CRC32 crc=new CRC32();long size=0;
                    try(InputStream in=zip.getInputStream(entry);OutputStream out=Files.newOutputStream(file,StandardOpenOption.CREATE_NEW)) {
                        int n;while((n=in.read(bytes))>=0) {
                            if((size+=n)>entry.getSize()||(total+=n)>MAX_EXPANDED)throw new IOException("Classpath cache size limit");
                            crc.update(bytes,0,n);out.write(bytes,0,n);
                        }
                    }
                    if(size!=entry.getSize()||crc.getValue()!=entry.getCrc())throw new IOException("Classpath cache integrity mismatch");
                }
                FilesUtil.write(temporary.resolve("ready"),READY+hash+"\n");
                // Only the SHA-addressed cache is replaced; original JARs are untouched.
                if(Files.exists(target,LinkOption.NOFOLLOW_LINKS))FilesUtil.deleteTree(target);
                FilesUtil.atomic(temporary,target);temporary=null;
                return target.resolve("content");
            }
        } catch(IOException|IllegalArgumentException|SecurityException failure) {
            // Uncertain archive semantics or unavailable cache keeps the original classpath.
            return archive;
        } finally {
            if(temporary!=null)try{FilesUtil.deleteTree(temporary);}catch(IOException ignored){}
        }
    }
}
