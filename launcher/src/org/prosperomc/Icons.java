package org.prosperomc;

import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;

/** Optional bounded PNG/JPEG/WebP artwork; a bad image never blocks a pack. */
final class Icons {
    static final int MAX_BYTES=2*1024*1024;
    static boolean valid(Path file)throws IOException {
        if(!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)||Files.size(file)<24||Files.size(file)>MAX_BYTES)return false;
        byte[] b=new byte[24];
        try(DataInputStream in=new DataInputStream(Files.newInputStream(file))) { in.readFully(b); }
        if(b[0]=='R'&&b[1]=='I'&&b[2]=='F'&&b[3]=='F'&&b[8]=='W'&&b[9]=='E'&&b[10]=='B'&&b[11]=='P'&&
           b[12]=='V'&&b[13]=='P'&&b[14]=='8'&&(b[15]==' '||b[15]=='L'||b[15]=='X')) {
            long length=0;for(int i=7;i>=4;i--)length=(length<<8)|(b[i]&255);
            return length+8==Files.size(file); // Native decoder validates dimensions/payload.
        }
        if((b[0]&255)==255&&(b[1]&255)==216&&(b[2]&255)==255)return true;
        byte[] signature={(byte)137,80,78,71,13,10,26,10};
        for(int i=0;i<8;i++)if(b[i]!=signature[i])return false;
        if(b[12]!=73||b[13]!=72||b[14]!=68||b[15]!=82)return false;
        int width=0,height=0;
        for(int i=16;i<20;i++)width=(width<<8)|(b[i]&255);
        for(int i=20;i<24;i++)height=(height<<8)|(b[i]&255);
        return width>0&&height>0&&width<=2048&&height<=2048;
    }
    static String nativePath(Path file) {
        String value=file.toAbsolutePath().normalize().toString().replace('\\','/');
        return value.regionMatches(true,0,"Z:/data/ProsperoMC/",0,18)?value.substring(2):value;
    }
    static String cache(Main app,String address) {
        if(address.isEmpty())return "";
        Path temporary=null;
        try {
            URL url=new URL(address);
            boolean fixture="http".equals(url.getProtocol())&&"127.0.0.1".equals(url.getHost())&&
                (app.settings.getOrDefault("modrinthApi","").startsWith("http://127.0.0.1:")||app.settings.getOrDefault("curseforgeApi","").startsWith("http://127.0.0.1:"));
            if(url.getUserInfo()!=null||(!fixture&&(!"https".equals(url.getProtocol())||!Arrays.asList("cdn.modrinth.com","media.forgecdn.net","mediafilez.forgecdn.net","edge.forgecdn.net").contains(url.getHost().toLowerCase(Locale.ROOT)))))return "";
            MessageDigest digest=MessageDigest.getInstance("SHA-256");
            StringBuilder key=new StringBuilder();
            for(byte b:digest.digest(address.getBytes("UTF-8")))key.append(String.format("%02x",b&255));
            Path cached=FilesUtil.safe(app.root.resolve("cache/icons"),key+".png");
            if(valid(cached))return nativePath(cached);
            Files.createDirectories(cached.getParent());
            temporary=cached.resolveSibling(cached.getFileName()+".part");
            HttpURLConnection connection=(HttpURLConnection)url.openConnection();
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(5000);connection.setReadTimeout(5000);
            connection.setRequestProperty("User-Agent","ProsperoMC/1.0 (Minecraft launcher)");
            try {
                if(connection.getResponseCode()!=200||connection.getContentLengthLong()>MAX_BYTES)return "";
                try(InputStream in=connection.getInputStream();OutputStream out=Files.newOutputStream(temporary)) {
                    byte[] buffer=new byte[8192];int n,total=0;
                    while((n=in.read(buffer))>=0) { if((total+=n)>MAX_BYTES)return "";out.write(buffer,0,n); }
                }
            } finally { connection.disconnect(); }
            if(!valid(temporary))return "";
            FilesUtil.atomic(temporary,cached);return nativePath(cached);
        } catch(Exception ignored) { return ""; }
        finally { if(temporary!=null)try {Files.deleteIfExists(temporary);}catch(IOException ignored){} }
    }
    static String instance(Main app,Path directory,Map<String,String> metadata)throws IOException {
        String relative=metadata.getOrDefault("icon","");
        if(!relative.isEmpty())try {Path icon=FilesUtil.safe(directory,relative);if(valid(icon))return nativePath(icon);}
            catch(IOException ignored) { /* Imported metadata cannot choose an external file. */ }
        Path own=directory.resolve("icon.png");
        if(valid(own))return nativePath(own);
        return "";
    }
    static void importIcon(Path pack,Path destination,Map<String,String> config,Map<String,String> metadata)throws IOException {
        String key=config.getOrDefault("iconKey","");
        List<Path> candidates=new ArrayList<Path>();
        if(key.matches("[A-Za-z0-9_.+-]{1,96}")) {
            candidates.add(FilesUtil.safe(pack,key+".png"));candidates.add(FilesUtil.safe(pack,"icons/"+key+".png"));
        }
        candidates.add(pack.resolve("icon.png"));
        for(Path icon:candidates)if(valid(icon)) {
            Files.copy(icon,destination.resolve("icon.png"),StandardCopyOption.REPLACE_EXISTING);
            metadata.put("icon","icon.png");return;
        }
    }
    /** Existing packs gain artwork on backend startup/refresh, never while drawing frames. */
    static void refreshInstances(Main app) {
        Path instances=app.root.resolve("instances");if(!Files.isDirectory(instances))return;
        int uncached=0;
        try(DirectoryStream<Path> directories=Files.newDirectoryStream(instances)) {
            for(Path directory:directories)try {
                if(Files.isSymbolicLink(directory))continue;
                Path properties=directory.resolve("instance.properties");
                if(!Files.isRegularFile(properties,LinkOption.NOFOLLOW_LINKS))continue;
                Map<String,String> metadata=FilesUtil.properties(properties);
                if(!instance(app,directory,metadata).isEmpty())continue;
                String project=metadata.getOrDefault("modrinthProject","");if(project.isEmpty())continue;
                Main.id(project);
                Path cached=FilesUtil.safe(app.root.resolve("cache"),"icon-project-"+project+".json");
                if(!Files.isRegularFile(cached)) {
                    if(uncached++>=2)continue;
                    app.progress("working","Loading instance artwork",0,1);
                    FilesUtil.refresh(app.settings.getOrDefault("modrinthApi","https://api.modrinth.com/v2").replaceAll("/+$","")+"/project/"+project,cached);
                }
                String address=Json.text(app.installer.json(cached),"icon_url"),image=cache(app,address);
                if(image.isEmpty())continue;
                Path source=Paths.get(image.startsWith("/data/ProsperoMC/")?"Z:"+image:image);
                Files.copy(source,directory.resolve("icon.png"),StandardCopyOption.REPLACE_EXISTING);
                metadata.put("icon","icon.png");FilesUtil.properties(properties,metadata);
            }catch(IOException ignored) { /* Artwork remains optional. */ }
             catch(IllegalArgumentException ignored) { /* Bad artwork metadata must not hide instances. */ }
        }catch(IOException ignored) { /* Installation state remains usable. */ }
    }
}
