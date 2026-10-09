package org.prosperomc;

import java.io.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.zip.*;

/** Java 8 on PS5 reports unavailable adapter queries as Error, not SocketException.
 * Let the pinned Netty class use its existing loopback fallback. The original
 * library is unchanged; this single-class overlay is used only on PS5/1.12.2.
 */
final class NettyCompat {
    static final String ENTRY="io/netty/util/NetUtil.class";
    static final String HASH="7b47c2127cc3b3ed7de881c738434d29c6eb7bce0f33df11aaaf83c87f5987ac";
    static Path prepare(Path root,List<Path> libraries)throws Exception {
        for(Path library:libraries) {
            if(!library.getFileName().toString().equals("netty-all-4.1.9.Final.jar"))continue;
            try(ZipFile zip=new ZipFile(library.toFile())) {
                ZipEntry entry=zip.getEntry(ENTRY);
                if(entry==null)throw new IOException("Netty network class missing");
                byte[] original;
                try(InputStream in=zip.getInputStream(entry)) {
                    ByteArrayOutputStream bytes=new ByteArrayOutputStream();
                    byte[] block=new byte[4096];int n;
                    while((n=in.read(block))!=-1)bytes.write(block,0,n);
                    original=bytes.toByteArray();
                }
                StringBuilder digest=new StringBuilder();
                for(byte value:MessageDigest.getInstance("SHA-256").digest(original))
                    digest.append(String.format(Locale.ROOT,"%02x",value&255));
                if(!HASH.equals(digest.toString()))throw new IOException("Unknown Netty class; compatibility overlay refused");
                Path overlay=root.resolve("compat/netty-4.1.9-ps5.jar");
                Files.createDirectories(overlay.getParent());
                Path pending=overlay.resolveSibling("netty-4.1.9-ps5.pending");
                try(ZipOutputStream out=new ZipOutputStream(Files.newOutputStream(pending))) {
                    out.putNextEntry(new ZipEntry(ENTRY));out.write(patch(original));out.closeEntry();
                    out.putNextEntry(new ZipEntry("META-INF/PROSPEROMC-NOTICE.txt"));
                    out.write(("Netty 4.1.9.Final, Copyright The Netty Project, Apache-2.0.\n"+
                        "https://github.com/netty/netty/tree/netty-4.1.9.Final\n"+
                        "ProsperoMC: network-adapter fallback also handles PS5 Java's Error.\n"+
                        "Original class SHA-256: "+HASH+"\n").getBytes("UTF-8"));out.closeEntry();
                    out.putNextEntry(new ZipEntry("META-INF/LICENSE.txt"));
                    try(InputStream license=NettyCompat.class.getResourceAsStream("/META-INF/NETTY-LICENSE.txt")) {
                        if(license==null)throw new IOException("Netty license missing from launcher");
                        byte[] block=new byte[4096];int n;
                        while((n=license.read(block))!=-1)out.write(block,0,n);
                    }
                    out.closeEntry();
                }
                FilesUtil.atomic(pending,overlay);
                return overlay;
            }
        }
        throw new IOException("Pinned Netty library missing for PS5 LAN compatibility");
    }
    static byte[] patch(byte[] original)throws IOException {
        DataInputStream in=new DataInputStream(new ByteArrayInputStream(original));
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        DataOutputStream out=new DataOutputStream(bytes);
        int magic=in.readInt();if(magic!=0xcafebabe)throw new IOException("Invalid Netty class");
        out.writeInt(magic);out.writeInt(in.readInt());
        int count=in.readUnsignedShort(), changed=0;out.writeShort(count);
        for(int i=1;i<count;i++) {
            int tag=in.readUnsignedByte();out.writeByte(tag);
            if(tag==1) {
                String value=in.readUTF();
                if(value.equals("java/net/SocketException")||value.equals("java/lang/Exception")) {
                    value="java/lang/Throwable";changed++;
                }
                out.writeUTF(value);continue;
            }
            int size;
            switch(tag) {
            case 3:case 4:case 9:case 10:case 11:case 12:case 18:size=4;break;
            case 5:case 6:size=8;i++;break;
            case 7:case 8:case 16:size=2;break;
            case 15:size=3;break;
            default:throw new IOException("Unsupported Netty constant tag: "+tag);
            }
            for(int j=0;j<size;j++)out.writeByte(in.readUnsignedByte());
        }
        if(changed!=2)throw new IOException("Unexpected Netty exception layout");
        byte[] block=new byte[4096];int n;
        while((n=in.read(block))!=-1)out.write(block,0,n);
        return bytes.toByteArray();
    }
}
