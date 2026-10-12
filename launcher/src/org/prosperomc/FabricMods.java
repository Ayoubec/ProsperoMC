package org.prosperomc;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

/** Report missing enabled Fabric dependencies before its desktop error dialog starts. */
final class FabricMods {
    static final class Mod {
        final String id,name,file;final Set<String> dependencies;
        Mod(String id,String name,String file,Set<String> dependencies) {this.id=id;this.name=name;this.file=file;this.dependencies=dependencies;}
    }
    static byte[] read(InputStream in,int limit)throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int count=0,n;
        while((n=in.read(buffer))>=0) {if((count+=n)>limit)throw new IOException("Mod metadata exceeds size limit");out.write(buffer,0,n);}
        return out.toByteArray();
    }
    static void inspect(byte[] archive,String file,List<Mod> mods,Set<String> available,int depth)throws IOException {
        if(depth>4||mods.size()>2048)throw new IOException("Too many nested mods");
        byte[] metadata=null;Map<String,byte[]> nested=new HashMap<String,byte[]>();
        try(ZipInputStream zip=new ZipInputStream(new ByteArrayInputStream(archive))) {
            ZipEntry entry;
            while((entry=zip.getNextEntry())!=null) {
                if(entry.getName().equals("fabric.mod.json"))metadata=read(zip,1024*1024);
                else if(entry.getName().endsWith(".jar"))nested.put(entry.getName(),read(zip,32*1024*1024));
            }
        }
        if(metadata==null)return;
        Map<String,Object> json=Json.obj(Json.parseFabric(new String(metadata,StandardCharsets.UTF_8)));
        if("server".equals(Json.text(json,"environment")))return;
        String id=Json.text(json,"id");if(id.isEmpty())return;
        available.add(id);
        if(json.containsKey("provides"))for(Object alias:Json.arr(json.get("provides")))available.add(Json.str(alias));
        Set<String> dependencies=new LinkedHashSet<String>();
        if(json.containsKey("depends"))dependencies.addAll(Json.obj(json.get("depends")).keySet());
        mods.add(new Mod(id,ModrinthPacks.text(Json.text(json,"name").isEmpty()?id:Json.text(json,"name")),file,dependencies));
        if(json.containsKey("jars"))for(Object entry:Json.arr(json.get("jars"))) {
            String name=Json.text(Json.obj(entry),"file");byte[] jar=nested.get(name);
            if(jar!=null)inspect(jar,file+"!"+name,mods,available,depth+1);
        }
    }
    static void check(Main app,Path instance,Map<String,String> metadata)throws IOException {
        if(!"fabric".equals(metadata.get("loader")))return;
        Path folder=FilesUtil.safe(instance,".minecraft/mods");if(!Files.isDirectory(folder))return;
        List<Mod> mods=new ArrayList<Mod>();Set<String> available=new HashSet<String>(Arrays.asList("minecraft","java","fabricloader"));
        try(DirectoryStream<Path> files=Files.newDirectoryStream(folder,"*.jar")) {
            for(Path file:files) {
                if(!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS))continue;
                // Read only declared nested archives, retaining the parent on disk.
                try(ZipFile zip=new ZipFile(file.toFile())) {
                    ZipEntry entry=zip.getEntry("fabric.mod.json");if(entry==null)continue;
                    byte[] descriptor;
                    try(InputStream in=zip.getInputStream(entry)){descriptor=read(in,1024*1024);}
                    Map<String,Object> json=Json.obj(Json.parseFabric(new String(descriptor,StandardCharsets.UTF_8)));
                    ByteArrayOutputStream out=new ByteArrayOutputStream();
                    try(ZipOutputStream compact=new ZipOutputStream(out)) {
                        compact.putNextEntry(new ZipEntry("fabric.mod.json"));compact.write(descriptor);compact.closeEntry();
                        if(json.containsKey("jars"))for(Object item:Json.arr(json.get("jars"))) {
                            String name=Json.text(Json.obj(item),"file");ZipEntry child=zip.getEntry(name);if(child==null)continue;
                            compact.putNextEntry(new ZipEntry(name));
                            try(InputStream in=zip.getInputStream(child)){compact.write(read(in,32*1024*1024));}compact.closeEntry();
                        }
                    }
                    inspect(out.toByteArray(),file.getFileName().toString(),mods,available,0);
                } catch(IllegalArgumentException e) {throw new IOException("Invalid Fabric metadata in "+file.getFileName()+": "+e.getMessage(),e);}
            }
        }
        List<String> missing=new ArrayList<String>();
        for(Mod mod:mods)for(String dependency:mod.dependencies)if(!available.contains(dependency)&&missing.size()<5)missing.add(mod.name+" needs "+dependency);
        if(!missing.isEmpty())throw new IOException("Missing enabled mod dependencies: "+String.join("; ",missing)+". Enable or install them in Content.");
    }
}
