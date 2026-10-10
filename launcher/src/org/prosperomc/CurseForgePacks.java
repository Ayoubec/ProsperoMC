package org.prosperomc;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** CurseForge's official API; publisher distribution restrictions are respected. */
final class CurseForgePacks {
    final Main app;
    CurseForgePacks(Main app) {this.app=app;}
    String api() {return app.settings.getOrDefault("curseforgeApi","https://api.curseforge.com/v1").replaceAll("/+$","");}
    static String number(String value)throws IOException {
        if(!value.matches("[1-9][0-9]{0,9}"))throw new IOException("Invalid CurseForge project/file ID");return value;
    }
    static String number(Object value)throws IOException {
        if(!(value instanceof Number)||((Number)value).doubleValue()!=((Number)value).longValue())throw new IOException("Invalid CurseForge project/file ID");
        return number(Long.toString(((Number)value).longValue()));
    }
    String key()throws IOException {
        String key=FilesUtil.properties(app.root.resolve("private/curseforge.properties")).getOrDefault("apiKey","");
        if(key.isEmpty())throw new IOException("CurseForge needs your API key. Configure private/curseforge.properties (apiKey=...) first; see README CurseForge setup.");
        if(key.length()>512||key.matches("(?s).*[\\x00-\\x1f].*"))throw new IOException("Invalid CurseForge API key configuration");
        return key;
    }
    Map<String,Object> fetch(String suffix)throws IOException {
        URL url=new URL(api()+suffix);
        boolean local="http".equals(url.getProtocol())&&"127.0.0.1".equals(url.getHost());
        if(url.getUserInfo()!=null||(!local&&(!"https".equals(url.getProtocol())||!"api.curseforge.com".equalsIgnoreCase(url.getHost()))))
            throw new IOException("CurseForge API must use its official HTTPS endpoint");
        HttpURLConnection connection=(HttpURLConnection)url.openConnection();
        connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(20000);connection.setReadTimeout(30000);
        connection.setRequestProperty("x-api-key",key());connection.setRequestProperty("Accept","application/json");
        connection.setRequestProperty("User-Agent","ProsperoMC/1.0 (Minecraft Java launcher)");
        try {
            int status=connection.getResponseCode();
            if(status==401||status==403)throw new IOException("CurseForge rejected the configured API key; check your API access");
            if(status!=200)throw new IOException("CurseForge API returned HTTP "+status);
            try(InputStream in=connection.getInputStream()) {
                return Json.obj(Json.parse(new String(FabricMods.read(in,32*1024*1024),StandardCharsets.UTF_8)));
            }
        } finally {connection.disconnect();}
    }
    Path state() {return app.root.resolve("cache/modrinth-view.properties");}
    Map<String,Object> project(String id)throws IOException {return Json.obj(fetch("/mods/"+number(id)).get("data"));}
    Map<String,Object> file(String project,String id)throws IOException {
        Map<String,Object> file=Json.obj(fetch("/mods/"+number(project)+"/files/"+number(id)).get("data"));
        if(!project.equals(number(file.get("modId")))||!id.equals(number(file.get("id"))))throw new IOException("CurseForge file belongs to another project");
        return file;
    }
    void search()throws IOException {
        String query=app.request.getOrDefault("query","");if(query.length()>128)throw new IOException("Search is too long");
        int offset;
        try {offset=Integer.parseInt(app.request.getOrDefault("offset","0"));}catch(NumberFormatException e){throw new IOException("Invalid search page");}
        if(offset<0||offset>10000)throw new IOException("Invalid search page");
        new ModrinthPacks(app).resetSearch(query,offset);
        app.progress("searching","Searching CurseForge modpacks",0,1);
        Map<String,Object> result=fetch("/mods/search?gameId=432&classId=4471&pageSize=24&index="+offset+
            "&sortField=2&sortOrder=desc&searchFilter="+URLEncoder.encode(query,"UTF-8"));
        Map<String,Object> pagination=result.containsKey("pagination")?Json.obj(result.get("pagination")):Collections.<String,Object>emptyMap();
        Map<String,String> view=Main.stringMap("remote.query",ModrinthPacks.text(query),"remote.offset",Integer.toString(offset),
            "remote.total",Long.toString(pagination.get("totalCount") instanceof Number?((Number)pagination.get("totalCount")).longValue():0),"remote.version.count","0");
        int n=0;
        for(Object item:Json.arr(result.get("data"))) {
            if(n==24)break;Map<String,Object> project=Json.obj(item);String prefix="remote.pack."+n+".";
            view.put(prefix+"id",number(project.get("id")));view.put(prefix+"name",ModrinthPacks.text(Json.text(project,"name")));
            view.put(prefix+"description",ModrinthPacks.text(Json.text(project,"summary")));
            String logo=project.get("logo") instanceof Map?Json.text(Json.obj(project.get("logo")),"thumbnailUrl"):"";
            view.put(prefix+"icon",Icons.cache(app,logo));n++;
        }
        view.put("remote.pack.count",Integer.toString(n));FilesUtil.properties(state(),view);
        app.message=n==0?"No CurseForge modpacks found":"CurseForge modpacks loaded";
    }
    void versions()throws IOException {
        String project=number(app.required("projectId"));
        Map<String,String> view=FilesUtil.properties(state());
        for(String key:new ArrayList<String>(view.keySet()))if(key.startsWith("remote.version."))view.remove(key);
        view.put("remote.projectId",project);view.put("remote.version.count","0");FilesUtil.properties(state(),view);int n=0;
        for(Object entry:Json.arr(fetch("/mods/"+project+"/files?pageSize=64&index=0").get("data"))) {
            Map<String,Object> file=Json.obj(entry);
            if(!Json.text(file,"fileName").toLowerCase(Locale.ROOT).endsWith(".zip")||Boolean.FALSE.equals(file.get("isAvailable")))continue;
            if(n==64)break;String game="",loader="vanilla";
            for(Object value:Json.arr(file.get("gameVersions"))) {
                String version=Json.str(value);
                if(version.matches("[0-9][A-Za-z0-9_.+-]{0,63}"))game=version;
                if(Arrays.asList("Fabric","Quilt","Forge","NeoForge").contains(version))loader=version.toLowerCase(Locale.ROOT);
            }
            String prefix="remote.version."+n+".";
            String type=file.get("releaseType") instanceof Number?(((Number)file.get("releaseType")).intValue()==1?"release":((Number)file.get("releaseType")).intValue()==2?"beta":"alpha"):"release";
            view.put(prefix+"id",number(file.get("id")));view.put(prefix+"name",ModrinthPacks.text(Json.text(file,"displayName"))+" ["+type+"]");
            view.put(prefix+"game",game);view.put(prefix+"loader",loader);n++;
        }
        view.put("remote.version.count",Integer.toString(n));FilesUtil.properties(state(),view);
        app.message=n==0?"No downloadable CurseForge pack releases":"Choose a CurseForge modpack release";
    }
    Path downloadFile(Map<String,Object> project,Map<String,Object> file,Path destination)throws IOException {
        String id=number(file.get("id"));
        if(Boolean.FALSE.equals(project.get("allowModDistribution"))||Json.text(file,"downloadUrl").isEmpty())
            throw new IOException("CurseForge download is unavailable for "+Json.text(project,"name")+"; the publisher may block third-party downloads. Import a permitted exported pack instead.");
        URL url=new URL(Json.text(file,"downloadUrl"));
        boolean local="http".equals(url.getProtocol())&&"127.0.0.1".equals(url.getHost())&&api().startsWith("http://127.0.0.1:");
        if(url.getUserInfo()!=null||(!local&&(!"https".equals(url.getProtocol())||!Arrays.asList("edge.forgecdn.net","mediafilez.forgecdn.net","media.forgecdn.net").contains(url.getHost().toLowerCase(Locale.ROOT)))))
            throw new IOException("CurseForge downloads must use its HTTPS CDN");
        Object length=file.get("fileLength");
        if(!(length instanceof Number))throw new IOException("CurseForge file size is missing");
        long size=((Number)length).longValue();
        if(((Number)length).doubleValue()!=size||size<=0||size>2L*1024*1024*1024)throw new IOException("Invalid CurseForge file size");
        String sha1="",md5="";
        for(Object entry:Json.arr(file.get("hashes"))) {
            Map<String,Object> hash=Json.obj(entry);Object algorithm=hash.get("algo");if(!(algorithm instanceof Number))continue;
            if(((Number)algorithm).intValue()==1)sha1=Json.text(hash,"value");
            else if(((Number)algorithm).intValue()==2)md5=Json.text(hash,"value");
        }
        if((!sha1.isEmpty()&&!sha1.matches("[A-Fa-f0-9]{40}"))||(!md5.isEmpty()&&!md5.matches("[A-Fa-f0-9]{32}"))||(sha1.isEmpty()&&md5.isEmpty()))
            throw new IOException("CurseForge download hashes are missing or invalid");
        Path cached=FilesUtil.safe(app.root.resolve("cache/curseforge-downloads"),id+".zip");
        FilesUtil.download(url.toString(),cached,sha1,size);
        if(!md5.isEmpty()&&!FilesUtil.hash(cached,"MD5").equalsIgnoreCase(md5)) {Files.deleteIfExists(cached);throw new IOException("CurseForge download hash mismatch");}
        Content.validateArchive(cached);Files.createDirectories(destination.getParent());
        Files.copy(cached,destination,StandardCopyOption.REPLACE_EXISTING);return destination;
    }
    void download()throws Exception {
        String projectId=number(app.required("projectId")),fileId=number(app.required("packVersion"));
        String instance=Main.id(app.request.getOrDefault("id","curseforge-"+projectId+"-"+fileId));
        if(Files.exists(app.dir(instance))) {
            Map<String,String> existing=app.instance(instance);
            if(!projectId.equals(existing.get("curseforgeProject"))||!fileId.equals(existing.get("curseforgeFile")))throw new IOException("An instance with this ID already exists");
            if(!"true".equals(existing.get("installed")))app.installer.install(existing,app.dir(instance));
            app.message="CurseForge modpack is installed";return;
        }
        Map<String,Object> project=project(projectId),file=file(projectId,fileId);
        if(!(project.get("classId") instanceof Number)||((Number)project.get("classId")).intValue()!=4471)throw new IOException("Choose a CurseForge Minecraft modpack project");
        Path archive=FilesUtil.safe(app.root.resolve("imports"),"curseforge-"+projectId+"-"+fileId+".zip");downloadFile(project,file,archive);
        Main imported=new Main(app.root,Main.stringMap("id",instance,"source",archive.toString(),"name",app.request.getOrDefault("name",ModrinthPacks.text(Json.text(project,"name")))));
        imported.importPack();Map<String,String> created=app.instance(instance);
        created.put("curseforgeProject",projectId);created.put("curseforgeFile",fileId);
        String logo=project.get("logo") instanceof Map?Json.text(Json.obj(project.get("logo")),"thumbnailUrl"):"";
        String icon=Icons.cache(app,logo);
        if(!icon.isEmpty()) {
            Path cached=Paths.get(icon.startsWith("/data/ProsperoMC/")?"Z:"+icon:icon);
            if(Icons.valid(cached)) {Files.copy(cached,app.dir(instance).resolve("icon.png"),StandardCopyOption.REPLACE_EXISTING);created.put("icon","icon.png");}
        }
        FilesUtil.properties(app.dir(instance).resolve("instance.properties"),created);
        app.installer.install(created,app.dir(instance));app.message="CurseForge modpack installed as "+instance;
    }
    void importManifest(Path pack,Path destination,String instance)throws IOException {
        Map<String,Object> manifest=app.installer.json(pack.resolve("manifest.json"));
        if(!"minecraftModpack".equals(Json.text(manifest,"manifestType"))||!(manifest.get("manifestVersion") instanceof Number)||((Number)manifest.get("manifestVersion")).doubleValue()!=1)
            throw new IOException("Unsupported CurseForge manifest format");
        Map<String,Object> minecraft=Json.obj(manifest.get("minecraft"));String version=Main.id(Json.text(minecraft,"version")),loader="vanilla",loaderVersion="";
        List<Object> loaders=Json.arr(minecraft.get("modLoaders"));
        Map<String,Object> chosen=null;
        for(Object entry:loaders) {Map<String,Object> candidate=Json.obj(entry);if(chosen==null||Boolean.TRUE.equals(candidate.get("primary")))chosen=candidate;}
        if(chosen!=null) {
            String value=Json.text(chosen,"id");int split=value.indexOf('-');
            if(split<1)throw new IOException("Invalid CurseForge mod loader");
            loader=value.substring(0,split);loaderVersion=Main.id(value.substring(split+1));
            if(!Arrays.asList("fabric","quilt","forge").contains(loader))throw new IOException("Unsupported CurseForge loader: "+loader+"; modern Forge/NeoForge installers are not implemented");
            if(loader.equals("forge")&&!version.equals("1.12.2"))throw new IOException("Forge support currently requires Minecraft 1.12.2; modern Forge/NeoForge installers are not implemented");
        }
        String name=app.request.getOrDefault("name",Json.text(manifest,"name"));Main.validateName(name);
        List<Object> files=Json.arr(manifest.get("files"));if(files.size()>10000)throw new IOException("Too many CurseForge pack files");
        if(!files.isEmpty())key();
        Path game=destination.resolve(".minecraft");Files.createDirectories(game.resolve("mods"));Set<String> seen=new HashSet<String>();Set<Path> targets=new HashSet<Path>();long total=0;
        for(Object entry:files) {
            Map<String,Object> reference=Json.obj(entry);String projectId=number(reference.get("projectID")),fileId=number(reference.get("fileID"));
            if(!seen.add(projectId+"/"+fileId))throw new IOException("Duplicate CurseForge pack file");
            Map<String,Object> project=project(projectId),file=file(projectId,fileId);String filename=Json.text(file,"fileName");
            String kind=filename.toLowerCase(Locale.ROOT).endsWith(".jar")?"mods":project.get("classId") instanceof Number&&((Number)project.get("classId")).intValue()==6552?"shaderpacks":"resourcepacks";
            if(!Content.filename(kind,filename)||filename.endsWith(".disabled"))throw new IOException("Unsupported CurseForge content filename");
            Path target=FilesUtil.safe(game,kind+"/"+filename);
            if(!targets.add(target))throw new IOException("Duplicate CurseForge content filename");
            if(!(file.get("fileLength") instanceof Number))throw new IOException("CurseForge file size is missing");
            long size=((Number)file.get("fileLength")).longValue();
            if(size<=0||size>2L*1024*1024*1024||(total+=size)>4L*1024*1024*1024)throw new IOException("CurseForge pack download size limit");
            downloadFile(project,file,target);
        }
        String overrides=Json.text(manifest,"overrides");
        if(!overrides.isEmpty()) {Path source=FilesUtil.safe(pack,overrides);if(Files.isDirectory(source))FilesUtil.copyTree(source,game);}
        Map<String,String> metadata=Main.stringMap("id",instance,"name",name,"version",version,"loader",loader,"loaderVersion",loaderVersion,"installed","false");
        Icons.importIcon(pack,destination,Collections.<String,String>emptyMap(),metadata);
        FilesUtil.properties(destination.resolve("instance.properties"),metadata);app.writePolyMC(destination,metadata);
        app.message="CurseForge modpack imported; install to fetch Minecraft and Java";
    }
}
