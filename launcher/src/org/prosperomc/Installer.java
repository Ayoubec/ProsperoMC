package org.prosperomc;
import java.io.*;
import java.nio.file.*;
import java.util.*;
final class Installer {
    final Main app;
    final Path root;
    final Map<String, String> settings;
    Installer(Main a) {
        app=a;
        root=a.root;
        settings=a.settings;
    }
    static long size(Map<String, Object> m) {
        Object v=m.get("size");
        return v instanceof Number?((Number)v).longValue():-1;
    }
    Map<String, Object> json(Path p)throws IOException {
        return Json.obj(Json.parse(FilesUtil.read(p)));
    }
    Map<String, Object> fetchJson(String url, Path p, String sha, long size)throws IOException {
        FilesUtil.download(url, p, sha, size);
        return json(p);
    }
    Map<String, Object> catalog(boolean refresh)throws IOException {
        Path p=root.resolve("cache/version_manifest_v2.json");
        if(refresh||!Files.isRegularFile(p)) {
            Path temp=p.resolveSibling("manifest-new.json");
            FilesUtil.refresh(settings.getOrDefault("manifestUrl", "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"),temp);
            Map<String,Object> m=json(temp);
            if(!m.containsKey("versions"))throw new IOException("Version manifest lacks versions");
            FilesUtil.atomic(temp, p);
            return m;
        }
        return json(p);
    }
    Map<String, Object> version(String id, Set<String> stack)throws IOException {
        Main.id(id);
        if(!stack.add(id)||stack.size()>16)throw new IOException("Cyclic/deep version inheritance");
        Path p=root.resolve("versions/"+id+"/"+id+".json");
        if(!Files.isRegularFile(p)) {
            Map<String, Object> found=null;
            for(Object o:Json.arr(catalog(false).get("versions"))) {
                Map<String, Object> e=Json.obj(o);
                if(id.equals(Json.text(e, "id"))) {
                    found=e;
                    break;
                }
            }
            if(found==null)throw new IOException("Minecraft version not found: "+id);
            fetchJson(Json.text(found, "url"), p, Json.text(found, "sha1"), size(found));
        }
        Map<String, Object> child=json(p);
        if(!id.equals(Json.text(child, "id")))throw new IOException("Version metadata ID mismatch");
        String parent=Json.text(child, "inheritsFrom");
        if(parent.isEmpty())return child;
        Map<String, Object> result=new LinkedHashMap<String, Object>(version(parent, stack));
        List<Object> libs=new ArrayList<Object>(Json.arr(result.get("libraries")));
        libs.addAll(Json.arr(child.get("libraries")));
        result.putAll(child);
        result.put("libraries", libs);
        if(child.containsKey("arguments")) {
            Map<String, Object> args=new LinkedHashMap<String, Object>();
            Map<String, Object> parentMeta=version(parent, new HashSet<String>());
            Map<String, Object> old=parentMeta.containsKey("arguments")?Json.obj(parentMeta.get("arguments")):Collections.<String, Object>emptyMap();
            Map<String, Object> young=Json.obj(child.get("arguments"));
            for(String key:Arrays.asList("game", "jvm")) {
                List<Object> vals=new ArrayList<Object>(Json.arr(old.get(key)));
                vals.addAll(Json.arr(young.get(key)));
                args.put(key, vals);
            }
            result.put("arguments", args);
        }
        result.put("id", id);
        return result;
    }
    Map<String, Object> version(String id)throws IOException {
        return version(id, new HashSet<String>());
    }
    static boolean rules(Object object) {
        if(object==null)return true;
        boolean allowed=false;
        for(Object v:Json.arr(object)) {
            Map<String, Object> rule=Json.obj(v);
            boolean matches=true;
            Object os=rule.get("os");
            if(os!=null) {
                Map<String, Object> o=Json.obj(os);
                String name=Json.text(o, "name"), arch=Json.text(o, "arch"), version=Json.text(o, "version");
                if(!name.isEmpty()&&!name.equals("windows"))matches=false;
                if(!arch.isEmpty()&&!"amd64".matches(arch)&&!"x86_64".matches(arch))matches=false;
                if(!version.isEmpty()&&!"10.0".matches(version))matches=false;
            }
            if(rule.containsKey("features")) {
                for(Object f:Json.obj(rule.get("features")).values())if(Boolean.TRUE.equals(f))matches=false;
            }
            if(matches)allowed="allow".equals(Json.text(rule, "action"));
        }
        return allowed;
    }
    static String maven(String coordinate)throws IOException {
        String[] a=coordinate.split(":");
        if(a.length<3||a.length>4)throw new IOException("Malformed Maven coordinate");
        String version=a[2], ext="jar";
        int at=version.indexOf('@');
        if(at>=0) {
            ext=version.substring(at+1);
            version=version.substring(0, at);
        }
        return a[0].replace('.', '/')+"/"+a[1]+"/"+version+"/"+a[1]+"-"+version+(a.length==4?"-"+a[3]:"")+"."+ext;
    }
    Path artifact(Map<String, Object> spec, String fallback)throws IOException {
        String rel=Json.text(spec, "path");
        if(rel.isEmpty())rel=fallback;
        Path p=FilesUtil.safe(root.resolve("libraries"), rel);
        String url=Json.text(spec, "url");
        if(url.isEmpty())throw new IOException("Library URL missing: "+rel);
        String hash=Json.text(spec, "sha1");
        long expected=size(spec);
        if(hash.isEmpty()) {
            Path checksum=FilesUtil.safe(root.resolve("cache/maven-sha1"),rel+".sha1");
            FilesUtil.download(url+".sha1",checksum,"",-1);
            String[] words=FilesUtil.read(checksum).trim().split("\\s+");
            if(words.length==0||!words[0].matches("[a-fA-F0-9]{40}"))throw new IOException("Library publisher did not provide a valid SHA1: "+rel);
            hash=words[0];
            spec.put("sha1",hash);
        }
        // Mojang's 1.12.2 metadata references an empty LWJGL artifact whose URL
        // is now gone. Reconstruct only the exact SHA1-verified ZIP bytes.
        if(expected==22&&hash.equalsIgnoreCase("b04f3ee8f5e43fa3b162981b50bb72fe1acabb33")) {
            byte[] empty=new byte[22];
            empty[0]='P';
            empty[1]='K';
            empty[2]=5;
            empty[3]=6;
            Files.createDirectories(p.getParent());
            Files.write(p, empty);
            if(!FilesUtil.valid(p, hash, expected))throw new IOException("Empty library integrity mismatch");
        }
        else FilesUtil.download(url, p, hash, expected);
        return p;
    }
    List<Path> libraries(Map<String, Object> meta, Path natives, boolean install)throws IOException {
        List<Path> cp=new ArrayList<Path>();
        Set<String> seen=new HashSet<String>();
        for(Object o:Json.arr(meta.get("libraries"))) {
            Map<String, Object> lib=Json.obj(o);
            if(!rules(lib.get("rules")))continue;
            String coordinate=Json.text(lib, "name");
            Map<String, Object> downloads=lib.containsKey("downloads")?Json.obj(lib.get("downloads")):Collections.<String, Object>emptyMap();
            Map<String, Object> spec=null;
            if(downloads.containsKey("artifact"))spec=Json.obj(downloads.get("artifact"));
            else if(!lib.containsKey("downloads")&&!coordinate.isEmpty()) {
                String rel=maven(coordinate);
                spec=new LinkedHashMap<String, Object>();
                spec.put("path", rel);
                spec.put("url", (lib.containsKey("url")?Json.text(lib, "url"):"https://libraries.minecraft.net/")+rel);
                if(lib.containsKey("sha1"))spec.put("sha1", lib.get("sha1"));
                else if(!Json.arr(lib.get("checksums")).isEmpty())spec.put("sha1",Json.arr(lib.get("checksums")).get(0));
                lib.put("downloads",Auth.map("artifact",spec));
            }
            if(spec!=null) {
                String rel=Json.text(spec, "path");
                if(rel.isEmpty())rel=maven(coordinate);
                Path p=FilesUtil.safe(root.resolve("libraries"), rel);
                if(install)artifact(spec, rel);
                if(!Files.isRegularFile(p)||!FilesUtil.valid(p, Json.text(spec, "sha1"), size(spec)))throw new IOException("Missing/corrupt library: "+rel);
                if(seen.add(p.toString()))cp.add(p);
                if(install&&coordinate.contains(":natives-windows")&&!coordinate.contains("arm64")&&!coordinate.contains("x86:"))FilesUtil.unzip(p, natives, new HashSet<String>(Arrays.asList("manifest.mf")));
            }
            if(lib.containsKey("natives")) {
                String classifier=Json.text(Json.obj(lib.get("natives")), "windows").replace("${arch}", "64");
                if(!classifier.isEmpty()) {
                    Map<String, Object> classifiers=downloads.containsKey("classifiers")?Json.obj(downloads.get("classifiers")):Collections.<String, Object>emptyMap();
                    Map<String, Object> nativeSpec;
                    if(classifiers.containsKey(classifier))nativeSpec=Json.obj(classifiers.get(classifier));
                    else {
                        String rel=maven(coordinate+":"+classifier);
                        nativeSpec=new LinkedHashMap<String, Object>();
                        nativeSpec.put("path", rel);
                        nativeSpec.put("url", (lib.containsKey("url")?Json.text(lib, "url"):"https://libraries.minecraft.net/")+rel);
                    }
                    String rel=Json.text(nativeSpec, "path");
                    if(rel.isEmpty())rel=maven(coordinate+":"+classifier);
                    Path p=FilesUtil.safe(root.resolve("libraries"), rel);
                    if(install)artifact(nativeSpec, rel);
                    if(!Files.isRegularFile(p)||!FilesUtil.valid(p, Json.text(nativeSpec, "sha1"), size(nativeSpec)))throw new IOException("Missing/corrupt native archive: "+rel);
                    Set<String> ex=new HashSet<String>(Arrays.asList("manifest.mf"));
                    if(lib.containsKey("extract"))for(Object exclude:Json.arr(Json.obj(lib.get("extract")).get("exclude")))ex.add(Json.str(exclude));
                    FilesUtil.unzip(p, natives, ex);
                }
            }
        }
        return cp;
    }
    Map<String, Object> withLoader(Map<String, Object> base, Map<String, String> instance)throws IOException {
        String loader=instance.getOrDefault("loader", "vanilla");
        if(loader.equals("vanilla"))return base;
        if(loader.equals("forge"))return ForgeInstaller.install(this,base,instance);
        if(!loader.equals("fabric")&&!loader.equals("quilt"))throw new IOException("Unsupported loader: "+loader+". Forge/NeoForge installer processors are not implemented; use Fabric or Quilt.");
        String api=settings.getOrDefault(loader+"Api", loader.equals("fabric")?"https://meta.fabricmc.net/v2":"https://meta.quiltmc.org/v3");
        String lv=instance.getOrDefault("loaderVersion", "");
        String mc=instance.get("version");
        if(lv.isEmpty()) {
            Path p=root.resolve("cache/"+loader+"-loaders.json");
            FilesUtil.refresh(api+"/versions/loader/"+mc, p);
            List<Object> candidates=Json.arr(Json.parse(FilesUtil.read(p)));
            for(Object c:candidates) {
                Map<String, Object> item=Json.obj(c);
                Map<String, Object> l=item.containsKey("loader")?Json.obj(item.get("loader")):item;
                if(!Boolean.FALSE.equals(l.get("stable"))) {
                    lv=Json.text(l, "version");
                    break;
                }
            }
            if(lv.isEmpty())throw new IOException("No "+loader+" loader is available for "+mc);
            instance.put("loaderVersion", lv);
        }
        Main.id(lv);
        Path p=root.resolve("cache/"+loader+"-"+mc+"-"+lv+".json");
        if(!Files.isRegularFile(p))FilesUtil.download(api+"/versions/loader/"+mc+"/"+lv+"/profile/json", p, "", -1);
        Map<String, Object> patch=json(p), merged=new LinkedHashMap<String, Object>(base);
        List<Object> libs=new ArrayList<Object>(Json.arr(base.get("libraries")));
        libs.addAll(Json.arr(patch.get("libraries")));
        merged.put("libraries", libs);
        merged.put("mainClass", patch.get("mainClass"));
        if(patch.containsKey("arguments")) {
            Map<String, Object> a=base.containsKey("arguments")?new LinkedHashMap<String, Object>(Json.obj(base.get("arguments"))):new LinkedHashMap<String, Object>();
            Map<String, Object> patchArgs=Json.obj(patch.get("arguments"));
            for(String k:Arrays.asList("game", "jvm")) {
                List<Object> vals=new ArrayList<Object>(Json.arr(a.get(k)));
                vals.addAll(Json.arr(patchArgs.get(k)));
                a.put(k, vals);
            }
            merged.put("arguments", a);
        }
        return merged;
    }
    void install(Map<String, String> instance, Path dir)throws IOException {
        instance.put("installed", "false");
        FilesUtil.properties(dir.resolve("instance.properties"), instance);
        app.progress("installing", "Resolving Minecraft metadata", 0, 1);
        Map<String, Object> meta=withLoader(version(instance.get("version")), instance);
        app.runtimes.ensure(javaMajor(meta),false);
        Path game=dir.resolve(".minecraft"), natives=dir.resolve("natives");
        Files.createDirectories(game);
        FilesUtil.deleteTree(natives);
        Files.createDirectories(natives);
        String jarId=Json.text(meta, "jar");
        if(jarId.isEmpty())jarId=instance.get("version");
        Main.id(jarId);
        Path client=root.resolve("versions/"+jarId+"/"+jarId+".jar");
        Map<String, Object> ds=meta.containsKey("downloads")?Json.obj(meta.get("downloads")):Collections.<String, Object>emptyMap();
        if(ds.containsKey("client")) {
            Map<String, Object> c=Json.obj(ds.get("client"));
            app.progress("installing", "Downloading client", 0, 1);
            FilesUtil.download(Json.text(c, "url"), client, Json.text(c, "sha1"), size(c));
        }
        else if(!Files.isRegularFile(client))throw new IOException("Client archive unavailable for this version");
        app.progress("installing", "Installing libraries and Windows x64 natives", 0, 1);
        libraries(meta, natives, true);
        if(meta.containsKey("assetIndex")) {
            Map<String, Object> ai=Json.obj(meta.get("assetIndex"));
            String aid=Json.text(ai, "id");
            Main.id(aid);
            Map<String, Object> idx=fetchJson(Json.text(ai, "url"), root.resolve("assets/indexes/"+aid+".json"), Json.text(ai, "sha1"), size(ai));
            Map<String, Object> objects=Json.obj(idx.get("objects"));
            int done=0;
            for(Map.Entry<String, Object> e:objects.entrySet()) {
                Map<String, Object> asset=Json.obj(e.getValue());
                String hash=Json.text(asset, "hash");
                if(!hash.matches("[a-f0-9]{40}"))throw new IOException("Invalid asset hash");
                Path target=FilesUtil.safe(root.resolve("assets/objects"), hash.substring(0, 2)+"/"+hash);
                String endpoint=settings.getOrDefault("assetsUrl", "https://resources.download.minecraft.net");
                FilesUtil.download(endpoint+"/"+hash.substring(0, 2)+"/"+hash, target, hash, size(asset));
                if(Boolean.TRUE.equals(idx.get("virtual")))copyAsset(target, root.resolve("assets/virtual/"+aid), e.getKey());
                if(Boolean.TRUE.equals(idx.get("map_to_resources")))copyAsset(target, game.resolve("resources"), e.getKey());
                if(done++%20==0)app.progress("installing", "Assets", done, objects.size());
            }
        }
        if(meta.containsKey("logging")) {
            Map<String, Object> log=Json.obj(meta.get("logging"));
            if(log.containsKey("client")) {
                Map<String, Object> c=Json.obj(log.get("client")), f=Json.obj(c.get("file"));
                String id=Json.text(f, "id");
                Main.id(id);
                FilesUtil.download(Json.text(f, "url"), root.resolve("assets/log_configs/"+id), Json.text(f, "sha1"), size(f));
            }
        }
        meta.put("_clientPath", root.relativize(client).toString().replace('\\', '/'));
        FilesUtil.write(dir.resolve("installed.json"), Json.stringify(meta));
        instance.put("installed", "true");
        FilesUtil.properties(dir.resolve("instance.properties"), instance);
        app.progress("ready", "Minecraft installed", 1, 1);
    }
    void copyAsset(Path from, Path dir, String rel)throws IOException {
        Path p=FilesUtil.safe(dir, rel);
        Files.createDirectories(p.getParent());
        Files.copy(from, p, StandardCopyOption.REPLACE_EXISTING);
    }
    static int javaMajor(Map<String, Object> meta) {
        if(meta.containsKey("javaVersion")) {
            Object n=Json.obj(meta.get("javaVersion")).get("majorVersion");
            if(n instanceof Number)return((Number)n).intValue();
        }
        String id=Json.text(meta, "id");
        if(id.matches("1\\.(1[78])([.].*)?"))return id.startsWith("1.17")?16:17;
        if(id.matches("1\\.(19|20)([.].*)?"))return id.startsWith("1.20.5")||id.startsWith("1.20.6")?21:17;
        return 8;
    }
}
