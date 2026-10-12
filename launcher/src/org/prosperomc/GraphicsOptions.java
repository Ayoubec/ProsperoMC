package org.prosperomc;

import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.zip.ZipFile;

/** Supported game providers: Zink OpenGL and Minecraft's own Vulkan API. */
final class GraphicsOptions {
    static void fullscreen(Path game)throws IOException {
        Path options=FilesUtil.safe(game,"options.txt");
        String before=Files.exists(options)?FilesUtil.read(options):"";
        if(before.length()>256*1024)throw new IOException("Minecraft options exceed expected size");
        List<String> lines=new ArrayList<String>();
        for(String line:before.split("\\r?\\n"))
            if(!line.isEmpty()&&!line.startsWith("fullscreen:")&&!line.startsWith("fullscreenResolution:")&&
               !line.startsWith("overrideWidth:")&&!line.startsWith("overrideHeight:"))lines.add(line);
        lines.add("fullscreen:true");lines.add("fullscreenResolution:");
        lines.add("overrideWidth:0");lines.add("overrideHeight:0");
        String after=String.join("\n",lines)+"\n";
        if(after.equals(before))return;
        Path backup=FilesUtil.safe(game,"options-prosperomc-before-fullscreen.txt");
        if(!before.isEmpty()&&!Files.exists(backup))FilesUtil.write(backup,before);
        FilesUtil.write(options,after);
    }
    static String provider(String saved)throws IOException {
        if(saved==null||saved.equals("opengl")||saved.equals("zink"))return "zink";
        if(saved.equals("vulkan"))return saved;
        throw new IOException("Unknown graphics API");
    }
    static void select(Path game,Path client,String graphics)throws IOException {
        graphics=provider(graphics);
        boolean selectable;
        try(ZipFile jar=new ZipFile(client.toFile())) {
            selectable=jar.getEntry("net/minecraft/client/PreferredGraphicsApi.class")!=null;
        }
        if(!selectable) {
            if(graphics.equals("vulkan"))throw new IOException("This Minecraft version has no built-in Vulkan backend. Choose OpenGL or a Minecraft version with Vulkan support.");
            return;
        }
        Path options=FilesUtil.safe(game,"options.txt");
        String before=Files.exists(options)?FilesUtil.read(options):"";
        if(before.length()>256*1024)throw new IOException("Minecraft options exceed expected size");
        String wanted="preferredGraphicsBackend:\""+(graphics.equals("vulkan")?"vulkan":"opengl")+"\"";
        List<String> lines=new ArrayList<String>();boolean found=false,changed=false;
        for(String line:before.split("\\r?\\n")) {
            if(line.startsWith("preferredGraphicsBackend:")) {
                if(!found)lines.add(wanted);
                changed|=found||!line.equals(wanted);found=true;
            } else if(!line.isEmpty())lines.add(line);
        }
        if(found&&!changed)return;
        if(!found)lines.add(wanted);
        if(!before.isEmpty()) {
            Path backup=FilesUtil.safe(game,"options-prosperomc-before-api.txt");
            if(!Files.exists(backup))FilesUtil.write(backup,before);
        }
        FilesUtil.write(options,String.join("\n",lines)+"\n");
    }
}
