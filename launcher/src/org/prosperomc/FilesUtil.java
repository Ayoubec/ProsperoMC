package org.prosperomc;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.security.*;
import java.util.*;
import java.util.zip.*;
final class FilesUtil {
    static String read(Path p)throws IOException {
        if(Files.size(p)>32*1024*1024)throw new IOException("Metadata too large: "+p.getFileName());
        return new String(Files.readAllBytes(p), StandardCharsets.UTF_8);
    }
    static Map<String, String> properties(Path p)throws IOException {
        Map<String, String> m=new LinkedHashMap<String, String>();
        if(!Files.isRegularFile(p))return m;
        for(String line:read(p).split("\\r?\\n")) {
            if(line.trim().isEmpty()||line.startsWith("#")||line.startsWith(";"))continue;
            int n=line.indexOf('=');
            if(n<=0)throw new IOException("Malformed properties line");
            String k=line.substring(0, n).trim(), v=line.substring(n+1);
            if(m.put(k, v)!=null)throw new IOException("Duplicate property: "+k);
        }
        return m;
    }
    static void properties(Path p, Map<String, String> m)throws IOException {
        StringBuilder b=new StringBuilder();
        for(Map.Entry<String, String> e:m.entrySet()) {
            if(e.getKey().matches(".*[\\r\\n=].*")||e.getValue().matches("(?s).*[\\r\\n].*"))throw new IOException("Multiline property refused");
            b.append(e.getKey()).append('=').append(e.getValue()).append('\n');
        }
        write(p, b.toString());
    }
    static void write(Path p, String data)throws IOException {
        Files.createDirectories(p.toAbsolutePath().getParent());
        Path t=p.resolveSibling(p.getFileName()+".tmp");
        Files.write(t, data.getBytes(StandardCharsets.UTF_8));
        atomic(t, p);
    }
    static void atomic(Path t, Path p)throws IOException {
        IOException last=null;
        for(int attempt=0; attempt<50; attempt++) {
            try {
                try {
                    Files.move(t, p, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
                }
                catch(AtomicMoveNotSupportedException e) {
                    Files.move(t, p, StandardCopyOption.REPLACE_EXISTING);
                }
                return;
            }
            catch(FileSystemException e) {
                last=e;
                if(!Files.exists(t))throw e;
                try {
                    Thread.sleep(20);
                }
                catch(InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    throw new IOException("State replacement interrupted", interrupted);
                }
            }
        }
        throw last;
    }
    static Path safe(Path root, String rel)throws IOException {
        if(rel.isEmpty()||rel.indexOf('\0')>=0||rel.indexOf(':')>=0||rel.startsWith("/")||rel.startsWith("\\"))throw new IOException("Unsafe relative path: "+rel);
        Path r=root.toAbsolutePath().normalize(), p=r.resolve(rel.replace('\\', '/')).normalize();
        if(!p.startsWith(r)||p.equals(r))throw new IOException("Path escapes destination: "+rel);
        Path check=p;
        while(check!=null&&check.startsWith(r)) {
            if(Files.isSymbolicLink(check))throw new IOException("Symbolic link refused: "+rel);
            check=check.getParent();
        }
        return p;
    }
    static String sha1(Path p)throws IOException {
        return hash(p,"SHA-1");
    }
    static String hash(Path p,String algorithm)throws IOException {
        try {
            MessageDigest d=MessageDigest.getInstance(algorithm);
            try(InputStream in=Files.newInputStream(p)) {
                byte[] b=new byte[65536];
                int n;
                while((n=in.read(b))>=0)d.update(b, 0, n);
            }
            StringBuilder s=new StringBuilder();
            for(byte b:d.digest())s.append(String.format("%02x", b&255));
            return s.toString();
        }
        catch(NoSuchAlgorithmException e) {
            throw new AssertionError(e);
        }
    }
    static void download(String address, Path target, String hash, long size)throws IOException {
        if(!hash.isEmpty()&&!hash.matches("[0-9a-fA-F]{40}"))throw new IOException("Invalid SHA1");
        if(Files.isRegularFile(target)&&valid(target, hash, size))return;
        Files.createDirectories(target.toAbsolutePath().getParent());
        Path t=target.resolveSibling(target.getFileName()+".part");
        try {
            URL url=new URL(address);
            if(!url.getProtocol().equals("https")&&!url.getProtocol().equals("http"))throw new IOException("Only HTTP(S) downloads are allowed");
            URLConnection connection=url.openConnection();
            connection.setConnectTimeout(20000);
            connection.setReadTimeout(30000);
            connection.setRequestProperty("User-Agent", "ProsperoMC/0.1 (Minecraft Java launcher)");
            if(connection instanceof HttpURLConnection) {
                int status=((HttpURLConnection)connection).getResponseCode();
                if(status!=200)throw new IOException("HTTP "+status+" downloading "+url.getHost());
            }
            long total=0;
            try(InputStream in=connection.getInputStream(); OutputStream out=Files.newOutputStream(t)) {
                byte[] b=new byte[65536];
                int n;
                while((n=in.read(b))>=0) {
                    total+=n;
                    if(total>2L*1024*1024*1024||(size>=0&&total>size))throw new IOException("Download exceeds expected size");
                    out.write(b, 0, n);
                }
            }
            if(!valid(t, hash, size))throw new IOException("Download integrity mismatch: "+target.getFileName());
            atomic(t, target);
        }
        finally {
            Files.deleteIfExists(t);
        }
    }
    static void refresh(String address,Path target)throws IOException {
        Path fresh=target.resolveSibling(target.getFileName()+".refresh-"+System.nanoTime());
        try { download(address,fresh,"",-1); atomic(fresh,target); }
        finally { Files.deleteIfExists(fresh); }
    }
    static boolean valid(Path p, String hash, long size)throws IOException {
        return(size<0||Files.size(p)==size)&&(hash.isEmpty()||sha1(p).equalsIgnoreCase(hash));
    }
    static void unzip(Path archive, Path dst, Set<String> excludes)throws IOException {
        long total=0;
        int count=0;
        try(ZipInputStream z=new ZipInputStream(Files.newInputStream(archive))) {
            ZipEntry e;
            while((e=z.getNextEntry())!=null) {
                if(++count>100000)throw new IOException("Too many archive entries");
                Path p=safe(dst, e.getName());
                String name=p.getFileName().toString().toLowerCase(Locale.ROOT);
                String entryName=e.getName().replace('\\','/');
                boolean excluded=excludes.contains(name)||entryName.startsWith("META-INF/");
                for(String prefix:excludes)if(entryName.startsWith(prefix))excluded=true;
                if(excluded)continue;
                if(e.isDirectory()) {
                    Files.createDirectories(p);
                    continue;
                }
                Files.createDirectories(p.getParent());
                try(OutputStream out=Files.newOutputStream(p)) {
                    byte[] b=new byte[65536];
                    int n;
                    while((n=z.read(b))>=0) {
                        total+=n;
                        if(total>4L*1024*1024*1024)throw new IOException("Archive expanded size limit");
                        out.write(b, 0, n);
                    }
                }
            }
        }
    }
    static boolean privateFile(String name) {
        String n=name.toLowerCase(Locale.ROOT);
        return n.equals("accounts.json")||n.startsWith("launcher_accounts")||n.startsWith("launcher_profiles")||n.equals("usercache.json")||n.equals("account.json")||n.equals("auth.properties")||n.equals("auth-pending.json")||n.equals("launch-plan.json")||n.endsWith(".log");
    }
    static void copyTree(final Path src, final Path dst)throws IOException {
        Files.walkFileTree(src, new SimpleFileVisitor<Path>() {
            public FileVisitResult preVisitDirectory(Path p, BasicFileAttributes a)throws IOException {
                if(Files.isSymbolicLink(p))throw new IOException("Symbolic link import refused"); Files.createDirectories(dst.resolve(src.relativize(p))); return FileVisitResult.CONTINUE;
            }
            public FileVisitResult visitFile(Path p, BasicFileAttributes a)throws IOException {
                if(a.isSymbolicLink())throw new IOException("Symbolic link import refused"); if(!privateFile(p.getFileName().toString()))Files.copy(p, dst.resolve(src.relativize(p)), StandardCopyOption.REPLACE_EXISTING); return FileVisitResult.CONTINUE;
            }
        }
        );
    }
    static void deleteTree(Path p)throws IOException {
        if(!Files.exists(p))return;
        Files.walkFileTree(p, new SimpleFileVisitor<Path>() {
            public FileVisitResult visitFile(Path f, BasicFileAttributes a)throws IOException {
                Files.delete(f); return FileVisitResult.CONTINUE;
            }
            public FileVisitResult postVisitDirectory(Path d, IOException e)throws IOException {
                if(e!=null)throw e; Files.delete(d); return FileVisitResult.CONTINUE;
            }
        }
        );
    }
    static String quote(String s) {
        if(s.indexOf('"')>=0||s.indexOf('\n')>=0||s.indexOf('\r')>=0)throw new IllegalArgumentException("Unsafe command argument");
        return "\""+s+"\"";
    }
    static void restrict(Path p) {
        try {
            Files.setPosixFilePermissions(p, PosixFilePermissions.fromString("rw-------"));
        }
        catch(Exception ignored) {
            /* Wine/Windows has no POSIX permissions: runtime data directory controls access. */
        }
    }
}
