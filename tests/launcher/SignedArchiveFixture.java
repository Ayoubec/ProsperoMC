import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import org.prosperomc.zip.ArchiveFile;

/** Real signed JAR verification survives eviction; corrupt signed content fails. */
public class SignedArchiveFixture {
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[0]);List<JarFile> files=new ArrayList<>();
        try {
            for(int i=0;i<64;i++) {
                Path file=root.resolve("signed-"+i+".jar");Files.copy(root.resolve("signed.jar"),file);
                files.add(new JarFile(file.toFile(),true));
            }
            for(int n=0;n<256;n++) {
                JarFile file=files.get((n*37)%64);JarEntry entry=file.getJarEntry("data.txt");
                try(InputStream input=file.getInputStream(entry)){while(input.read()!=-1){}}
                if(entry.getCodeSigners()==null||entry.getCodeSigners().length!=1)throw new AssertionError("Signature not verified");
            }
            if(ArchiveFile.statistics()[0]>16||ArchiveFile.statistics()[3]<64)throw new AssertionError("Signed JARs did not evict");
            try(JarFile corrupt=new JarFile(root.resolve("corrupt.jar").toFile(),true)) {
                try(InputStream input=corrupt.getInputStream(corrupt.getJarEntry("data.txt"))) {
                    try{while(input.read()!=-1){}throw new AssertionError("Corrupt signed JAR accepted");}
                    catch(SecurityException expected){}
                }
            }
        } finally {for(JarFile file:files)file.close();}
        if(ArchiveFile.statistics()[0]!=0)throw new AssertionError("Signed JAR handle leak");
        System.out.println("SIGNED_JAR_POOL_PASS: 64 signed archives; 256 verified reads; corrupt signature rejected; handles closed");
    }
}
