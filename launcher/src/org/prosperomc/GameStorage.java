package org.prosperomc;

import java.io.IOException;
import java.nio.file.*;

/** Give Minecraft the existing data drive so FileStore queries reach /data. */
final class GameStorage {
    static Path gameDirectory(Path root,Path game)throws IOException {
        if(!root.toString().replace('\\','/').equalsIgnoreCase("Z:/data/ProsperoMC"))return game;
        return onDataDrive(root,game,Paths.get("P:\\"));
    }
    static Path onDataDrive(Path root,Path game,Path dataDrive)throws IOException {
        Path base=root.toAbsolutePath().normalize(),child=game.toAbsolutePath().normalize();
        if(!child.startsWith(base))throw new IOException("Minecraft directory is outside the launcher data directory");
        if(!Files.isDirectory(dataDrive)||!Files.isSameFile(base,dataDrive))
            throw new IOException("Minecraft data drive P: does not map to the launcher data directory");
        Path mapped=dataDrive.resolve(base.relativize(child));
        if(!Files.isSameFile(child,mapped))throw new IOException("Minecraft data-drive directory does not match its existing files");
        System.out.println("PS5 Minecraft storage: existing game directory on data drive "+mapped);
        return mapped;
    }
}
