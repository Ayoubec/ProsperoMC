package org.prosperomc;

import java.io.*;
import java.lang.instrument.*;
import java.lang.reflect.Method;
import java.nio.file.*;
import java.security.ProtectionDomain;
import java.util.*;
import java.util.jar.JarFile;

/** Redirect only ZipFS's immutable archive READ backing; keep loader JAR caching. */
public final class ZipFsAgent {
    private static JarFile bootstrap;
    public static void premain(String argument,final Instrumentation instrumentation)throws Exception {
        if(argument==null||argument.length()==0)throw new IOException("ZIP channel bootstrap path missing");
        Path path=Paths.get(argument).toAbsolutePath().normalize();
        if(!Files.isRegularFile(path)||!path.getFileName().toString().equals("prosperomc-zipfs.jar"))
            throw new IOException("ZIP channel bootstrap JAR missing");
        bootstrap=new JarFile(path.toFile());
        instrumentation.appendToBootstrapClassLoaderSearch(bootstrap);
        Class<?> helper=Class.forName("org.prosperomc.zip.ZipChannels",true,null);
        Class.forName("org.prosperomc.zip.ArchiveFile",true,null);
        Class<?> moduleType=Class.forName("java.lang.Module");
        Object helperModule=Class.class.getMethod("getModule").invoke(helper);
        Class<?> layerType=Class.forName("java.lang.ModuleLayer");
        Object layer=layerType.getMethod("boot").invoke(null);
        Optional<?> module=(Optional<?>)layerType.getMethod("findModule",String.class).invoke(layer,"jdk.zipfs");
        if(!module.isPresent())throw new IOException("JDK ZIP filesystem module unavailable");
        Method redefine=Instrumentation.class.getMethod("redefineModule",moduleType,Set.class,Map.class,Map.class,Set.class,Map.class);
        redefine.invoke(instrumentation,module.get(),Collections.singleton(helperModule),Collections.emptyMap(),
            Collections.emptyMap(),Collections.emptySet(),Collections.emptyMap());
        Object baseModule=Class.class.getMethod("getModule").invoke(Object.class);
        redefine.invoke(instrumentation,baseModule,Collections.singleton(helperModule),Collections.emptyMap(),
            Collections.emptyMap(),Collections.emptySet(),Collections.emptyMap());
        instrumentation.addTransformer(new ClassFileTransformer() {
            public byte[] transform(ClassLoader loader,String name,Class<?> type,ProtectionDomain domain,byte[] bytes) {
                if("java/util/zip/ZipFile$Source".equals(name)) {
                    try{byte[] result=ArchiveSourceRedirect.redirect(bytes);jarRedirected=true;return result;}
                    catch(Exception error){throw new IllegalStateException("JAR backing redirect failed",error);}
                }
                if(!"jdk/nio/zipfs/ZipFileSystem".equals(name))return null;
                try {return redirect(bytes);}catch(Exception error) {
                    throw new IllegalStateException("ZIP backing redirect failed",error);
                }
            }
        },true);
        Class<?> source=Class.forName("java.util.zip.ZipFile$Source",false,null);
        jarRedirected=false;
        instrumentation.retransformClasses(source);
        if(!jarRedirected)throw new IOException("JAR backing READ constructor was not redirected");
        // Force linking now so a missing redirect is diagnosed before mod startup.
        ClassLoader platform=(ClassLoader)ClassLoader.class.getMethod("getPlatformClassLoader").invoke(null);
        Class.forName("jdk.nio.zipfs.ZipFileSystem",false,platform);
        if(!redirected)throw new IOException("ZIP backing READ call was not redirected");
        System.out.println("PS5 ZIP backing channels: limit=16; directory metadata and loader cache preserved");
        System.out.println("PS5 JAR backing files: limit=16; central directory, verification and URL cache preserved");
    }
    private static volatile boolean redirected;
    private static volatile boolean jarRedirected;
    private static int u2(byte[] b,int at) {return ((b[at]&255)<<8)|(b[at+1]&255);}
    static byte[] redirect(byte[] bytes)throws IOException {
        if(bytes.length<10||bytes[0]!=(byte)0xca||bytes[1]!=(byte)0xfe)throw new IOException("Invalid ZIP class");
        int count=u2(bytes,8),at=10;
        int[] offsets=new int[count],tags=new int[count];String[] utf=new String[count];
        for(int n=1;n<count;n++) {
            offsets[n]=at;int tag=tags[n]=bytes[at++]&255;
            switch(tag) {
            case 1:int size=u2(bytes,at);at+=2;utf[n]=new String(bytes,at,size,"UTF-8");at+=size;break;
            case 3:case 4:case 9:case 10:case 11:case 12:case 17:case 18:at+=4;break;
            case 5:case 6:at+=8;n++;break;
            case 7:case 8:case 16:case 19:case 20:at+=2;break;
            case 15:at+=3;break;
            default:throw new IOException("Unknown ZIP class constant tag "+tag);
            }
            if(at>bytes.length)throw new IOException("Truncated ZIP class constants");
        }
        byte[] patched=bytes.clone();int matches=0;
        String descriptor="(Ljava/nio/file/Path;[Ljava/nio/file/OpenOption;)Ljava/nio/channels/SeekableByteChannel;";
        for(int n=1;n<count;n++)if(tags[n]==10) {
            int owner=u2(bytes,offsets[n]+1),nt=u2(bytes,offsets[n]+3);
            if(tags[owner]!=7||tags[nt]!=12)throw new IOException("Invalid ZIP method reference");
            if("java/nio/file/Files".equals(utf[u2(bytes,offsets[owner]+1)])&&
                "newByteChannel".equals(utf[u2(bytes,offsets[nt]+1)])&&descriptor.equals(utf[u2(bytes,offsets[nt]+3)])) {
                patched[offsets[n]+1]=(byte)((count+1)>>8);patched[offsets[n]+2]=(byte)(count+1);matches++;
            }
        }
        if(matches!=1||count>65532)throw new IOException("Unexpected ZIP READ method references: "+matches);
        ByteArrayOutputStream output=new ByteArrayOutputStream(bytes.length+64);DataOutputStream data=new DataOutputStream(output);
        data.write(patched,0,8);data.writeShort(count+2);data.write(patched,10,at-10);
        data.writeByte(1);data.writeUTF("org/prosperomc/zip/ZipChannels");data.writeByte(7);data.writeShort(count);
        data.write(patched,at,patched.length-at);data.flush();redirected=true;return output.toByteArray();
    }
}
