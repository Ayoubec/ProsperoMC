package org.prosperomc;

import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;

/** Isolated real class/resource/service loading and archive-handle fixture. */
public final class ClasspathCacheFixture {
    public interface Greeting {String message();}
    public static final class Provider implements Greeting {
        public Provider(){}
        public String message(){return "service preserved";}
    }
    public static final class Payload {
        public static String message(){return "class preserved";}
    }
    static void require(boolean value,String message) {if(!value)throw new AssertionError(message);}
    static void put(JarOutputStream zip,String name,byte[] data)throws IOException {
        zip.putNextEntry(new JarEntry(name));zip.write(data);zip.closeEntry();
    }
    static Path jar(Path folder,String name,Map<String,byte[]> entries)throws IOException {
        Path file=folder.resolve(name);Files.createDirectories(folder);
        try(JarOutputStream zip=new JarOutputStream(Files.newOutputStream(file))) {
            for(Map.Entry<String,byte[]> entry:entries.entrySet())put(zip,entry.getKey(),entry.getValue());
        }
        return file;
    }
    static Map<String,byte[]> map(String name,String value) {
        Map<String,byte[]> entries=new LinkedHashMap<String,byte[]>();entries.put(name,value.getBytes(java.nio.charset.StandardCharsets.UTF_8));return entries;
    }
    static byte[] resource(String name)throws IOException {
        try(InputStream in=ClasspathCacheFixture.class.getResourceAsStream("/"+name)) {
            require(in!=null,"missing fixture class "+name);return FabricMods.read(in,1024*1024);
        }
    }
    static void barrier(String label)throws IOException {
        System.out.println("MEASURE "+label);System.out.flush();System.in.read();
    }
    static void handles(Path root,boolean cached)throws Exception {
        Path libraries=root.resolve("libraries");List<Path> originals=new ArrayList<Path>();
        for(int i=0;i<40;++i) {
            Map<String,byte[]> entries=map("resource"+i+".txt","resource preserved");
            if(i==0) {
                for(String suffix:Arrays.asList("","$Payload","$Greeting","$Provider")) {
                    String name="org/prosperomc/ClasspathCacheFixture"+suffix+".class";entries.put(name,resource(name));
                }
                entries.put("META-INF/services/org.prosperomc.ClasspathCacheFixture$Greeting",
                    "org.prosperomc.ClasspathCacheFixture$Provider\n".getBytes("UTF-8"));
            }
            originals.add(jar(libraries,"library"+i+".jar",entries));
        }
        List<Path> classpath=cached?ClasspathCache.prepare(root,originals):originals;
        if(cached)for(int i=0;i<40;++i)require(!classpath.get(i).equals(originals.get(i)),"fixture not expanded");
        URL[] urls=new URL[classpath.size()];for(int i=0;i<urls.length;++i)urls[i]=classpath.get(i).toUri().toURL();
        barrier("before");
        try(URLClassLoader loader=new URLClassLoader(urls,null)) {
            Class<?> payload=loader.loadClass("org.prosperomc.ClasspathCacheFixture$Payload");
            require(payload.getMethod("message").invoke(null).equals("class preserved"),"class changed");
            for(int i=0;i<40;++i) {
                URL found=loader.getResource("resource"+i+".txt");require(found!=null,"resource missing");
                try(InputStream in=found.openStream()){require(new String(FabricMods.read(in,1024),"UTF-8").equals("resource preserved"),"resource changed");}
            }
            Class<?> greeting=loader.loadClass("org.prosperomc.ClasspathCacheFixture$Greeting");
            Object provider=ServiceLoader.load(greeting,loader).iterator().next();
            require(greeting.getMethod("message").invoke(provider).equals("service preserved"),"service changed");
            barrier("during");
        }
        barrier("after");
        System.out.println("PASS class/resource/ServiceLoader "+(cached?"cached":"original"));
    }
    static void safety(Path root)throws Exception {
        Path libs=root.resolve("libraries");Path ordinary=jar(libs,"ordinary.jar",map("fixture/resource.txt","good"));
        String original=FilesUtil.hash(ordinary,"SHA-256");Path expanded=ClasspathCache.expand(root,ordinary);
        require(!expanded.equals(ordinary),"ordinary dependency was not expanded");
        require(ClasspathCache.expand(root,ordinary).equals(expanded),"cache not reused");
        Files.write(expanded.resolve("fixture/resource.txt"),"evil".getBytes("UTF-8"));
        require(ClasspathCache.expand(root,ordinary).equals(expanded),"corrupt cache could not rebuild");
        require(new String(Files.readAllBytes(expanded.resolve("fixture/resource.txt")),"UTF-8").equals("good"),"same-size corrupt cache not repaired");
        Files.write(expanded.resolve("extra.class"),new byte[]{1});ClasspathCache.expand(root,ordinary);
        require(!Files.exists(expanded.resolve("extra.class")),"extra cache classes were kept");
        Files.delete(expanded.resolve("fixture/resource.txt"));ClasspathCache.expand(root,ordinary);
        require(Files.exists(expanded.resolve("fixture/resource.txt")),"missing cache resource not repaired");
        for(String name:Arrays.asList("META-INF/SIGN.SF","META-INF/SIGN.RSA","fabric.mod.json","quilt.mod.json",
                "META-INF/mods.toml","META-INF/neoforge.mods.toml","mcmod.info","META-INF/versions/9/Foo.class",
                "net/fabricmc/loader/Foo.class","org/quiltmc/loader/Foo.class","net/minecraftforge/Foo.class",
                "net/minecraft/launchwrapper/Launch.class","META-INF/embedded/foo.jar","META-INF/INDEX.LIST")) {
            Path special=jar(libs,"special"+Math.abs(name.hashCode())+".jar",map(name,"fixture"));
            require(ClasspathCache.expand(root,special).equals(special),"special archive expanded: "+name);
        }
        for(String attribute:Arrays.asList("Sealed: true","Multi-Release: true","Class-Path: other.jar",
                "Implementation-Version: 1","Specification-Version: 1")) {
            Path special=jar(libs,"manifest"+Math.abs(attribute.hashCode())+".jar",map("META-INF/MANIFEST.MF","Manifest-Version: 1.0\r\n"+attribute+"\r\n\r\n"));
            require(ClasspathCache.expand(root,special).equals(special),"manifest semantics changed: "+attribute);
        }
        Map<String,byte[]> collision=map("a/Foo.class","foo");collision.put("A/Bar.class","bar".getBytes("UTF-8"));
        Path collide=jar(libs,"collision.jar",collision);require(ClasspathCache.expand(root,collide).equals(collide),"case collision expanded");
        for(String name:Arrays.asList("../escape","absolute/../../escape","/escape","bad\\file", "NUL.class")) {
            Path traversal=jar(libs,"bad"+Math.abs(name.hashCode())+".jar",map(name,"bad"));
            require(ClasspathCache.expand(root,traversal).equals(traversal),"unsafe archive expanded");
        }
        Path outside=jar(root.resolve("instances"),"game.jar",map("Main.class","game"));
        require(ClasspathCache.expand(root,outside).equals(outside),"game/mod archive changed");
        Path corrupt=libs.resolve("corrupt.jar");Files.write(corrupt,new byte[]{1,2,3});
        require(ClasspathCache.expand(root,corrupt).equals(corrupt),"corrupt archive changed");
        require(FilesUtil.hash(ordinary,"SHA-256").equals(original),"original archive modified");
        Path failed=root.resolve("failure");Files.createDirectories(failed.resolve("libraries"));
        Path dependency=jar(failed.resolve("libraries"),"lib.jar",map("file.txt","content"));
        Files.write(failed.resolve("cache"),new byte[]{0});
        require(ClasspathCache.expand(failed,dependency).equals(dependency),"cache failure did not preserve original");
        System.out.println("PASS conservative guards, CRC repair, cache reuse, traversal, fallback, original integrity");
    }
    static void urlHandles(Path root,boolean uncached)throws Exception {
        List<Path> archives=new ArrayList<Path>();
        for(int i=0;i<40;++i)archives.add(jar(root,"resource"+i+".jar",map("resource.txt","same bytes")));
        barrier("before");
        if(uncached)Ps5Compat.resourceArchives();
        for(Path archive:archives) {
            URL resource=new URL("jar:"+archive.toUri().toURL()+"!/resource.txt");
            URLConnection connection=resource.openConnection();
            require(connection.getUseCaches()!=uncached,"jar cache default not applied");
            try(InputStream input=connection.getInputStream()) {
                require(new String(FabricMods.read(input,1024),"UTF-8").equals("same bytes"),"resource changed");
            }
        }
        barrier("during");barrier("after");
    }
    static void graphics(Path root)throws Exception {
        Path game=root.resolve("game");Files.createDirectories(game);
        Path modern=jar(root,"modern.jar",map("net/minecraft/client/PreferredGraphicsApi.class","fixture"));
        Path legacy=jar(root,"legacy.jar",map("legacy.class","fixture"));
        String original="renderDistance:16\npreferredGraphicsBackend:\"default\"\ncustom:keep\n";
        FilesUtil.write(game.resolve("options.txt"),original);
        GraphicsOptions.select(game,modern,"opengl");
        require(FilesUtil.read(game.resolve("options.txt")).contains("preferredGraphicsBackend:\"opengl\""),"Zink GL alias not selected");
        GraphicsOptions.select(game,modern,"vulkan");
        String options=FilesUtil.read(game.resolve("options.txt"));
        require(options.contains("preferredGraphicsBackend:\"vulkan\"")&&options.contains("renderDistance:16")&&options.contains("custom:keep"),"Vulkan or unrelated settings changed");
        require(FilesUtil.read(game.resolve("options-prosperomc-before-api.txt")).equals(original),"backup changed");
        GraphicsOptions.select(game,modern,"zink");
        require(FilesUtil.read(game.resolve("options.txt")).contains("preferredGraphicsBackend:\"opengl\""),"optional Zink must use game GL");
        try {GraphicsOptions.select(game,legacy,"vulkan");throw new AssertionError("legacy Vulkan silently accepted");}
        catch(IOException expected){require(expected.getMessage().contains("no built-in Vulkan"),"wrong failure");}
        String windowed="fullscreen:false\nfullscreenResolution:720x408@60:24\noverrideWidth:720\noverrideHeight:408\nrenderDistance:32\nresourcePacks:[\"vanilla\"]\n";
        FilesUtil.write(game.resolve("options.txt"),windowed);
        GraphicsOptions.fullscreen(game);
        String full=FilesUtil.read(game.resolve("options.txt"));
        require(full.contains("fullscreen:true\n")&&!full.contains("fullscreen:false"),"saved options still override fullscreen");
        require(full.contains("fullscreenResolution:\n")&&full.contains("overrideWidth:0\n")&&full.contains("overrideHeight:0\n"),"stale window resolution retained");
        require(full.contains("renderDistance:32\n")&&full.contains("resourcePacks:[\"vanilla\"]"),"unrelated options changed");
        require(FilesUtil.read(game.resolve("options-prosperomc-before-fullscreen.txt")).equals(windowed),"original fullscreen backup missing");
        GraphicsOptions.fullscreen(game);
        require(FilesUtil.read(game.resolve("options.txt")).equals(full),"fullscreen rewrite not idempotent");
        System.out.println("PASS independent graphics APIs, option preservation and legacy guard");
    }
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[1]);Files.createDirectories(root);
        if(args[0].equals("safety"))safety(root);
        else if(args[0].equals("graphics"))graphics(root);
        else if(args[0].startsWith("url-"))urlHandles(root,args[0].equals("url-uncached"));
        else handles(root,args[0].equals("cached"));
    }
}
