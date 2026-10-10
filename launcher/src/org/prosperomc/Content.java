package org.prosperomc;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

/** One content manager for an instance's mods, resource packs and shader packs. */
final class Content {
    final Main app;
    final String instance,kind;
    final Map<String,String> metadata;
    Content(Main app)throws IOException {
        this.app=app;instance=Main.id(app.required("id"));metadata=app.instance(instance);
        kind=kind(app.request.getOrDefault("content_kind","mods"));
    }
    static String kind(String value)throws IOException {
        if(!Arrays.asList("mods","resourcepacks","shaderpacks").contains(value))throw new IOException("Choose mods, resource packs or shader packs");
        return value;
    }
    static boolean filename(String kind,String name) {
        if(name.isEmpty()||name.length()>191||name.indexOf('/')>=0||name.indexOf('\\')>=0||name.indexOf(':')>=0||name.matches("(?s).*[\\x00-\\x1f].*"))return false;
        String enabled=name.endsWith(".disabled")?name.substring(0,name.length()-9):name;
        return enabled.toLowerCase(Locale.ROOT).endsWith(kind.equals("mods")?".jar":".zip");
    }
    Path directory()throws IOException { return FilesUtil.safe(app.dir(instance),".minecraft/"+kind); }
    Path file(String name)throws IOException {
        if(!filename(kind,name))throw new IOException(kind.equals("mods")?"Choose a JAR mod":"Choose a ZIP pack");
        return FilesUtil.safe(directory(),name);
    }
    void select()throws IOException {
        FilesUtil.properties(app.root.resolve("cache/content-selection.properties"),Main.stringMap("id",instance,"kind",kind));
    }
    void run(String command)throws Exception {
        select();
        if(command.equals("content-list"))app.message="Content loaded for "+metadata.get("name");
        else if(command.equals("content-import"))add();
        else if(command.equals("content-toggle"))toggle();
        else if(command.equals("content-delete"))remove();
        else if(command.equals("content-search"))search();
        else if(command.equals("content-versions"))versions();
        else if(command.equals("content-download"))download();
        else throw new IOException("Unknown content command");
    }
    void add()throws IOException {
        if(kind.equals("mods")&&"vanilla".equals(metadata.get("loader")))throw new IOException("Select a Fabric, Quilt or supported Forge instance to add mods");
        Path source=Paths.get(app.required("source")).toAbsolutePath().normalize();
        Path imports=app.root.resolve("imports/"+kind).toAbsolutePath().normalize();
        if(!source.startsWith(imports)||!source.getParent().equals(imports))throw new IOException("Place this file in imports/"+kind+" first");
        source=FilesUtil.safe(imports,source.getFileName().toString());
        if(!Files.isRegularFile(source,LinkOption.NOFOLLOW_LINKS))throw new IOException("Import file is missing");
        Path destination=file(source.getFileName().toString());
        validateArchive(source);
        Files.createDirectories(destination.getParent());
        if(Files.exists(destination))throw new IOException("This content file already exists");
        Files.copy(source,destination);
        app.message="Added "+source.getFileName()+" to "+metadata.get("name");
    }
    static void validateArchive(Path source)throws IOException {
        try(ZipFile archive=new ZipFile(source.toFile())) {
            if(archive.size()==0)throw new IOException("Empty content archive");
        }
    }
    void toggle()throws IOException {
        String name=app.required("mod"),enabled=app.required("enabled");
        if(!enabled.equals("true")&&!enabled.equals("false"))throw new IOException("Content enabled must be true or false");
        Path source=file(name);
        if(!Files.isRegularFile(source,LinkOption.NOFOLLOW_LINKS))throw new IOException("Content file not found");
        boolean disable=enabled.equals("false");
        String target=disable?(name.endsWith(".disabled")?name:name+".disabled"):name.replaceFirst("\\.disabled$","");
        if(!target.equals(name)) {
            Path destination=file(target);
            if(Files.exists(destination))throw new IOException("A content file with that name already exists");
            Files.move(source,destination);
        }
        if(disable)unselect(name.replaceFirst("\\.disabled$",""));
        app.message=(disable?"Disabled ":"Enabled ")+target.replaceFirst("\\.disabled$","");
    }
    void remove()throws IOException {
        String name=app.required("mod");Path target=file(name);
        if(!Files.isRegularFile(target,LinkOption.NOFOLLOW_LINKS))throw new IOException("Content file not found");
        unselect(name.replaceFirst("\\.disabled$",""));Files.delete(target);
        app.message="Deleted "+name;
    }
    /** Remove disabled packs from the game's saved selection without changing other settings. */
    void unselect(String name)throws IOException {
        Path game=app.dir(instance).resolve(".minecraft");
        if(kind.equals("resourcepacks")) {
            Path options=game.resolve("options.txt");
            if(!Files.isRegularFile(options))return;
            List<String> lines=Files.readAllLines(options,StandardCharsets.UTF_8);boolean changed=false;
            for(int i=0;i<lines.size();i++) {
                String line=lines.get(i);
                for(String prefix:Arrays.asList("resourcePacks:","incompatibleResourcePacks:"))if(line.startsWith(prefix)) {
                    List<Object> selected=new ArrayList<Object>(Json.arr(Json.parse(line.substring(prefix.length()))));
                    if(selected.remove("file/"+name)|selected.remove(name)) {lines.set(i,prefix+Json.stringify(selected));changed=true;}
                }
            }
            if(changed)FilesUtil.write(options,String.join("\n",lines)+"\n");
        } else if(kind.equals("shaderpacks")) {
            for(String config:Arrays.asList("config/iris.properties","iris.properties","optionsshaders.txt")) {
                Path options=game.resolve(config);if(!Files.isRegularFile(options))continue;
                List<String> lines=Files.readAllLines(options,StandardCharsets.UTF_8);boolean changed=false;
                for(int i=0;i<lines.size();i++) {
                    String line=lines.get(i);
                    if(line.equals("shaderPack="+name)) {lines.set(i,"shaderPack=");changed=true;}
                    if(line.equals("shaderPack:"+name)) {lines.set(i,"shaderPack:");changed=true;}
                }
                if(changed)FilesUtil.write(options,String.join("\n",lines)+"\n");
            }
        }
    }
    String api() {return app.settings.getOrDefault("modrinthApi","https://api.modrinth.com/v2").replaceAll("/+$","");}
    String projectType() {return kind.equals("mods")?"mod":kind.equals("resourcepacks")?"resourcepack":"shader";}
    String versionQuery()throws IOException {
        String query="?game_versions="+URLEncoder.encode(Json.stringify(Arrays.asList(metadata.get("version"))),"UTF-8");
        if(kind.equals("mods"))query+="&loaders="+URLEncoder.encode(Json.stringify(Arrays.asList(metadata.get("loader"))),"UTF-8");
        return query;
    }
    Object fetch(String url,String name)throws IOException {
        Path target=app.root.resolve("cache/"+name);FilesUtil.refresh(url,target);return Json.parse(FilesUtil.read(target));
    }
    void search()throws IOException {
        String query=app.request.getOrDefault("query","");if(query.length()>128)throw new IOException("Search is too long");
        int offset;
        try {offset=Integer.parseInt(app.request.getOrDefault("offset","0"));}catch(NumberFormatException e){throw new IOException("Invalid search page");}
        if(offset<0||offset>100000)throw new IOException("Invalid search page");
        new ModrinthPacks(app).resetSearch(query,offset);
        List<Object> facets=new ArrayList<Object>();
        facets.add(Arrays.asList("project_type:"+projectType()));facets.add(Arrays.asList("versions:"+metadata.get("version")));
        if(kind.equals("mods"))facets.add(Arrays.asList("categories:"+metadata.get("loader")));
        Map<String,Object> result=Json.obj(fetch(api()+"/search?limit=24&offset="+offset+"&index="+(query.isEmpty()?"downloads":"relevance")+
            "&facets="+URLEncoder.encode(Json.stringify(facets),"UTF-8")+"&query="+URLEncoder.encode(query,"UTF-8"),"content-search.json"));
        Map<String,String> view=Main.stringMap("remote.query",ModrinthPacks.text(query),"remote.offset",Integer.toString(offset),
            "remote.total",Long.toString(result.get("total_hits") instanceof Number?((Number)result.get("total_hits")).longValue():0),"remote.version.count","0");
        int n=0;
        for(Object item:Json.arr(result.get("hits"))) {
            Map<String,Object> hit=Json.obj(item);
            if(!projectType().equals(Json.text(hit,"project_type")))continue;
            if(n==24)break;
            String prefix="remote.pack."+n+".";
            view.put(prefix+"id",Main.id(Json.text(hit,"project_id")));view.put(prefix+"name",ModrinthPacks.text(Json.text(hit,"title")));
            view.put(prefix+"description",ModrinthPacks.text(Json.text(hit,"description")));view.put(prefix+"icon",Icons.cache(app,Json.text(hit,"icon_url")));n++;
        }
        view.put("remote.pack.count",Integer.toString(n));FilesUtil.properties(app.root.resolve("cache/modrinth-view.properties"),view);
        app.message=n==0?"No compatible "+kind+" found for "+metadata.get("version"):"Compatible "+kind+" loaded";
    }
    List<Object> releases(String project)throws IOException {
        return Json.arr(fetch(api()+"/project/"+Main.id(project)+"/version"+versionQuery(),"content-versions.json"));
    }
    boolean compatible(Map<String,Object> release) {
        if(!Json.arr(release.get("game_versions")).contains(metadata.get("version")))return false;
        return !kind.equals("mods")||Json.arr(release.get("loaders")).contains(metadata.get("loader"));
    }
    void versions()throws IOException {
        String project=Main.id(app.required("projectId"));
        Map<String,String> view=FilesUtil.properties(app.root.resolve("cache/modrinth-view.properties"));
        for(String key:new ArrayList<String>(view.keySet()))if(key.startsWith("remote.version."))view.remove(key);
        view.put("remote.projectId",project);view.put("remote.version.count","0");
        FilesUtil.properties(app.root.resolve("cache/modrinth-view.properties"),view);int n=0;
        for(Object entry:releases(project)) {
            Map<String,Object> release=Json.obj(entry);if(!compatible(release))continue;if(n==64)break;
            String prefix="remote.version."+n+".";
            view.put(prefix+"id",Main.id(Json.text(release,"id")));view.put(prefix+"name",ModrinthPacks.text(Json.text(release,"name"))+" ["+Json.text(release,"version_type")+"]");
            view.put(prefix+"game",metadata.get("version"));view.put(prefix+"loader",kind.equals("mods")?metadata.get("loader"):projectType());n++;
        }
        view.put("remote.version.count",Integer.toString(n));FilesUtil.properties(app.root.resolve("cache/modrinth-view.properties"),view);
        app.message=n==0?"No compatible releases":"Choose a compatible release";
    }
    void download()throws IOException {
        String project=Main.id(app.required("projectId")),version=Main.id(app.required("packVersion"));
        if(kind.equals("mods")) {
            if("vanilla".equals(metadata.get("loader")))throw new IOException("Mods need a mod loader; choose a Fabric, Quilt or Forge instance");
            app.downloadModVersion(project,version,metadata,instance,api(),new HashMap<String,String>(),0);
        } else {
            Map<String,Object> release=null;
            for(Object entry:releases(project))if(version.equals(Json.text(Json.obj(entry),"id"))) {release=Json.obj(entry);break;}
            if(release==null||!compatible(release))throw new IOException("This release does not support the selected Minecraft version");
            Map<String,Object> selected=null;
            for(Object entry:Json.arr(release.get("files"))) {
                Map<String,Object> candidate=Json.obj(entry);if(!filename(kind,Json.text(candidate,"filename")))continue;
                if(selected==null||Boolean.TRUE.equals(candidate.get("primary")))selected=candidate;
            }
            if(selected==null)throw new IOException("Release has no downloadable ZIP pack");
            Map<String,Object> hashes=Json.obj(selected.get("hashes"));String sha=Json.text(hashes,"sha1");long size=Installer.size(selected);
            if(!sha.matches("[a-fA-F0-9]{40}")||size<=0||size>2L*1024*1024*1024)throw new IOException("Pack download integrity metadata missing");
            Path destination=file(Json.text(selected,"filename"));
            FilesUtil.download(Json.text(selected,"url"),destination,sha,size);validateArchive(destination);
        }
        app.message="Installed compatible "+kind+" in "+metadata.get("name")+"; choose resource/shader packs in Minecraft settings";
    }
    static void view(Main app,Map<String,String> view)throws IOException {
        Map<String,String> selected=FilesUtil.properties(app.root.resolve("cache/content-selection.properties"));
        String instance=selected.getOrDefault("id",""),kind=selected.getOrDefault("kind","mods");
        if(app.request.containsKey("id"))instance=app.request.get("id");
        if(app.request.containsKey("content_kind"))kind=app.request.get("content_kind");
        int n=0;
        if(!instance.isEmpty())try {
            Main.id(instance);Content.kind(kind);app.instance(instance);
            Path folder=FilesUtil.safe(app.dir(instance),".minecraft/"+kind);
            List<Path> files=new ArrayList<Path>();
            if(Files.isDirectory(folder))try(DirectoryStream<Path> stream=Files.newDirectoryStream(folder)) {
                for(Path file:stream)if(Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)&&filename(kind,file.getFileName().toString()))files.add(file);
            }
            Collections.sort(files);
            for(Path file:files) {if(n==128)break;String name=file.getFileName().toString();view.put("mod."+n+".name",name);view.put("mod."+n+".enabled",Boolean.toString(!name.endsWith(".disabled")));n++;}
            view.put("content.instance",instance);view.put("content.kind",kind);
        } catch(IOException ignored) { /* Deleted/stale selection is harmless. */ }
        view.put("mod.count",Integer.toString(n));
    }
}
