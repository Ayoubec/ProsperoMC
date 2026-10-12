package org.prosperomc;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
public class GameplayProfileLegacyFixture {
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[0]);Path folder=root.resolve("instances/legacy/.minecraft");Files.createDirectories(folder);
        Path marker=folder.resolve(GameplayProfile.MARKER);Files.write(marker,GameplayProfile.REQUEST.getBytes(StandardCharsets.US_ASCII));
        if(GameplayProfile.armed(root,"legacy",0,1)!=null||!Files.exists(marker))throw new AssertionError("Legacy JVM consumed request");
        if(Files.exists(root.resolve("diagnostics")))throw new AssertionError("Legacy JVM initialized profiler");
        System.out.println("GAMEPLAY_PROFILE_LEGACY_PASS");
    }
}
