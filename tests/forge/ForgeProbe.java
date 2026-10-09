package org.prosperomc;
import java.nio.file.*;
import java.util.*;
public final class ForgeProbe {
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[0]);
        Map<String,String> request=Main.stringMap("forgeInstaller",args[1],"forgeInstallerSha1",args[2]);
        Main main=new Main(root,request);
        Map<String,Object> base=Json.obj(Json.parse(FilesUtil.read(Paths.get(args[3]))));
        Map<String,String> instance=Main.stringMap("version",args[4],"loaderVersion",args[5],"loader","forge");
        Map<String,Object> result=ForgeInstaller.install(main.installer,base,instance);
        FilesUtil.write(root.resolve("merged.json"),Json.stringify(result));
        FilesUtil.properties(root.resolve("forge-instance.properties"),instance);
        if(args.length>6&&args[6].equals("download"))main.installer.libraries(result,root.resolve("natives"),true);
        System.out.println("Forge merge passed");
    }
}
