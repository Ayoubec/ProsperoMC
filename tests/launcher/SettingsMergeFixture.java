package org.prosperomc;

import java.nio.file.*;
import java.util.*;

/** Reproduce a native settings save while Java runtime work holds an old copy. */
public final class SettingsMergeFixture {
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[0]);
        Main delayed=new Main(root,Collections.<String,String>emptyMap());
        Map<String,String> fresh=FilesUtil.properties(root.resolve("settings.properties"));
        fresh.put("themeColor","amethyst");fresh.put("vrrMode","stable");
        fresh.put("memoryMb","4096");fresh.remove("java8");
        FilesUtil.properties(root.resolve("settings.properties"),fresh);
        delayed.runtimes.ensure(8,false);
        Map<String,String> saved=FilesUtil.properties(root.resolve("settings.properties"));
        if(!"amethyst".equals(saved.get("themeColor"))||!"stable".equals(saved.get("vrrMode"))||
           !"4096".equals(saved.get("memoryMb"))||!saved.containsKey("java8"))
            throw new AssertionError("Runtime registration erased native preferences: "+saved.keySet());
        // An in-flight settings request must also merge only the requested fields.
        Main request=new Main(root,Main.stringMap("command","settings","themeColor","gold"));
        saved.put("vrrMode","auto");saved.put("memoryMb","6144");
        FilesUtil.properties(root.resolve("settings.properties"),saved);
        request.updateSettings();saved=FilesUtil.properties(root.resolve("settings.properties"));
        if(!"gold".equals(saved.get("themeColor"))||!"auto".equals(saved.get("vrrMode"))||
           !"6144".equals(saved.get("memoryMb")))throw new AssertionError("Settings request erased later fields");
        System.out.println("PASS delayed runtime/settings work preserves native theme, VRR and memory");
    }
}
