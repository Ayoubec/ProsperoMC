package org.prosperomc;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

public final class ControlifyCompatFixture {
    static void require(boolean value,String reason) {if(!value)throw new AssertionError(reason);}
    static void jar(Path path,Map<String,String> entries)throws IOException {
        Files.createDirectories(path.getParent());
        try(ZipOutputStream out=new ZipOutputStream(Files.newOutputStream(path))) {
            for(Map.Entry<String,String> entry:entries.entrySet()) {
                out.putNextEntry(new ZipEntry(entry.getKey()));out.write(entry.getValue().getBytes("UTF-8"));out.closeEntry();
            }
        }
    }
    public static void main(String[] args)throws Exception {
        Path temp=Paths.get(args[0]),game=temp.resolve("game"),client=Paths.get(args[1]),mod=Paths.get(args[2]);
        Files.createDirectories(game.resolve("mods"));
        Files.copy(mod,game.resolve("mods/renamed-controller.jar"));
        String options="resourcePacks:[\"vanilla\",\"file/my texture.zip\",\"fabric\"]\r\n"+
            "renderDistance:16\r\nkey_key.attack:key.mouse.left\r\nlastServer:example.invalid\r\n";
        FilesUtil.write(game.resolve("options.txt"),options);
        FilesUtil.write(game.resolve("config/controlify/profile-1.json"),"{\"custom\":\"binding/rumble settings\"}");
        require(!ControlifyCompat.configure(game,client,"emulated"),"keyboard mode untouched");
        require(FilesUtil.read(game.resolve("options.txt")).equals(options),"keyboard options intact");
        ControlifyCompat.select(temp,game,client,"native");
        require(FilesUtil.read(game.resolve("options.txt")).equals(options),"host path untouched");
        require(ControlifyCompat.configure(game,client,"native"),"installed Controlify supported");
        Path pack=game.resolve("resourcepacks/prosperomc-dualsense");
        List<Object> ids=Json.arr(Json.parse(FilesUtil.read(pack.resolve(ControlifyCompat.IDENTIFICATION))));
        Map<String,Object> identity=Json.obj(ids.get(0));
        require(ids.size()==1&&Json.text(identity,"namespace").equals("controlify:dualsense"),"only bridge identity remapped");
        List<Object> hid=Json.arr(Json.arr(identity.get("hids")).get(0));
        require(hid.size()==2&&((Number)hid.get(0)).intValue()==0x45e&&((Number)hid.get(1)).intValue()==0x28e,"exact native bridge VID/PID");
        Map<String,Object> metadata=Json.obj(Json.obj(Json.parse(FilesUtil.read(pack.resolve("pack.mcmeta")))).get("pack"));
        require(((Number)Json.arr(metadata.get("min_format")).get(0)).intValue()==88,"actual26.2 resource format");
        require(!metadata.containsKey("supported_formats")&&!metadata.containsKey("pack_format"),"modern schema has no deprecated legacy fields");
        require(Json.arr(metadata.get("max_format")).equals(Json.arr(metadata.get("min_format"))),"exact modern format range");
        String changed=FilesUtil.read(game.resolve("options.txt"));
        require(changed.contains("resourcePacks:[\"vanilla\",\"file/my texture.zip\",\"fabric\",\"file/prosperomc-dualsense\"]"),"other packs retained in order");
        require(changed.contains("renderDistance:16\nkey_key.attack:key.mouse.left\nlastServer:example.invalid"),"unrelated options retained");
        require(FilesUtil.read(game.resolve("options-prosperomc-before-dualsense.txt")).equals(options),"original exact backup");
        require(FilesUtil.read(game.resolve("config/controlify/profile-1.json")).equals("{\"custom\":\"binding/rumble settings\"}"),"controller profile intact");
        ControlifyCompat.configure(game,client,"native");
        require(FilesUtil.read(game.resolve("options.txt")).equals(changed),"idempotent selection");
        require(FilesUtil.read(game.resolve("options-prosperomc-before-dualsense.txt")).equals(options),"first backup retained");
        // Modern and older resource-version layouts are both read from the client.
        Path oldClient=temp.resolve("old-client.jar");
        jar(oldClient,Collections.singletonMap("version.json","{\"pack_version\":{\"resource\":34}}"));
        ControlifyCompat.configure(game,oldClient,"native");
        metadata=Json.obj(Json.obj(Json.parse(FilesUtil.read(pack.resolve("pack.mcmeta")))).get("pack"));
        require(((Number)metadata.get("pack_format")).intValue()==34,"older format layout");
        require(metadata.containsKey("supported_formats")&&!metadata.containsKey("min_format"),"legacy schema retained");
        // Foreign packs and malformed selections must not be overwritten.
        FilesUtil.write(pack.resolve("prosperomc-managed.json"),"{\"owner\":\"user\"}");
        try {ControlifyCompat.configure(game,client,"native");throw new AssertionError("foreign pack overwritten");}
        catch(IOException expected) {require(expected.getMessage().contains("unmanaged"),"ownership refusal");}
        require(FilesUtil.read(game.resolve("options.txt")).equals(changed),"conflict preserves options");
        FilesUtil.write(game.resolve("options.txt"),"resourcePacks:[42]\nrenderDistance:16\n");
        try {ControlifyCompat.configure(game,client,"native");throw new AssertionError("invalid list overwritten");}
        catch(IOException expected) {}
        require(FilesUtil.read(game.resolve("options.txt")).equals("resourcePacks:[42]\nrenderDistance:16\n"),"invalid options untouched");
        Path absent=temp.resolve("no-controlify");Files.createDirectories(absent);
        require(!ControlifyCompat.configure(absent,client,"native"),"no mod untouched");
        require(!Files.exists(absent.resolve("resourcepacks")),"no unnecessary resource pack");
        System.out.println("CONTROLIFY_COMPAT_PASS: installed Controlify extension contract, actual client format, exact bridge identity, other packs/options/profiles preserved, host/keyboard/no-mod guards, idempotence and ownership/invalid-selection refusal");
    }
}
