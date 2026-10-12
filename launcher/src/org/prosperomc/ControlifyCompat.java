package org.prosperomc;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

/** Controlify's resource-pack identity override for the title's DualSense bridge. */
final class ControlifyCompat {
    static final String PACK="file/prosperomc-dualsense";
    static final String IDENTIFICATION="assets/controlify/controllers/controller_identification.json5";

    static void select(Path root,Path game,Path client,String mode)throws IOException {
        if(!root.toString().replace('\\','/').equalsIgnoreCase("Z:/data/ProsperoMC"))return;
        configure(game,client,mode);
    }

    static boolean configure(Path game,Path client,String mode)throws IOException {
        if(!"native".equals(mode))return false;
        Path mods=FilesUtil.safe(game,"mods");
        if(!Files.isDirectory(mods))return false;
        boolean supported=false;
        try(DirectoryStream<Path> jars=Files.newDirectoryStream(mods,"*.jar")) {
            for(Path mod:jars) {
                if(!Files.isRegularFile(mod,LinkOption.NOFOLLOW_LINKS))continue;
                try(ZipFile jar=new ZipFile(mod.toFile())) {
                    if(jar.getEntry(IDENTIFICATION)==null ||
                       jar.getEntry("assets/controlify/controllers/font_mappings/dualsense.json")==null)continue;
                    ZipEntry manager=jar.getEntry("dev/isxander/controlify/controller/id/ControllerTypeManager.class");
                    if(manager==null)continue;
                    String symbols=new String(readEntry(jar,manager,512*1024),StandardCharsets.ISO_8859_1);
                    if(!symbols.contains("getResourceStack"))continue;
                    supported=true;break;
                }
            }
        }
        if(!supported)return false;
        Map<String,Object> formats;
        try(ZipFile jar=new ZipFile(client.toFile())) {
            ZipEntry version=jar.getEntry("version.json");
            if(version==null)return false;
            Map<String,Object> v=Json.obj(Json.parse(new String(readEntry(jar,version,64*1024),StandardCharsets.UTF_8)));
            formats=Json.obj(v.get("pack_version"));
        }
        Object value=formats.containsKey("resource_major")?formats.get("resource_major"):formats.get("resource");
        if(!(value instanceof Number))return false;
        int major=((Number)value).intValue(),minor=0;
        if(formats.get("resource_minor") instanceof Number)minor=((Number)formats.get("resource_minor")).intValue();
        if(major<1||major>10000||minor<0||minor>10000)throw new IOException("Invalid client resource-pack format");

        Path options=FilesUtil.safe(game,"options.txt");
        String before=Files.exists(options)?FilesUtil.read(options):"";
        if(before.length()>256*1024)throw new IOException("Minecraft options exceed expected size");
        List<String> lines=new ArrayList<String>();List<Object> packs=new ArrayList<Object>();boolean found=false;
        for(String line:before.split("\\r?\\n")) {
            if(line.startsWith("resourcePacks:")) {
                if(found)throw new IOException("Duplicate Minecraft resourcePacks option");
                Object selection=Json.parse(line.substring("resourcePacks:".length()));
                if(!(selection instanceof List))throw new IOException("Invalid resource-pack selection");
                packs.addAll(Json.arr(selection));found=true;
                for(Object pack:packs)if(!(pack instanceof String))throw new IOException("Invalid resource-pack selection");
                lines.add(null);
            } else lines.add(line);
        }
        packs.removeIf(PACK::equals);packs.add(PACK);
        String selected="resourcePacks:"+Json.stringify(packs);
        if(found)lines.set(lines.indexOf(null),selected);else lines.add(selected);
        String after=String.join("\n",lines);
        if(!after.endsWith("\n"))after+="\n";

        Path pack=FilesUtil.safe(game,"resourcepacks/prosperomc-dualsense");
        Path marker=FilesUtil.safe(pack,"prosperomc-managed.json");
        String ownership="{\"owner\":\"ProsperoMC\",\"schema\":1}\n";
        if(Files.exists(pack)&&(!Files.isRegularFile(marker)||!FilesUtil.read(marker).equals(ownership)))
            throw new IOException("Refusing to replace an unmanaged prosperomc-dualsense resource pack");
        Map<String,Object> metadata=new LinkedHashMap<String,Object>();
        metadata.put("description","ProsperoMC DualSense controller identity");
        if(major<65) {
            metadata.put("pack_format",major);
            metadata.put("supported_formats",Arrays.asList(major,major));
        } else {
            metadata.put("min_format",Arrays.asList(major,minor));
            metadata.put("max_format",Arrays.asList(major,minor));
        }
        // Mark the owned directory first: a partial I/O failure can be repaired
        // on the next launch without mistaking our incomplete pack for a user's.
        writeIfChanged(marker,ownership);
        writeIfChanged(FilesUtil.safe(pack,"pack.mcmeta"),Json.stringify(Collections.singletonMap("pack",metadata))+"\n");
        // The title exposes the physical DualSense as standardized XInput.
        // Override only that bridge identity, using Controlify's own glyphs.
        // SDL capability discovery and rumble keep their actual transport.
        writeIfChanged(FilesUtil.safe(pack,IDENTIFICATION),
            "[{\"name\":\"DualSense Controller\",\"namespace\":\"controlify:dualsense\",\"hids\":[[1118,654]]}]\n");
        if(!after.equals(before)) {
            Path backup=FilesUtil.safe(game,"options-prosperomc-before-dualsense.txt");
            if(!Files.exists(backup))FilesUtil.write(backup,before);
            FilesUtil.write(options,after);
        }
        System.out.println("PS5 Controlify: DualSense identity and PlayStation glyphs enabled; standard input/rumble preserved");
        return true;
    }
    static void writeIfChanged(Path path,String text)throws IOException {
        if(!Files.isRegularFile(path)||!FilesUtil.read(path).equals(text))FilesUtil.write(path,text);
    }
    static byte[] readEntry(ZipFile jar,ZipEntry entry,int limit)throws IOException {
        try(InputStream in=jar.getInputStream(entry);ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            byte[] data=new byte[8192];int n;
            while((n=in.read(data))!=-1) {
                if(out.size()+n>limit)throw new IOException("Controlify metadata exceeds expected size");
                out.write(data,0,n);
            }
            return out.toByteArray();
        }
    }
}
