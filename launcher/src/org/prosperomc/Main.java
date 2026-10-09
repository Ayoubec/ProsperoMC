package org.prosperomc;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.*;
import java.nio.channels.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.security.*;
import java.util.*;
import java.util.zip.*;
/** Minecraft-only headless launcher used by the PS5 frontend and host CLI. */
public final class Main {
    final Path root;
    final Map<String, String> settings;
    final Map<String, String> request;
    final Map<String, String> authView=new LinkedHashMap<String, String>();
    String message="Ready", status="ready";
    final Installer installer;
    final Auth auth;
    final JavaRuntime runtimes;
    Main(Path root, Map<String, String> req)throws IOException {
        this.root=root.toAbsolutePath().normalize();
        Files.createDirectories(this.root);
        settings=FilesUtil.properties(this.root.resolve("settings.properties"));
        request=req;
        installer=new Installer(this);
        auth=new Auth(this);
        runtimes=new JavaRuntime(this);
    }
    public static void main(String[] args)throws Exception {
        Path root=null, requestPath=null, plan=null;
        boolean serve=false;
        for(int i=0; i<args.length; i++) {
            String a=args[i];
            if(a.equals("--root")&&i+1<args.length)root=Paths.get(args[++i]);
            else if(a.equals("--request")&&i+1<args.length)requestPath=Paths.get(args[++i]);
            else if(a.equals("--execute-plan")&&i+1<args.length)plan=Paths.get(args[++i]);
            else if(a.equals("--serve"))serve=true;
            else throw new IllegalArgumentException("Usage: --root PATH --request PATH | --execute-plan PATH");
        }
        if(root==null)throw new IllegalArgumentException("--root is required");
        if(root.toString().replace('\\','/').equalsIgnoreCase("Z:/data/ProsperoMC")
                &&System.getProperty("java.specification.version").equals("1.8"))Ps5Compat.localAddress();
        if(serve) {
            if(plan!=null||requestPath!=null)throw new IllegalArgumentException("--serve cannot be combined with a request or plan");
            serve(root);
            return;
        }
        if(plan!=null) {
            Main app=new Main(root, Collections.<String, String>emptyMap());
            app.execute(plan);
            return;
        }
        if(requestPath==null)throw new IllegalArgumentException("--request is required");
        if(!perform(root,requestPath))System.exit(1);
    }
    /** One JVM serves launcher work while the native controller UI remains visible. */
    static void serve(Path root)throws Exception {
        Files.createDirectories(root);
        Path queued=root.resolve("request.properties"), active=root.resolve("request.inflight.properties");
        FilesUtil.properties(root.resolve("backend-ready.properties"),stringMap("ready","true"));
        for(;;) {
            if(!Files.isRegularFile(queued)) { Thread.sleep(50); continue; }
            FilesUtil.atomic(queued,active);
            String command=FilesUtil.properties(active).getOrDefault("command","");
            boolean ok=perform(root,active);
            Files.deleteIfExists(active);
            // Minecraft uses its own selected JVM in a fresh title process.
            if(ok&&command.equals("prepare-launch"))return;
        }
    }
    static boolean perform(Path root,Path requestPath)throws Exception {
        Main app;
        try { app=new Main(root,FilesUtil.properties(requestPath)); }
        catch(IOException e) {
            String failure="Invalid launcher request/settings: "+e.getMessage();
            FilesUtil.properties(root.resolve("response.properties"),stringMap("ok","false","command","","message",failure));
            FilesUtil.properties(root.resolve("launcher-view.properties"),stringMap("status","error","detail",failure,"instance.count","0","version.count","0","mod.count","0"));
            System.err.println("ERROR: "+failure);
            return false;
        }
        String command=app.request.getOrDefault("command", "");
        boolean ok=false;
        try(FileChannel channel=FileChannel.open(app.root.resolve("launcher.lock"), StandardOpenOption.CREATE, StandardOpenOption.WRITE); FileLock lock=channel.tryLock()) {
            if(lock==null)throw new IOException("Another launcher operation is running");
            app.command(command);
            ok=true;
        }
        catch(Exception e) {
            app.status="error";
            app.message=e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();
            // Record cause types and frames without request/account values.
            for(Throwable t=e;t!=null;t=t.getCause()) {
                System.err.println("Launcher cause: "+t.getClass().getName());
                for(StackTraceElement frame:t.getStackTrace())System.err.println("  at "+frame);
            }
        }
        try {
            app.view();
            app.progress(app.status, app.message, ok?1:0, 1);
        }
        catch(Exception e) {
            if(ok)app.message="Failed to write launcher state: "+e.getClass().getSimpleName();
            ok=false;
            app.status="error";
            FilesUtil.properties(app.root.resolve("launcher-view.properties"),stringMap("status","error","detail",app.message,"instance.count","0","version.count","0","mod.count","0"));
        }
        FilesUtil.properties(app.root.resolve("response.properties"), stringMap("ok", Boolean.toString(ok), "command", command, "message", app.message));
        System.out.println((ok?"OK: ":"ERROR: ")+app.message);
        return ok;
    }
    static Map<String, String> stringMap(String... kv) {
        Map<String, String> m=new LinkedHashMap<String, String>();
        for(int i=0; i<kv.length; i+=2)m.put(kv[i], kv[i+1]);
        return m;
    }
    static String id(String s)throws IOException {
        if(s==null||!s.matches("[a-zA-Z0-9][a-zA-Z0-9_.+-]{0,63}")||s.equals(".")||s.equals(".."))throw new IOException("Invalid identifier");
        return s;
    }
    String required(String key)throws IOException {
        String s=request.getOrDefault(key, "");
        if(s.isEmpty())throw new IOException("Missing request property: "+key);
        return s;
    }
    Path dir(String id)throws IOException {
        return FilesUtil.safe(root.resolve("instances"), id(id));
    }
    Map<String, String> instance(String id)throws IOException {
        Path p=dir(id).resolve("instance.properties");
        if(!Files.isRegularFile(p))throw new IOException("Instance does not exist: "+id);
        return FilesUtil.properties(p);
    }
    void progress(String status, String detail, long done, long total)throws IOException {
        FilesUtil.properties(root.resolve("progress.properties"), stringMap("status", status, "detail", detail, "done", Long.toString(done), "total", Long.toString(total)));
    }
    void command(String cmd)throws Exception {
        if(cmd.equals("catalog")) {
            installer.catalog(true);
            message="Minecraft version catalog refreshed";
        }
        else if(cmd.equals("create")) {
            create();
            message="Instance created. Install to download Minecraft";
        }
        else if(cmd.equals("create-install")) {
            create();
            String i=required("id");
            Map<String,String> m=instance(i);
            installer.install(m,dir(i));
            message="Minecraft "+m.get("version")+" and required Java installed";
        }
        else if(cmd.equals("install")) {
            String i=required("id");
            Map<String, String> m=instance(i);
            installer.install(m, dir(i));
            message="Minecraft "+m.get("version")+" installed";
        }
        else if(cmd.equals("import")) {
            localImport();
        }
        else if(cmd.equals("prepare-launch")) {
            prepare();
        }
        else if(cmd.equals("mods")) {
            instance(required("id"));
            message="Mods loaded";
        }
        else if(cmd.equals("mod-add")) {
            addMod();
        }
        else if(cmd.equals("mod-toggle")) {
            toggleMod();
        }
        else if(cmd.equals("mod-remove")) {
            removeMod();
        }
        else if(cmd.equals("mod-search")) {
            modSearch();
        }
        else if(cmd.equals("mod-download")) {
            downloadMod();
        }
        else if(cmd.equals("settings")) {
            updateSettings();
        }
        else if(cmd.equals("install-java")) {
            installJava();
        }
        else if(cmd.equals("detect-java")) {
            message="Detected "+runtimes.inventory().size()+" Windows Java runtimes";
        }
        else if(cmd.equals("auth-device")) {
            auth.device();
        }
        else if(cmd.equals("auth-poll")) {
            auth.poll();
        }
        else if(cmd.equals("auth-signout")) {
            auth.signout();
        }
        else if(cmd.equals("clone")) {
            cloneInstance();
        }
        else if(cmd.equals("export")) {
            exportPack();
        }
        else if(cmd.equals("import-pack")) {
            importPack();
        }
        else if(cmd.equals("delete")) {
            deleteInstance();
        }
        else if(cmd.equals("view")) {
            message="Launcher ready";
        }
        else throw new IOException("Unknown command: "+cmd);
    }
    void create()throws IOException {
        String i=id(required("id")), v=id(required("version")), loader=request.getOrDefault("loader", "vanilla");
        if(!Arrays.asList("vanilla", "fabric", "quilt", "forge").contains(loader))throw new IOException("Unsupported loader: "+loader);
        if(loader.equals("forge")&&!v.equals("1.12.2"))throw new IOException("Forge support currently requires Minecraft 1.12.2; modern Forge/NeoForge processors are not implemented");
        Path d=dir(i);
        if(Files.exists(d))throw new IOException("Instance ID already exists");
        String name=request.getOrDefault("name", i);
        validateName(name);
        Files.createDirectories(d.resolve(".minecraft/mods"));
        Map<String, String> m=stringMap("id", i, "name", name, "version", v, "loader", loader, "loaderVersion", request.getOrDefault("loaderVersion", ""), "installed", "false");
        FilesUtil.properties(d.resolve("instance.properties"), m);
        writePolyMC(d, m);
    }
    static void validateName(String name)throws IOException {
        if(name.isEmpty()||name.length()>96||name.matches("(?s).*[\\r\\n\\x00-\\x1f].*"))throw new IOException("Name must be 1–96 printable characters");
    }
    void writePolyMC(Path d, Map<String, String> m)throws IOException {
        FilesUtil.properties(d.resolve("instance.cfg"), stringMap("InstanceType", "OneSix", "name", m.get("name"), "OverrideJavaLocation", "false"));
        List<Object> parts=new ArrayList<Object>();
        parts.add(Auth.map("uid", "net.minecraft", "version", m.get("version"), "important", true));
        String loader=m.get("loader");
        if(!loader.equals("vanilla"))parts.add(Auth.map("uid", loader.equals("fabric")?"net.fabricmc.fabric-loader":loader.equals("forge")?"net.minecraftforge":"org.quiltmc.quilt-loader", "version", m.getOrDefault("loaderVersion", "")));
        FilesUtil.write(d.resolve("mmc-pack.json"), Json.stringify(Auth.map("formatVersion", 1, "components", parts)));
    }
    void updateSettings()throws IOException {
        for(Map.Entry<String, String> e:request.entrySet()) {
            String k=e.getKey();
            if(k.equals("command"))continue;
            if(k.matches("java[0-9]+")||Arrays.asList("memoryMb", "microsoftClientId", "manifestUrl", "assetsUrl", "fabricApi", "quiltApi", "graphics", "accountMode", "username", "modrinthApi", "javaApi").contains(k)) {
                if(k.equals("memoryMb"))memory(e.getValue());
                if(k.equals("accountMode")&&!Arrays.asList("microsoft", "offline").contains(e.getValue()))throw new IOException("accountMode must be microsoft or offline");
                if(k.equals("graphics")&&!Arrays.asList("opengl", "zink").contains(e.getValue()))throw new IOException("graphics must be opengl or zink");
                settings.put(k, e.getValue());
            }
            else throw new IOException("Unknown setting: "+k);
        }
        FilesUtil.properties(root.resolve("settings.properties"), settings);
        message="Launcher settings saved";
    }
    static int memory(String s)throws IOException {
        try {
            int n=Integer.parseInt(s);
            if(n<512||n>12288)throw new IOException("Memory must be 512–12288 MiB");
            return n;
        }
        catch(NumberFormatException e) {
            throw new IOException("Invalid memory size");
        }
    }
    void localImport()throws IOException {
        Path src=Paths.get(required("source")).toAbsolutePath().normalize();
        if(Files.isDirectory(src.resolve(".minecraft")))src=src.resolve(".minecraft");
        if(!Files.isDirectory(src.resolve("versions")))throw new IOException("Import requires a .minecraft folder with versions");
        String v=request.getOrDefault("version", "");
        if(v.isEmpty()) {
            List<String> vs=new ArrayList<String>();
            try(DirectoryStream<Path> ds=Files.newDirectoryStream(src.resolve("versions"))) {
                for(Path p:ds)if(Files.isRegularFile(p.resolve(p.getFileName()+".json"))&&Files.isRegularFile(p.resolve(p.getFileName()+".jar")))vs.add(p.getFileName().toString());
            }
            if(vs.size()!=1)throw new IOException("Specify version when local folder has multiple complete versions");
            v=vs.get(0);
        }
        id(v);
        String i=id(required("id"));
        if(Files.exists(dir(i)))throw new IOException("Instance ID already exists");
        Path vp=src.resolve("versions/"+v);
        if(!Files.isRegularFile(vp.resolve(v+".json"))||!Files.isRegularFile(vp.resolve(v+".jar")))throw new IOException("Requested local version lacks JSON or client JAR");
        Map<String, Object> meta=installer.json(vp.resolve(v+".json"));
        if(!v.equals(Json.text(meta, "id")))throw new IOException("Local version ID mismatch");
        if(meta.containsKey("downloads")&&Json.obj(meta.get("downloads")).containsKey("client")) {
            Map<String, Object> client=Json.obj(Json.obj(meta.get("downloads")).get("client"));
            if(!FilesUtil.valid(vp.resolve(v+".jar"), Json.text(client, "sha1"), Installer.size(client)))throw new IOException("Local client SHA1/size mismatch");
        }
        FilesUtil.copyTree(vp, root.resolve("versions/"+v));
        for(String folder:Arrays.asList("libraries", "assets"))if(Files.isDirectory(src.resolve(folder)))FilesUtil.copyTree(src.resolve(folder), root.resolve(folder));
        Path d=dir(i), game=d.resolve(".minecraft");
        Files.createDirectories(game);
        for(String folder:Arrays.asList("saves", "mods", "config", "resourcepacks", "shaderpacks", "screenshots"))if(Files.isDirectory(src.resolve(folder)))FilesUtil.copyTree(src.resolve(folder), game.resolve(folder));
        for(String file:Arrays.asList("options.txt", "optionsof.txt", "servers.dat"))if(Files.isRegularFile(src.resolve(file)))Files.copy(src.resolve(file), game.resolve(file), StandardCopyOption.REPLACE_EXISTING);
        Map<String, String> m=stringMap("id", i, "name", request.getOrDefault("name", i), "version", v, "loader", "vanilla", "loaderVersion", "", "installed", "false");
        validateName(m.get("name"));
        FilesUtil.properties(d.resolve("instance.properties"), m);
        writePolyMC(d, m);
        try {
            installer.install(m, d);
            message="Local Minecraft "+v+" imported and verified; account databases excluded";
        }
        catch(IOException e) {
            message="Local files imported; run install to repair dependencies: "+e.getMessage();
        }
    }
    Path modPath(String i, String filename)throws IOException {
        instance(i);
        if(filename.indexOf('/')>=0||filename.indexOf('\\')>=0||!(filename.endsWith(".jar")||filename.endsWith(".jar.disabled")))throw new IOException("Mod must be a JAR filename");
        return FilesUtil.safe(dir(i).resolve(".minecraft/mods"), filename);
    }
    void addMod()throws IOException {
        String i=required("id");
        Map<String, String> m=instance(i);
        if(m.get("loader").equals("vanilla"))throw new IOException("Install a Fabric, Quilt or supported Forge instance before adding mods");
        Path src=Paths.get(required("source"));
        String n=request.getOrDefault("mod", src.getFileName().toString());
        Path dst=modPath(i, n);
        try(ZipFile z=new ZipFile(src.toFile())) {
            if(z.size()==0)throw new IOException("Empty mod archive");
        }
        Files.createDirectories(dst.getParent());
        Files.copy(src, dst, StandardCopyOption.REPLACE_EXISTING);
        message="Mod added: "+n;
    }
    void toggleMod()throws IOException {
        String i=required("id"), n=request.getOrDefault("mod", request.getOrDefault("name", ""));
        Path src=modPath(i, n);
        if(!Files.isRegularFile(src))throw new IOException("Mod not found");
        boolean enabled=Boolean.parseBoolean(request.getOrDefault("enabled", Boolean.toString(n.endsWith(".disabled"))));
        String dest=enabled?n.replaceFirst("\\.disabled$", ""):n.endsWith(".disabled")?n:n+".disabled";
        if(!n.equals(dest)) {
            Path to=modPath(i, dest);
            if(Files.exists(to))throw new IOException("Destination mod already exists");
            Files.move(src, to);
        }
        message="Mod "+(enabled?"enabled":"disabled");
    }
    void removeMod()throws IOException {
        Files.delete(modPath(required("id"), required("mod")));
        message="Mod removed";
    }
    void cloneInstance()throws IOException {
        String from=request.getOrDefault("sourceId", required("id")), i;
        if(request.containsKey("sourceId"))i=id(required("id"));
        else {
            String base=from.length()>52?from.substring(0, 52):from;
            i=base+"-copy";
            int n=2;
            while(Files.exists(dir(i)))i=base+"-copy-"+(n++);
        }
        Map<String, String> m=instance(from);
        if(Files.exists(dir(i)))throw new IOException("Destination instance exists");
        FilesUtil.copyTree(dir(from), dir(i));
        m.put("id", i);
        m.put("name", request.getOrDefault("name", m.get("name")+" copy"));
        validateName(m.get("name"));
        FilesUtil.properties(dir(i).resolve("instance.properties"), m);
        writePolyMC(dir(i), m);
        message="Instance cloned as "+i;
    }
    void deleteInstance()throws IOException {
        String i=required("id");
        instance(i);
        FilesUtil.deleteTree(dir(i));
        Files.deleteIfExists(root.resolve("profiles/launch.profile"));
        Files.deleteIfExists(root.resolve("profiles/launch-plan.json"));
        message="Instance deleted";
    }
    void exportPack()throws IOException {
        String i=required("id");
        Map<String, String> m=instance(i);
        String destination=request.getOrDefault("destination", "");
        Path d=dir(i), out=destination.isEmpty()?root.resolve("exports/"+i+".zip"):Paths.get(destination).toAbsolutePath().normalize();
        if(out.startsWith(d))throw new IOException("Export destination cannot be inside the instance");
        writePolyMC(d, m);
        Files.createDirectories(out.getParent());
        final ZipOutputStream zip=new ZipOutputStream(Files.newOutputStream(out));
        try {
            Files.walkFileTree(d, new SimpleFileVisitor<Path>() {
                public FileVisitResult preVisitDirectory(Path p, BasicFileAttributes a) {
                    String n=p.getFileName().toString(); return n.equals("natives")?FileVisitResult.SKIP_SUBTREE:FileVisitResult.CONTINUE;
                }
                public FileVisitResult visitFile(Path p, BasicFileAttributes a)throws IOException {
                    String n=p.getFileName().toString(); if(a.isSymbolicLink())throw new IOException("Symlink export refused"); if(FilesUtil.privateFile(n)||n.equals("installed.json")||n.equals("instance.properties"))return FileVisitResult.CONTINUE; zip.putNextEntry(new ZipEntry(d.relativize(p).toString().replace('\\', '/'))); Files.copy(p, zip); zip.closeEntry(); return FileVisitResult.CONTINUE;
                }
            }
            );
        }
        finally {
            zip.close();
        }
        message="PolyMC-compatible instance pack exported: "+out.getFileName();
    }
    void importPack()throws IOException {
        String i=id(required("id"));
        Path dest=dir(i);
        if(Files.exists(dest))throw new IOException("Destination instance exists");
        Path stage=FilesUtil.safe(root.resolve("cache"), "pack-"+i+"-"+System.nanoTime());
        Files.createDirectories(stage);
        try {
            FilesUtil.unzip(Paths.get(required("source")), stage, new HashSet<String>(Arrays.asList("accounts.json", "launcher_accounts.json", "launcher_profiles.json", "account.json", "auth.properties", "auth-pending.json", "launch-plan.json")));
            Path pack=stage;
            if(!Files.isRegularFile(pack.resolve("mmc-pack.json"))) {
                try(DirectoryStream<Path> ds=Files.newDirectoryStream(stage)) {
                    for(Path p:ds)if(Files.isDirectory(p)&&Files.isRegularFile(p.resolve("mmc-pack.json"))) {
                        if(pack!=stage)throw new IOException("Pack has multiple instances");
                        pack=p;
                    }
                }
            }
            if(!Files.isRegularFile(pack.resolve("mmc-pack.json")))throw new IOException("Expected PolyMC/MultiMC mmc-pack.json. CurseForge and Modrinth packs require their own manifests");
            Map<String, Object> manifest=installer.json(pack.resolve("mmc-pack.json"));
            String v="", loader="vanilla", lv="";
            for(Object c:Json.arr(manifest.get("components"))) {
                Map<String, Object> part=Json.obj(c);
                String uid=Json.text(part, "uid");
                if(uid.equals("net.minecraft"))v=Json.text(part, "version");
                else if(uid.equals("net.fabricmc.fabric-loader")) {
                    loader="fabric";
                    lv=Json.text(part, "version");
                }
                else if(uid.equals("org.quiltmc.quilt-loader")) {
                    loader="quilt";
                    lv=Json.text(part, "version");
                }
                else if(uid.equals("net.minecraftforge")) {
                    loader="forge";
                    lv=Json.text(part,"version");
                }
                else if(uid.toLowerCase(Locale.ROOT).contains("forge"))throw new IOException("Modern Forge/NeoForge pack installation is not supported");
                else if(!Arrays.asList("org.lwjgl", "org.lwjgl3", "net.fabricmc.intermediary").contains(uid))throw new IOException("Unsupported pack component: "+uid);
            }
            id(v);
            if(loader.equals("forge")&&!v.equals("1.12.2"))throw new IOException("Forge packs currently require Minecraft 1.12.2");
            Map<String, String> cfg=FilesUtil.properties(pack.resolve("instance.cfg"));
            String name=request.getOrDefault("name", cfg.getOrDefault("name", i));
            validateName(name);
            Files.createDirectories(dest.resolve(".minecraft"));
            Path game=pack.resolve(".minecraft");
            if(!Files.isDirectory(game))game=pack.resolve("minecraft");
            if(Files.isDirectory(game))FilesUtil.copyTree(game, dest.resolve(".minecraft"));
            Map<String, String> m=stringMap("id", i, "name", name, "version", v, "loader", loader, "loaderVersion", lv, "installed", "false");
            FilesUtil.properties(dest.resolve("instance.properties"), m);
            writePolyMC(dest, m);
            message="PolyMC pack imported; install to fetch verified game and loader dependencies";
        }
        catch(IOException e) {
            FilesUtil.deleteTree(dest);
            throw e;
        }
        finally {
            FilesUtil.deleteTree(stage);
        }
    }
    void modSearch()throws IOException {
        String q=required("query"), base=settings.getOrDefault("modrinthApi", "https://api.modrinth.com/v2");
        String facets="";
        if(request.containsKey("id")) {
            Map<String, String> m=instance(request.get("id"));
            facets="&facets="+URLEncoder.encode(Json.stringify(Arrays.asList(Arrays.asList("versions:"+m.get("version")), Arrays.asList("categories:"+m.get("loader")))), "UTF-8");
        }
        Path p=root.resolve("cache/mod-search.json");
        FilesUtil.refresh(base+"/search?limit=20&query="+URLEncoder.encode(q, "UTF-8")+facets, p);
        Map<String, Object> results=installer.json(p);
        int n=0;
        for(Object h:Json.arr(results.get("hits"))) {
            Map<String, Object> hit=Json.obj(h);
            authView.put("search."+n+".id", Json.text(hit, "project_id"));
            authView.put("search."+n+".name", Json.text(hit, "title"));
            authView.put("search."+n+".description", Json.text(hit, "description").replace('\n', ' '));
            n++;
        }
        authView.put("search.count", Integer.toString(n));
        message="Modrinth search completed";
    }
    void downloadMod()throws IOException {
        String i=required("id");
        Map<String, String> m=instance(i);
        if(m.get("loader").equals("vanilla"))throw new IOException("Mods require Fabric, Quilt or supported Forge");
        String pid=id(required("projectId")), base=settings.getOrDefault("modrinthApi", "https://api.modrinth.com/v2");
        Map<String,String> installed=new HashMap<String,String>();
        downloadModVersion(pid, request.getOrDefault("modVersion", ""), m, i, base, installed, 0);
        message="Compatible Modrinth mod and required dependencies installed";
    }
    void downloadModVersion(String project, String requested, Map<String, String> m, String i, String base, Map<String,String> visited, int depth)throws IOException {
        if(depth>20)throw new IOException("Mod dependency depth limit");
        if(visited.containsKey(project)) {
            if(!requested.isEmpty()&&!requested.equals(visited.get(project)))throw new IOException("Conflicting required mod dependency version: "+project);
            return;
        }
        Path p=root.resolve("cache/mod-"+id(project)+".json");
        String url=base+"/project/"+project+"/version?loaders="+URLEncoder.encode(Json.stringify(Arrays.asList(m.get("loader"))), "UTF-8")+"&game_versions="+URLEncoder.encode(Json.stringify(Arrays.asList(m.get("version"))), "UTF-8");
        FilesUtil.refresh(url, p);
        List<Object> versions=Json.arr(Json.parse(FilesUtil.read(p)));
        if(versions.isEmpty())throw new IOException("No compatible Modrinth version for "+project);
        Map<String, Object> v=Json.obj(versions.get(0));
        if(!requested.isEmpty()) {
            v=null;
            for(Object e:versions)if(requested.equals(Json.text(Json.obj(e), "id"))) {
                v=Json.obj(e);
                break;
            }
            if(v==null)throw new IOException("Requested mod version/dependency is incompatible");
        }
        visited.put(project,Json.text(v,"id"));
        Map<String, Object> file=null;
        for(Object f:Json.arr(v.get("files"))) {
            Map<String, Object> ff=Json.obj(f);
            if(file==null||Boolean.TRUE.equals(ff.get("primary")))file=ff;
        }
        if(file==null)throw new IOException("Mod version has no downloadable files");
        Path dst=modPath(i, Json.text(file, "filename"));
        Map<String, Object> hashes=Json.obj(file.get("hashes"));
        FilesUtil.download(Json.text(file, "url"), dst, Json.text(hashes, "sha1"), Installer.size(file));
        for(Object dep:Json.arr(v.get("dependencies"))) {
            Map<String, Object> d=Json.obj(dep);
            if(!"required".equals(Json.text(d, "dependency_type")))continue;
            String projectId=Json.text(d, "project_id");
            if(projectId.isEmpty())throw new IOException("Dependency requires an explicit version with no project ID; install it manually");
            downloadModVersion(projectId, Json.text(d,"version_id"), m, i, base, visited, depth+1);
        }
    }
    void installJava()throws IOException {
        int major;
        try { major=Integer.parseInt(required("major")); }
        catch(NumberFormatException e) { throw new IOException("Invalid Java major version"); }
        JavaRuntime.Info info=runtimes.ensure(major,Boolean.parseBoolean(request.getOrDefault("repair","false")));
        message="Windows x64 Java "+info.version+" ready";
    }
    static String digest(Path p, String algorithm)throws Exception {
        MessageDigest d=MessageDigest.getInstance(algorithm);
        try(InputStream in=Files.newInputStream(p)) {
            byte[] b=new byte[65536];
            int n;
            while((n=in.read(b))>=0)d.update(b, 0, n);
        }
        StringBuilder out=new StringBuilder();
        for(byte v:d.digest())out.append(String.format("%02x", v&255));
        return out.toString();
    }
    void view()throws IOException {
        Map<String, String> v=stringMap("status", status, "detail", message);
        int n=0;
        Path inst=root.resolve("instances");
        if(Files.isDirectory(inst)) {
            List<Path> paths=new ArrayList<Path>();
            try(DirectoryStream<Path> ds=Files.newDirectoryStream(inst)) {
                for(Path p:ds)if(Files.isRegularFile(p.resolve("instance.properties")))paths.add(p);
            }
            Collections.sort(paths);
            for(Path p:paths) {
                if(n>=128)break;
                Map<String, String> m=FilesUtil.properties(p.resolve("instance.properties"));
                for(String k:Arrays.asList("id", "name", "version", "loader", "installed", "loaderVersion"))v.put("instance."+n+"."+k, m.getOrDefault(k, ""));
                n++;
            }
        }
        v.put("instance.count", Integer.toString(n));
        n=0;
        Path catalog=root.resolve("cache/version_manifest_v2.json");
        if(Files.isRegularFile(catalog)) {
            for(Object o:Json.arr(installer.json(catalog).get("versions"))) {
                if(n>=2048)break;
                Map<String, Object> m=Json.obj(o);
                v.put("version."+n+".id", Json.text(m, "id"));
                v.put("version."+n+".type", Json.text(m, "type"));
                int requiredJava=0;
                Path cached=root.resolve("versions/"+Json.text(m,"id")+"/"+Json.text(m,"id")+".json");
                if(Files.isRegularFile(cached))try {requiredJava=Installer.javaMajor(installer.json(cached));}
                catch(IOException ignored) { /* An incomplete cache must not hide the operation error. */ }
                catch(IllegalArgumentException ignored) { /* Installation reports invalid metadata precisely. */ }
                v.put("version."+n+".java",Integer.toString(requiredJava));
                n++;
            }
        }
        v.put("version.count", Integer.toString(n));
        n=0;
        if(request.containsKey("id")&&request.get("id").matches("[a-zA-Z0-9][a-zA-Z0-9_.+-]{0,63}")&&Files.isDirectory(dir(request.get("id")).resolve(".minecraft/mods"))) {
            List<Path> mods=new ArrayList<Path>();
            try(DirectoryStream<Path> ds=Files.newDirectoryStream(dir(request.get("id")).resolve(".minecraft/mods"))) {
                for(Path p:ds)if(Files.isRegularFile(p)&&(p.toString().endsWith(".jar")||p.toString().endsWith(".jar.disabled")))mods.add(p);
            }
            Collections.sort(mods);
            for(Path p:mods) {
                if(n>=256)break;
                v.put("mod."+n+".name", p.getFileName().toString());
                v.put("mod."+n+".enabled", Boolean.toString(p.toString().endsWith(".jar")));
                n++;
            }
        }
        v.put("mod.count", Integer.toString(n));
        v.put("settings.memoryMb", settings.getOrDefault("memoryMb", "2048"));
        v.put("settings.accountMode", settings.getOrDefault("accountMode", "microsoft"));
        v.put("settings.username",settings.getOrDefault("username","Player"));
        for(Map.Entry<String, String> e:settings.entrySet())if(e.getKey().matches("java[0-9]+"))v.put("settings."+e.getKey(), e.getValue());
        v.put("auth.signedIn", Boolean.toString(Files.isRegularFile(root.resolve("private/account.json"))));
        n=0;
        for(JavaRuntime.Info info:runtimes.inventory()) {
            if(n>=16)break;
            v.put("java."+n+".major",Integer.toString(info.major));
            v.put("java."+n+".version",info.version);
            v.put("java."+n+".path",info.executable.toString());
            v.put("java."+n+".valid",Boolean.toString(info.valid));
            v.put("java."+n+".detail",info.detail);
            n++;
        }
        v.put("java.count",Integer.toString(n));
        v.putAll(authView);
        FilesUtil.properties(root.resolve("launcher-view.properties"), v);
    }
    static List<String> argumentValues(Object args) {
        List<String> out=new ArrayList<String>();
        for(Object a:Json.arr(args)) {
            if(a instanceof String)out.add((String)a);
            else {
                Map<String, Object> rule=Json.obj(a);
                if(Installer.rules(rule.get("rules"))) {
                    Object value=rule.get("value");
                    if(value instanceof String)out.add((String)value);
                    else for(Object v:Json.arr(value))out.add(Json.str(v));
                }
            }
        }
        return out;
    }
    static List<String> tokenize(String text)throws IOException {
        List<String> args=new ArrayList<String>();
        StringBuilder b=new StringBuilder();
        boolean quote=false;
        for(int i=0; i<text.length(); i++) {
            char c=text.charAt(i);
            if(c=='"') {
                quote=!quote;
                continue;
            }
            if(Character.isWhitespace(c)&&!quote) {
                if(b.length()>0) {
                    args.add(b.toString());
                    b.setLength(0);
                }
            }
            else b.append(c);
        }
        if(quote)throw new IOException("Unterminated argument quote");
        if(b.length()>0)args.add(b.toString());
        return args;
    }
    static String replace(String input, Map<String, String> values, boolean allowAuth)throws IOException {
        String out=input;
        for(Map.Entry<String, String> e:values.entrySet())out=out.replace("${"+e.getKey()+"}", e.getValue());
        if(out.contains("${")&&!(allowAuth&&out.matches(".*\\$\\{auth_(access_token|session)\\}.*")))throw new IOException("Unsupported launch placeholder: "+out.replaceAll("[^a-zA-Z0-9_${} ]", ""));
        return out;
    }
    static String windows(Path p) {
        String s=p.toAbsolutePath().normalize().toString();
        return s.matches("^[a-zA-Z]:.*")?s.replace('/', '\\'):"Z:"+s.replace('/', '\\');
    }
    Path javaFor(int major)throws IOException {
        return runtimes.ensure(major,false).executable;
    }
    void prepare()throws Exception {
        Files.deleteIfExists(root.resolve("profiles/launch.profile"));
        Files.deleteIfExists(root.resolve("profiles/launch-plan.json"));
        String i=required("id");
        Map<String, String> m=instance(i);
        Path d=dir(i);
        if(!Boolean.parseBoolean(m.get("installed"))||!Files.isRegularFile(d.resolve("installed.json")))throw new IOException("Instance is not installed; run install first");
        Map<String, Object> meta=installer.json(d.resolve("installed.json"));
        int major=Installer.javaMajor(meta);
        Path java=javaFor(major), game=d.resolve(".minecraft"), natives=d.resolve("natives"), launcher=root.resolve("launcher/prosperomc-launcher.jar");
        if(!Files.isRegularFile(launcher))throw new IOException("Launcher JAR missing from root/launcher; stage the app first");
        List<Path> cp=installer.libraries(meta, natives, false);
        if(root.toString().replace('\\','/').equalsIgnoreCase("Z:/data/ProsperoMC")
                &&major==8&&"1.12.2".equals(Json.text(meta,"id")))
            cp.add(0,NettyCompat.prepare(root,cp));
        Path client=FilesUtil.safe(root, Json.text(meta, "_clientPath"));
        if(!Files.isRegularFile(client))throw new IOException("Client JAR missing");
        Map<String, Object> ds=meta.containsKey("downloads")?Json.obj(meta.get("downloads")):Collections.<String, Object>emptyMap();
        if(ds.containsKey("client")) {
            Map<String, Object> c=Json.obj(ds.get("client"));
            if(!FilesUtil.valid(client, Json.text(c, "sha1"), Installer.size(c)))throw new IOException("Client integrity mismatch; reinstall");
        }
        cp.add(client);
        cp.add(launcher);
        StringBuilder classpath=new StringBuilder();
        for(Path p:cp) {
            if(classpath.length()>0)classpath.append(';');
            classpath.append(windows(p));
        }
        String mode=request.getOrDefault("accountMode", settings.getOrDefault("accountMode", "microsoft"));
        Map<String, String> placeholders=new LinkedHashMap<String, String>();
        String name, uuid;
        if(mode.equals("microsoft")) {
            Map<String, Object> a=auth.account(true);
            name=Json.text(a, "name");
            uuid=Json.text(a, "uuid");
        }
        else if(mode.equals("offline")) {
            name=request.getOrDefault("username", settings.getOrDefault("username", "Player"));
            if(!name.matches("[A-Za-z0-9_]{1,16}"))throw new IOException("Offline username must be 1–16 letters, digits or underscores");
            uuid=UUID.nameUUIDFromBytes(("OfflinePlayer:"+name).getBytes(StandardCharsets.UTF_8)).toString().replace("-", "");
        }
        else throw new IOException("accountMode must be microsoft or offline");
        placeholders.put("auth_player_name", name);
        placeholders.put("auth_uuid", uuid);
        placeholders.put("user_type", mode.equals("microsoft")?"msa":"legacy");
        placeholders.put("version_name", m.get("version"));
        placeholders.put("version_type", "release");
        placeholders.put("game_directory", windows(game));
        placeholders.put("assets_root", windows(root.resolve("assets")));
        String assets=meta.containsKey("assetIndex")?Json.text(Json.obj(meta.get("assetIndex")), "id"):"legacy";
        placeholders.put("assets_index_name", assets);
        placeholders.put("game_assets", windows(root.resolve("assets/virtual/"+assets)));
        placeholders.put("user_properties", "{}");
        placeholders.put("natives_directory", windows(natives));
        placeholders.put("classpath", classpath.toString());
        placeholders.put("classpath_separator", ";");
        placeholders.put("library_directory", windows(root.resolve("libraries")));
        placeholders.put("launcher_name", "ProsperoMC");
        placeholders.put("launcher_version", "1.0");
        placeholders.put("clientid", settings.getOrDefault("microsoftClientId", ""));
        placeholders.put("auth_xuid", "");
        placeholders.put("resolution_width", "1280");
        placeholders.put("resolution_height", "720");
        List<String> jvm=new ArrayList<String>();
        jvm.add("-Xms512M");
        jvm.add("-Xmx"+memory(request.getOrDefault("memoryMb", settings.getOrDefault("memoryMb", "2048")))+"M");
        // PS5 Wine backs the Java heap above the compressed-pointer address range.
        jvm.add("-XX:-UseCompressedOops");
        jvm.add("-XX:-UseCompressedClassPointers");
        jvm.add("-Djava.library.path="+windows(natives));
        List<String> gameArgs;
        if(meta.containsKey("arguments")) {
            Map<String, Object> a=Json.obj(meta.get("arguments"));
            for(String value:argumentValues(a.get("jvm"))) {
                if(value.equals("-cp")||value.equals("${classpath}"))continue;
                jvm.add(replace(value, placeholders, false));
            }
            gameArgs=argumentValues(a.get("game"));
        }
        else gameArgs=tokenize(Json.text(meta, "minecraftArguments"));
        if(meta.containsKey("logging")) {
            Map<String, Object> log=Json.obj(meta.get("logging"));
            if(log.containsKey("client")) {
                Map<String, Object> c=Json.obj(log.get("client")), f=Json.obj(c.get("file"));
                Path file=FilesUtil.safe(root.resolve("assets/log_configs"), Json.text(f, "id"));
                if(!Files.isRegularFile(file)||!FilesUtil.valid(file, Json.text(f, "sha1"), Installer.size(f)))throw new IOException("Logging configuration missing/corrupt; install to repair");
                Map<String, String> vars=stringMap("path", windows(file));
                jvm.add(replace(Json.text(c, "argument"), vars, false));
            }
        }
        List<String> planArgs=new ArrayList<String>();
        for(String a:gameArgs)planArgs.add(replace(a, placeholders, true));
        String main=Json.text(meta, "mainClass");
        if(!main.matches("[a-zA-Z_$][a-zA-Z0-9_$.]*"))throw new IOException("Invalid Minecraft main class");
        Path plan=root.resolve("profiles/launch-plan.json");
        FilesUtil.write(plan, Json.stringify(Auth.map("instanceId", i, "mainClass", main, "arguments", planArgs, "accountMode", mode, "uuid", uuid, "name", name)));
        FilesUtil.restrict(plan);
        jvm.add("-cp");
        jvm.add(classpath.toString());
        jvm.add("org.prosperomc.Main");
        jvm.add("--root");
        jvm.add(windows(root));
        jvm.add("--execute-plan");
        jvm.add(windows(plan));
        StringBuilder argline=new StringBuilder();
        for(String a:jvm) {
            if(argline.length()>0)argline.append(' ');
            argline.append(FilesUtil.quote(a));
        }
        if(argline.length()>32768)throw new IOException("Minecraft command line exceeds Windows/runtime 32768-character limit");
        String graphics=settings.getOrDefault("graphics", "opengl");
        String text="[application]\nid=minecraft\nname=Minecraft Java\nexecutable="+windows(java)+"\nworking_directory="+windows(game)+"\narguments="+argline+"\nprefix=minecraft\nruntime=wine-wow64\narchitecture=pe64\ngraphics="+graphics+"\n[display]\ndesktop=1280x720\nview=window\nscaling=fit\n[input]\nmode=keyboard\nmouse=right_stick\ncross=space\ncircle=escape\nsquare=e\ntriangle=q\nl1=1\nr1=2\nl2=mouse_right\nr2=mouse_left\nup=w\ndown=s\nleft=a\nright=d\noptions=escape\n";
        FilesUtil.write(root.resolve("profiles/launch.profile"), text);
        FilesUtil.restrict(root.resolve("profiles/launch.profile"));
        writePolyMC(d, m);
        message="Minecraft launch prepared with Java "+major+(mode.equals("offline")?" (local offline single-player; online ownership/server authentication unavailable)":"");
    }
    void execute(Path requested)throws Exception {
        Path plan=root.resolve("profiles/launch-plan.json").toAbsolutePath().normalize();
        if(!requested.toAbsolutePath().normalize().equals(plan))throw new IOException("Only the internal launch plan can execute");
        Map<String, Object> data=installer.json(plan);
        String i=id(Json.text(data, "instanceId"));
        instance(i);
        String main=Json.text(data, "mainClass");
        Map<String, String> values=new LinkedHashMap<String, String>();
        String mode=Json.text(data, "accountMode");
        if(mode.equals("microsoft")) {
            Map<String, Object> account=auth.account(true);
            if(!Json.text(account, "uuid").equals(Json.text(data, "uuid")))throw new IOException("Signed-in account changed; prepare launch again");
            values.put("auth_access_token", Json.text(account, "accessToken"));
            values.put("auth_session", "token:"+Json.text(account, "accessToken")+":"+Json.text(account, "uuid"));
        }
        else if(mode.equals("offline")) {
            values.put("auth_access_token", "0");
            values.put("auth_session", "0");
        }
        else throw new IOException("Invalid launch account mode");
        List<String> args=new ArrayList<String>();
        for(Object a:Json.arr(data.get("arguments")))args.add(replace(Json.str(a), values, false));
        try {
            Class.forName(main).getMethod("main", String[].class).invoke(null, (Object)args.toArray(new String[0]));
        }
        catch(InvocationTargetException e) {
            Throwable cause=e.getCause();
            StringWriter trace=new StringWriter();
            cause.printStackTrace(new PrintWriter(trace));
            String diagnostic=trace.toString();
            for(String value:values.values())if(value.length()>1)diagnostic=diagnostic.replace(value,"<redacted>");
            System.err.println(diagnostic);
            System.exit(2);
        }
    }
}
