package org.prosperomc;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

/** Exact legacy Minecraft 1.12.2 Forge formats; never executes installer code. */
final class ForgeInstaller {
    static final String DEFAULT_VERSION="14.23.5.2864";
    static final String MAVEN="https://maven.minecraftforge.net/";
    static final String DEFAULT_SHA1="b5ec0016c292830f2325e39417d1ec4d9e166cab";
    private ForgeInstaller() {}

    static Map<String,Object> install(Installer installer,Map<String,Object> base,
                                      Map<String,String> instance)throws IOException {
        String mc=instance.get("version"), lv=instance.getOrDefault("loaderVersion","");
        if(!"1.12.2".equals(mc)||!"1.12.2".equals(Json.text(base,"id")))
            throw new IOException("Legacy Forge supports Minecraft 1.12.2 only; modern Forge processors are unavailable");
        if(lv.isEmpty()) lv=DEFAULT_VERSION;
        if(!Arrays.asList("14.23.5.2847","14.23.5.2859",DEFAULT_VERSION).contains(lv))
            throw new IOException("Unsupported legacy Forge version; supported: 14.23.5.2847, 14.23.5.2859, "+DEFAULT_VERSION);
        String coordinate="net.minecraftforge:forge:"+mc+"-"+lv;
        String rel=Installer.maven(coordinate);
        String address=MAVEN+rel.substring(0,rel.length()-4)+"-installer.jar";
        Path cache=FilesUtil.safe(installer.root.resolve("cache"),"forge-"+mc+"-"+lv+"-installer.jar");
        String source=installer.app.request.getOrDefault("forgeInstaller","");
        String expected;
        if(!source.isEmpty()) {
            expected=installer.app.request.getOrDefault("forgeInstallerSha1","");
            digest(expected);
            Path input=Paths.get(source);
            if(!FilesUtil.valid(input,expected,-1))throw new IOException("Forge installer integrity mismatch");
            Files.createDirectories(cache.getParent());
            Files.copy(input,cache,StandardCopyOption.REPLACE_EXISTING);
        } else {
            expected=lv.equals(DEFAULT_VERSION)?DEFAULT_SHA1:remoteDigest(address,cache.resolveSibling(cache.getFileName()+".sha1"));
            FilesUtil.download(address,cache,expected,-1);
        }
        if(!FilesUtil.valid(cache,expected,-1))throw new IOException("Forge installer integrity mismatch");
        try(ZipFile zip=new ZipFile(cache.toFile())) {
            validateEntries(zip,installer.root.resolve("cache/forge-entry-validation"));
            Map<String,Object> profile=readJson(zip,"install_profile.json");
            if(!Json.arr(profile.get("processors")).isEmpty())throw new IOException("Forge installer processors are unsupported");
            Map<String,Object> patch;
            String embedded;
            if(profile.containsKey("versionInfo")) {
                Map<String,Object> install=Json.obj(profile.get("install"));
                if(!mc.equals(Json.text(install,"minecraft"))||!coordinate.equals(Json.text(install,"path")))
                    throw new IOException("Forge installer profile coordinate/version mismatch");
                patch=Json.obj(profile.get("versionInfo"));
                embedded=Json.text(install,"filePath");
                FilesUtil.safe(installer.root.resolve("cache/forge-entry-validation"),embedded);
            } else {
                if(!mc.equals(Json.text(profile,"minecraft"))||!coordinate.equals(Json.text(profile,"path")))
                    throw new IOException("Forge installer profile coordinate/version mismatch");
                String json=Json.text(profile,"json");
                if(json.startsWith("/"))json=json.substring(1);
                FilesUtil.safe(installer.root.resolve("cache/forge-entry-validation"),json);
                patch=readJson(zip,json);embedded="maven/"+rel;
            }
            if(!mc.equals(Json.text(patch,"inheritsFrom"))||
               !"net.minecraft.launchwrapper.Launch".equals(Json.text(patch,"mainClass"))||
               !Json.text(patch,"minecraftArguments").contains("--tweakClass net.minecraftforge.fml.common.launcher.FMLTweaker"))
                throw new IOException("Unsupported Forge launch profile; expected 1.12.2 LaunchWrapper/FMLTweaker");
            List<Object> patchLibs=new ArrayList<Object>();
            boolean foundForge=false;
            for(Object value:Json.arr(patch.get("libraries"))) {
                Map<String,Object> lib=new LinkedHashMap<String,Object>(Json.obj(value));
                if(Boolean.FALSE.equals(lib.get("clientreq")))continue;
                String name=Json.text(lib,"name"), libraryRel=Installer.maven(name);
                Path libraryPath=FilesUtil.safe(installer.root.resolve("libraries"),libraryRel);
                Map<String,Object> spec;
                if(lib.containsKey("downloads")) {
                    Map<String,Object> downloads=Json.obj(lib.get("downloads"));
                    if(!downloads.containsKey("artifact"))throw new IOException("Forge library artifact missing");
                    spec=new LinkedHashMap<String,Object>(Json.obj(downloads.get("artifact")));
                    if(!libraryRel.equals(Json.text(spec,"path")))throw new IOException("Forge artifact coordinate/path mismatch");
                } else {
                    spec=new LinkedHashMap<String,Object>();spec.put("path",libraryRel);
                    String repository=lib.containsKey("url")?Json.text(lib,"url"):"https://libraries.minecraft.net/";
                    spec.put("url",repository+(repository.endsWith("/")?"":"/")+libraryRel);
                    List<Object> hashes=Json.arr(lib.get("checksums"));
                    if(!hashes.isEmpty())spec.put("sha1",Json.str(hashes.get(0)));
                    else if(lib.containsKey("sha1"))spec.put("sha1",lib.get("sha1"));
                }
                if(name.equals(coordinate)) {
                    foundForge=true;
                    extract(zip,embedded,libraryPath);
                    String hash=Json.text(spec,"sha1");
                    if(!hash.isEmpty())digest(hash);
                    if(!FilesUtil.valid(libraryPath,hash,Installer.size(spec))) {
                        Files.deleteIfExists(libraryPath);throw new IOException("Embedded Forge artifact integrity mismatch");
                    }
                    spec.put("sha1",FilesUtil.sha1(libraryPath));spec.put("size",Files.size(libraryPath));
                    /* Existing verified jar short-circuits the generic downloader. */
                    spec.put("url",MAVEN+libraryRel);
                } else {
                    String hash=Json.text(spec,"sha1");
                    if(hash.isEmpty()) {
                        Path sum=FilesUtil.safe(installer.root.resolve("cache/forge-checksums"),libraryRel+".sha1");
                        hash=remoteDigest(Json.text(spec,"url"),sum);spec.put("sha1",hash);
                    }
                    digest(hash);
                }
                Map<String,Object> downloads=new LinkedHashMap<String,Object>();downloads.put("artifact",spec);
                lib.put("downloads",downloads);patchLibs.add(lib);
            }
            if(!foundForge)throw new IOException("Forge profile does not include the expected embedded artifact");
            LinkedHashMap<String,Object> libs=new LinkedHashMap<String,Object>();
            for(Object lib:Json.arr(base.get("libraries"))) libs.put(key(Json.text(Json.obj(lib),"name")),lib);
            for(Object lib:patchLibs) libs.put(key(Json.text(Json.obj(lib),"name")),lib);
            Map<String,Object> merged=new LinkedHashMap<String,Object>(base);
            merged.put("libraries",new ArrayList<Object>(libs.values()));
            merged.put("mainClass",patch.get("mainClass"));
            merged.put("minecraftArguments",patch.get("minecraftArguments"));
            merged.remove("arguments");
            merged.put("jar",mc);merged.put("id",mc);
            instance.put("loaderVersion",lv);
            return merged;
        } catch(IllegalArgumentException e) {
            throw new IOException("Malformed Forge installer metadata: "+e.getMessage(),e);
        }
    }
    static String key(String coordinate)throws IOException {
        String[] parts=coordinate.split(":");
        if(parts.length<3||parts.length>4)throw new IOException("Malformed Forge Maven coordinate");
        String ext=parts[2].contains("@")?parts[2].substring(parts[2].indexOf('@')):"@jar";
        return parts[0]+":"+parts[1]+":"+(parts.length==4?parts[3]:"")+ext;
    }
    static void digest(String value)throws IOException {
        if(!value.matches("[0-9a-fA-F]{40}"))throw new IOException("Invalid/missing Forge SHA1 checksum");
    }
    static String remoteDigest(String url,Path path)throws IOException {
        FilesUtil.download(url+".sha1",path,"",-1);
        String value=FilesUtil.read(path).trim().split("\\s+")[0];digest(value);return value;
    }
    static void validateEntries(ZipFile zip,Path scratch)throws IOException {
        Set<String> names=new HashSet<String>();int count=0;
        for(Enumeration<? extends ZipEntry> entries=zip.entries();entries.hasMoreElements();) {
            ZipEntry entry=entries.nextElement();
            if(++count>100000)throw new IOException("Forge installer entry count exceeds limit");
            FilesUtil.safe(scratch,entry.getName());
            if(!names.add(entry.getName()))throw new IOException("Duplicate Forge installer entry");
        }
    }
    static byte[] read(ZipFile zip,String name,long limit)throws IOException {
        ZipEntry e=zip.getEntry(name);
        if(e==null||e.isDirectory())throw new IOException("Forge installer entry missing: "+name);
        if(e.getSize()>limit)throw new IOException("Forge installer entry too large");
        try(InputStream input=zip.getInputStream(e);ByteArrayOutputStream output=new ByteArrayOutputStream()) {
            byte[] buffer=new byte[65536];long total=0;int n;
            while((n=input.read(buffer))>=0) {
                if((total+=n)>limit)throw new IOException("Forge installer entry expanded size exceeds limit");
                output.write(buffer,0,n);
            }
            return output.toByteArray();
        }
    }
    static Map<String,Object> readJson(ZipFile zip,String name)throws IOException {
        return Json.obj(Json.parse(new String(read(zip,name,4*1024*1024),StandardCharsets.UTF_8)));
    }
    static void extract(ZipFile zip,String name,Path target)throws IOException {
        byte[] bytes=read(zip,name,64*1024*1024);
        Files.createDirectories(target.getParent());Path temporary=target.resolveSibling(target.getFileName()+".tmp");
        Files.write(temporary,bytes);FilesUtil.atomic(temporary,target);
    }
}
