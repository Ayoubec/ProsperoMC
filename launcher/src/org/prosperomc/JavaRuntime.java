package org.prosperomc;

import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Validates and provisions the Windows JVM selected by Minecraft metadata. */
final class JavaRuntime {
    private final Main app;

    JavaRuntime(Main app) { this.app=app; }

    static final class Info {
        final int major;
        final Path executable;
        String version="", detail="";
        boolean valid;

        Info(int major,Path executable) { this.major=major; this.executable=executable; }
    }

    Path home(int major) throws IOException {
        if(major<8||major>99)throw new IOException("Unsupported Java major: "+major);
        return FilesUtil.safe(app.root.resolve("runtimes"),"java"+major);
    }

    Info inspect(int major,Path runtime) {
        Info result=new Info(major,runtime.resolve("bin/java.exe").toAbsolutePath().normalize());
        try {
            if(Files.isSymbolicLink(runtime))throw new IOException("Symbolic-link runtime is not allowed");
            FilesUtil.safe(runtime,"bin/java.exe");
            Path release=FilesUtil.safe(runtime,"release");
            if(!Files.isRegularFile(release))throw new IOException("Java runtime release metadata missing");
            Map<String,String> metadata=FilesUtil.properties(release);
            result.version=unquote(metadata.getOrDefault("JAVA_VERSION",""));
            Matcher match=Pattern.compile("^(?:1\\.)?([0-9]+)(?:[._+\\-].*)?$").matcher(result.version);
            if(!match.matches()||Integer.parseInt(match.group(1))!=major)
                throw new IOException("Runtime version does not match required Java "+major);
            if(!"Windows".equalsIgnoreCase(unquote(metadata.getOrDefault("OS_NAME",""))))
                throw new IOException("Runtime must target Windows");
            String architecture=unquote(metadata.getOrDefault("OS_ARCH",""));
            if(!architecture.equals("amd64")&&!architecture.equals("x86_64"))
                throw new IOException("Runtime must target Windows x64 (amd64)");
            pe64(result.executable);
            pe64(FilesUtil.safe(runtime,"bin/server/jvm.dll"));
            result.valid=true;
            result.detail="Windows x64 Java "+result.version;
        } catch(Exception e) {
            result.detail=e.getMessage()==null?"Invalid Java runtime":e.getMessage();
        }
        return result;
    }

    static String unquote(String s) {
        return s.length()>=2&&s.charAt(0)=='"'&&s.charAt(s.length()-1)=='"'?s.substring(1,s.length()-1):s;
    }

    static void pe64(Path executable) throws IOException {
        if(!Files.isRegularFile(executable))throw new IOException("Runtime binary missing: "+executable.getFileName());
        try(RandomAccessFile input=new RandomAccessFile(executable.toFile(),"r")) {
            if(input.length()<64)throw new IOException("Runtime binary is not a valid Windows PE64 file: "+executable.getFileName());
            byte[] dos=new byte[64];input.readFully(dos);
            if(dos[0]!='M'||dos[1]!='Z')throw new IOException("Runtime binary is not a Windows executable: "+executable.getFileName());
            int offset=ByteBuffer.wrap(dos,60,4).order(ByteOrder.LITTLE_ENDIAN).getInt();
            if(offset<64||offset>input.length()-26)throw new IOException("Invalid Windows executable header");
            input.seek(offset);byte[] pe=new byte[26];input.readFully(pe);
            ByteBuffer header=ByteBuffer.wrap(pe).order(ByteOrder.LITTLE_ENDIAN);
            if(pe[0]!='P'||pe[1]!='E'||pe[2]!=0||pe[3]!=0||
               (header.getShort(4)&65535)!=0x8664||(header.getShort(20)&65535)<2||
               (header.getShort(24)&65535)!=0x20b)
                throw new IOException("Runtime binary must be Windows x64 PE32+: "+executable.getFileName());
        }
    }

    List<Info> inventory() throws IOException {
        List<Info> list=new ArrayList<Info>();
        Path root=app.root.resolve("runtimes");
        if(Files.isDirectory(root))try(DirectoryStream<Path> entries=Files.newDirectoryStream(root)) {
            for(Path entry:entries) {
                String name=entry.getFileName().toString();
                if(name.matches("java[0-9]{1,2}")) {
                    int major=Integer.parseInt(name.substring(4));
                    if(major>=8)list.add(inspect(major,entry));
                }
            }
        }
        Collections.sort(list,new Comparator<Info>() {
            public int compare(Info a,Info b) { return Integer.compare(a.major,b.major); }
        });
        return list;
    }

    Info ensure(int major,boolean repair) throws IOException {
        Path runtime=home(major), expected=runtime.resolve("bin/java.exe").toAbsolutePath().normalize();
        String configured=app.request.getOrDefault("javaPath",app.settings.getOrDefault("java"+major,expected.toString()));
        if(!Paths.get(configured).toAbsolutePath().normalize().equals(expected))
            throw new IOException("Java "+major+" must use runtimes/java"+major+"/bin/java.exe; reset its configured path");
        if(Files.exists(runtime)) {
            Info existing=inspect(major,runtime);
            if(existing.valid) {
                register(existing);
                app.progress("installing","Using installed Java "+existing.version,1,1);
                return existing;
            }
            if(!repair)throw new IOException("Java "+major+" needs repair: "+existing.detail+
                ". Use install-java major="+major+" repair=true");
        }
        return provision(major,runtime,repair);
    }

    private void register(Info info) throws IOException {
        String key="java"+info.major;
        if(!info.executable.toString().equals(app.settings.get(key))) {
            app.settings.put(key,info.executable.toString());
            FilesUtil.properties(app.root.resolve("settings.properties"),app.settings);
        }
    }

    private List<Object> releases(int major,String kind,Path metadata) throws IOException {
        String base=app.settings.getOrDefault("javaApi","https://api.adoptium.net/v3");
        if(base.endsWith("/"))base=base.substring(0,base.length()-1);
        try {
            FilesUtil.refresh(base+"/assets/latest/"+major+
                "/hotspot?architecture=x64&image_type="+kind+"&os=windows&vendor=eclipse",metadata);
        } catch(IOException e) {
            if(e.getMessage()!=null&&e.getMessage().startsWith("HTTP 404"))return Collections.emptyList();
            throw e;
        }
        return Json.arr(Json.parse(FilesUtil.read(metadata)));
    }

    private Info provision(int major,Path destination,boolean repair) throws IOException {
        app.progress("installing","Finding Windows x64 Java "+major,0,4);
        Path metadata=app.root.resolve("cache/java"+major+".json");
        String kind="jre";
        List<Object> available=releases(major,kind,metadata);
        if(available.isEmpty()) { kind="jdk"; available=releases(major,kind,metadata); }
        if(available.isEmpty())throw new IOException("No Windows x64 Java "+major+
            " JRE or JDK is available; provide a matching runtime manually");
        Map<String,Object> binary=Json.obj(Json.obj(available.get(0)).get("binary"));
        if(!"x64".equals(Json.text(binary,"architecture"))||!"windows".equals(Json.text(binary,"os"))||
           !kind.equals(Json.text(binary,"image_type")))
            throw new IOException("Java provider returned the wrong architecture/platform");
        Map<String,Object> pkg=Json.obj(binary.get("package"));
        String expected=Json.text(pkg,"checksum");
        if(!expected.matches("[a-fA-F0-9]{64}"))throw new IOException("Java provider SHA256 checksum missing/invalid");
        Path archive=app.root.resolve("cache/java"+major+".zip");
        app.progress("installing","Downloading Windows x64 Java "+major+" "+kind.toUpperCase(),1,4);
        try {
            if(Files.isRegularFile(archive)&&!Main.digest(archive,"SHA-256").equalsIgnoreCase(expected))
                Files.delete(archive);
            FilesUtil.download(Json.text(pkg,"link"),archive,"",Installer.size(pkg));
            if(!Main.digest(archive,"SHA-256").equalsIgnoreCase(expected)) {
                Files.deleteIfExists(archive);
                throw new IOException("Java archive SHA256 mismatch");
            }
        } catch(IOException e) { throw e; }
        catch(Exception e) { throw new IOException("Java archive verification failed",e); }
        Path stage=app.root.resolve("cache/java-stage-"+major+"-"+System.nanoTime());
        Files.createDirectories(stage);
        try {
            app.progress("installing","Verifying and extracting Java "+major,2,4);
            FilesUtil.unzip(archive,stage,Collections.<String>emptySet());
            Path candidate=Files.isRegularFile(stage.resolve("bin/java.exe"))?stage:null;
            try(DirectoryStream<Path> entries=Files.newDirectoryStream(stage)) {
                for(Path entry:entries)if(Files.isRegularFile(entry.resolve("bin/java.exe"))) {
                    if(candidate!=null)throw new IOException("Java archive contains multiple runtimes");
                    candidate=entry;
                }
            }
            if(candidate==null)throw new IOException("Java archive lacks bin/java.exe");
            Info verified=inspect(major,candidate);
            if(!verified.valid)throw new IOException("Downloaded Java runtime invalid: "+verified.detail);
            Files.createDirectories(destination.getParent());
            Path backup=null;
            if(Files.exists(destination)) {
                if(!repair)throw new IOException("Java runtime appeared while installing");
                backup=app.root.resolve("cache/java"+major+"-invalid-"+System.nanoTime());
                FilesUtil.atomic(destination,backup);
            }
            try { FilesUtil.atomic(candidate,destination); }
            catch(IOException e) {
                if(backup!=null)FilesUtil.atomic(backup,destination);
                throw e;
            }
            Info result=inspect(major,destination);
            register(result);
            app.progress("installing","Java "+result.version+" ready",4,4);
            return result;
        } finally { FilesUtil.deleteTree(stage); }
    }
}
