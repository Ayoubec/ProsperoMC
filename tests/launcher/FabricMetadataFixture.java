package org.prosperomc;

import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;
import net.fabricmc.loader.impl.metadata.*;

public final class FabricMetadataFixture {
    static void require(boolean value,String reason) {if(!value)throw new AssertionError(reason);}
    static byte[] archive(String text)throws Exception {
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        try(ZipOutputStream zip=new ZipOutputStream(out)) {
            zip.putNextEntry(new ZipEntry("fabric.mod.json"));zip.write(text.getBytes(StandardCharsets.UTF_8));zip.closeEntry();
        }
        return out.toByteArray();
    }
    public static void main(String[] args)throws Exception {
        Path corpus=Paths.get(args[0]),temp=Paths.get(args[1]);int checked=0,multiline=0;
        VersionOverrides versions=new VersionOverrides();DependencyOverrides dependencies=new DependencyOverrides(temp);
        try(java.util.stream.Stream<Path> files=Files.walk(corpus)) {
            for(Path file:(Iterable<Path>)files.filter(p->p.toString().endsWith(".fabric.json")&&!p.getParent().equals(corpus))::iterator) {
                byte[] data=Files.readAllBytes(file);String text=new String(data,StandardCharsets.UTF_8);
                LoaderModMetadata actual=ModMetadataParser.parseMetadata(new ByteArrayInputStream(data),file.toString(),Collections.emptyList(),versions,dependencies,false);
                Map<String,Object> parsed=Json.obj(Json.parseFabric(text));
                require(Json.text(parsed,"id").equals(actual.getId()),"Fabric id "+file);
                require(Json.text(parsed,"description").equals(actual.getDescription()),"Fabric description "+file);
                List<FabricMods.Mod> mods=new ArrayList<>();Set<String> available=new HashSet<>();
                FabricMods.inspect(archive(text),file.toString(),mods,available,0);
                if(!"server".equals(Json.text(parsed,"environment")))require(available.contains(actual.getId()),"dependency inspection "+file);
                if(actual.getDescription().contains("\n"))multiline++;
                checked++;
            }
        }
        require(checked>0&&multiline>0,"real mod corpus covers multiline descriptions");
        String raw="{\"id\":\"example\",\"description\":\"first\nsecond\tline\"}";
        require(Json.text(Json.obj(Json.parseFabric(raw)),"description").equals("first\nsecond\tline"),"raw controls retained");
        require(Json.text(Json.obj(Json.parseFabric("\uFEFF"+raw)),"id").equals("example"),"leading BOM");
        try {Json.parse(raw);throw new AssertionError("strict JSON weakened");}catch(IllegalArgumentException expected) {}
        for(String invalid:Arrays.asList("{\"id\":\"bad\\q\"}","{\"id\":\"unterminated}","{\"id\":\"ok\",}","{\"id\":\"ok\"} extra")) {
            try {Json.parseFabric(invalid);throw new AssertionError("malformed metadata accepted");}catch(IllegalArgumentException expected) {}
        }
        System.out.println("FABRIC_METADATA_PASS descriptors="+checked+" multiline="+multiline+" actual Fabric parser matches; strict JSON and malformed-input guards retained");
    }
}
