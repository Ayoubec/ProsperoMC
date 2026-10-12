package org.prosperomc;

import java.nio.file.*;
import java.lang.reflect.*;
import java.util.*;

/** Run using the actual Java25 client and libraries, without starting a game. */
public final class PackMetadataCodecFixture {
    static Object decode(String text)throws Exception {
        Object json=Class.forName("com.google.gson.JsonParser").getMethod("parseString",String.class).invoke(null,text);
        Object section=json.getClass().getMethod("getAsJsonObject").invoke(json);
        Object pack=section.getClass().getMethod("get",String.class).invoke(section,"pack");
        Class<?> packType=Class.forName("net.minecraft.server.packs.PackType");
        Object type=packType.getField("CLIENT_RESOURCES").get(null);
        Object mapCodec=Class.forName("net.minecraft.server.packs.metadata.pack.PackFormat").getMethod("packCodec",packType).invoke(null,type);
        Object codec=Class.forName("com.mojang.serialization.MapCodec").getMethod("codec").invoke(mapCodec);
        Class<?> ops=Class.forName("com.mojang.serialization.DynamicOps");
        Object jsonOps=Class.forName("com.mojang.serialization.JsonOps").getField("INSTANCE").get(null);
        return Class.forName("com.mojang.serialization.Decoder").getMethod("parse",ops,Object.class).invoke(codec,jsonOps,pack);
    }
    static boolean success(Object result)throws Exception {
        return ((Optional<?>)Class.forName("com.mojang.serialization.DataResult").getMethod("result").invoke(result)).isPresent();
    }
    public static void main(String[] args)throws Exception {
        Path folder=Paths.get(args[0]),client=Paths.get(args[1]),mod=Paths.get(args[2]);
        Path game=folder.resolve("codec-game");Files.createDirectories(game.resolve("mods"));
        Files.copy(mod,game.resolve("mods/controlify.jar"));
        ControlifyCompat.configure(game,client,"native");
        String fixed=FilesUtil.read(game.resolve("resourcepacks/prosperomc-dualsense/pack.mcmeta"));
        Object valid=decode(fixed);
        if(!success(valid))throw new AssertionError("Actual client rejected generated metadata: "+valid);
        Object old=decode(FilesUtil.read(Paths.get(args[3])));
        if(success(old))throw new AssertionError("Old console pack must reproduce the deprecated-field rejection");
        System.out.println("PACK_METADATA_CODEC_PASS actual26.2 accepts generated controller pack and rejects original: "+old);
    }
}
