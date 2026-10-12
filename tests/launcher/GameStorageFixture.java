package org.prosperomc;

import java.io.IOException;
import java.nio.file.*;
import java.util.*;

/** An actual directory alias retains world files and rejects unrelated mappings. */
public class GameStorageFixture {
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[0]),alias=Paths.get(args[1]),wrong=Paths.get(args[2]);
        Path game=root.resolve("instances/pack-with-spaces/.minecraft");Files.createDirectories(game);
        Path world=game.resolve("saves/New World/level.dat");Files.createDirectories(world.getParent());
        Files.write(world,new byte[]{1,2,3,4});
        Path mapped=GameStorage.onDataDrive(root,game,alias);
        if(!mapped.startsWith(alias)||!Files.isSameFile(mapped,game)||
            !Arrays.equals(Files.readAllBytes(mapped.resolve("saves/New World/level.dat")),new byte[]{1,2,3,4}))
            throw new AssertionError("Game mapping lost the existing world");
        Files.write(mapped.resolve("saves/New World/level.dat"),new byte[]{4,3,2,1});
        if(!Arrays.equals(Files.readAllBytes(world),new byte[]{4,3,2,1}))throw new AssertionError("Alias save/reopen failed");
        try{GameStorage.onDataDrive(root,game,wrong);throw new AssertionError("Unrelated data mapping accepted");}catch(IOException expected){}
        try{GameStorage.onDataDrive(root,wrong,alias);throw new AssertionError("Outside game directory accepted");}catch(IOException expected){}
        if(!GameStorage.gameDirectory(root,game).equals(game))throw new AssertionError("Host game directory changed");
        System.out.println("GAME_STORAGE_ALIAS_PASS: same existing world; write/reopen; wrong/outside mapping rejected; host unchanged");
    }
}
