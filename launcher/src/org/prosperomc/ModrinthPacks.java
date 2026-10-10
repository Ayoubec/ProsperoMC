package org.prosperomc;

import java.io.IOException;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.file.*;
import java.util.*;

/** Modrinth discovery feeds the same verified mrpack importer as local packs. */
final class ModrinthPacks {
    final Main app;
    ModrinthPacks(Main app) { this.app=app; }
    String api() { return app.settings.getOrDefault("modrinthApi","https://api.modrinth.com/v2").replaceAll("/+$",""); }
    Path state() { return app.root.resolve("cache/modrinth-view.properties"); }
    static String text(String value) {
        String clean=value.replace('\r',' ').replace('\n',' ');
        return clean.length()>512?clean.substring(0,512):clean;
    }
    Map<String,Object> fetch(String url,String file) throws IOException {
        Path p=app.root.resolve("cache/"+file);
        FilesUtil.refresh(url,p);
        return app.installer.json(p);
    }
    void search() throws IOException {
        String query=app.request.getOrDefault("query","");
        if(query.length()>128)throw new IOException("Search is too long");
        int offset;
        try { offset=Integer.parseInt(app.request.getOrDefault("offset","0")); }
        catch(NumberFormatException e) { throw new IOException("Invalid search page"); }
        if(offset<0||offset>100000)throw new IOException("Invalid search page");
        app.progress("searching","Searching Modrinth modpacks",0,1);
        String facets=URLEncoder.encode("[[\"project_type:modpack\"]]","UTF-8");
        Map<String,Object> result=fetch(api()+"/search?limit=24&offset="+offset+
            "&index="+(query.isEmpty()?"downloads":"relevance")+"&facets="+facets+
            "&query="+URLEncoder.encode(query,"UTF-8"),"modrinth-search.json");
        Map<String,String> view=Main.stringMap("remote.query",text(query),"remote.offset",Integer.toString(offset),
            "remote.total",Long.toString(result.get("total_hits") instanceof Number ? ((Number)result.get("total_hits")).longValue() : 0),"remote.version.count","0");
        int n=0;
        for(Object item:Json.arr(result.get("hits"))) {
            Map<String,Object> hit=Json.obj(item);
            if(!"modpack".equals(Json.text(hit,"project_type")))continue;
            if(n==24)break;
            view.put("remote.pack."+n+".id",Main.id(Json.text(hit,"project_id")));
            view.put("remote.pack."+n+".name",text(Json.text(hit,"title")));
            view.put("remote.pack."+n+".description",text(Json.text(hit,"description")));
            ++n;
        }
        view.put("remote.pack.count",Integer.toString(n));
        FilesUtil.properties(state(),view);
        app.message=n==0?"No Modrinth modpacks match this search":"Modrinth modpacks loaded";
    }
    static Map<String,Object> packFile(Map<String,Object> version) throws IOException {
        Map<String,Object> selected=null;
        for(Object item:Json.arr(version.get("files"))) {
            Map<String,Object> file=Json.obj(item);
            if(Json.text(file,"filename").toLowerCase(Locale.ROOT).endsWith(".mrpack")) {
                if(selected==null||Boolean.TRUE.equals(file.get("primary")))selected=file;
            }
        }
        return selected;
    }
    void versions() throws IOException {
        String project=Main.id(app.required("projectId"));
        app.progress("searching","Loading modpack releases",0,1);
        Map<String,String> view=FilesUtil.properties(state());
        for(String key:new ArrayList<String>(view.keySet()))if(key.startsWith("remote.version."))view.remove(key);
        view.put("remote.projectId",project);view.put("remote.version.count","0");
        FilesUtil.properties(state(),view);
        Path p=app.root.resolve("cache/modrinth-versions.json");
        FilesUtil.refresh(api()+"/project/"+project+"/version",p);
        int n=0;
        for(Object item:Json.arr(Json.parse(FilesUtil.read(p)))) {
            Map<String,Object> version=Json.obj(item);
            if(packFile(version)==null)continue;
            if(n==64)break;
            List<Object> games=Json.arr(version.get("game_versions")),loaders=Json.arr(version.get("loaders"));
            view.put("remote.version."+n+".id",Main.id(Json.text(version,"id")));
            view.put("remote.version."+n+".name",text(Json.text(version,"name"))+" ["+text(Json.text(version,"version_type"))+"]");
            view.put("remote.version."+n+".game",games.isEmpty()?"":Json.str(games.get(0)));
            view.put("remote.version."+n+".loader",loaders.isEmpty()?"":Json.str(loaders.get(0)));
            ++n;
        }
        view.put("remote.version.count",Integer.toString(n));
        FilesUtil.properties(state(),view);
        app.message=n==0?"This project has no downloadable mrpack releases":"Choose a modpack release";
    }
    void download() throws Exception {
        String project=Main.id(app.required("projectId")),version=Main.id(app.required("packVersion"));
        Map<String,Object> metadata=fetch(api()+"/version/"+version,"modrinth-download.json");
        if(!project.equals(Json.text(metadata,"project_id")))throw new IOException("Modpack release belongs to another project");
        Map<String,Object> file=packFile(metadata);
        if(file==null)throw new IOException("Release has no mrpack file");
        URL url=new URL(Json.text(file,"url"));
        if(!"https".equals(url.getProtocol())||!"cdn.modrinth.com".equalsIgnoreCase(url.getHost())||url.getUserInfo()!=null)
            throw new IOException("Modpack archive must use Modrinth HTTPS CDN");
        Map<String,Object> hashes=Json.obj(file.get("hashes"));
        String sha1=Json.text(hashes,"sha1"),sha512=Json.text(hashes,"sha512");
        if(!sha1.matches("[a-fA-F0-9]{40}")||!sha512.matches("[a-fA-F0-9]{128}"))throw new IOException("Modpack archive hashes missing");
        String instance=Main.id(app.request.getOrDefault("id","modrinth-"+project+"-"+version));
        if(Files.exists(app.dir(instance))) {
            Map<String,String> existing=app.instance(instance);
            if(!project.equals(existing.get("modrinthProject"))||!version.equals(existing.get("modrinthVersion")))
                throw new IOException("An instance with this name already exists");
            if(!"true".equals(existing.get("installed")))app.installer.install(existing,app.dir(instance));
            app.message="Modpack is installed; open Library to play";return;
        }
        Path archive=FilesUtil.safe(app.root.resolve("imports"),project+"-"+version+".mrpack");
        long size=Installer.size(file);
        if(size<=0||size>2L*1024*1024*1024)throw new IOException("Invalid modpack archive size");
        app.progress("downloading","Downloading modpack archive",0,1);
        FilesUtil.download(url.toString(),archive,sha1,size);
        if(!FilesUtil.hash(archive,"SHA-512").equalsIgnoreCase(sha512)) {
            Files.deleteIfExists(archive);throw new IOException("Modpack archive SHA512 mismatch");
        }
        Map<String,String> req=Main.stringMap("id",instance,"source",archive.toString(),
            "name",app.request.getOrDefault("name",text(Json.text(metadata,"name"))));
        Main imported=new Main(app.root,req);
        imported.importPack();
        Map<String,String> created=app.instance(instance);
        created.put("modrinthProject",project);created.put("modrinthVersion",version);
        FilesUtil.properties(app.dir(instance).resolve("instance.properties"),created);
        app.progress("installing","Installing modpack Minecraft and Java",0,1);
        app.installer.install(created,app.dir(instance));
        app.message="Modpack installed as "+instance;
    }
}
