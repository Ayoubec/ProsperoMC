package org.prosperomc;

import java.io.*;
import java.util.*;

/** Redirect Source's ordinary READ constructor; preserve OPEN_DELETE and metadata. */
final class ArchiveSourceRedirect {
    private static int u2(byte[] b,int at){return ((b[at]&255)<<8)|(b[at+1]&255);}
    private static int u4(byte[] b,int at){return (u2(b,at)<<16)|u2(b,at+2);}
    private static void put2(byte[] b,int at,int value){b[at]=(byte)(value>>8);b[at+1]=(byte)value;}
    static byte[] redirect(byte[] bytes)throws IOException {
        try{return checked(bytes);}catch(IndexOutOfBoundsException|NegativeArraySizeException error){throw new IOException("Truncated JAR Source class",error);}
    }
    private static byte[] checked(byte[] bytes)throws IOException {
        if(bytes.length<10||u4(bytes,0)!=0xcafebabe)throw new IOException("Invalid JAR Source class");
        int count=u2(bytes,8),at=10,rafClass=0,rafConstructor=0,fileDelete=0;
        int[] offsets=new int[count],tags=new int[count];String[] utf=new String[count];
        for(int n=1;n<count;n++) {
            offsets[n]=at;int tag=tags[n]=bytes[at++]&255;
            switch(tag) {
            case 1:int size=u2(bytes,at);at+=2;utf[n]=new String(bytes,at,size,"UTF-8");at+=size;break;
            case 3:case 4:case 9:case 10:case 11:case 12:case 17:case 18:at+=4;break;
            case 5:case 6:at+=8;n++;break;
            case 7:case 8:case 16:case 19:case 20:at+=2;break;
            case 15:at+=3;break;
            default:throw new IOException("Unknown JAR Source constant tag "+tag);
            }
            if(at>bytes.length)throw new IOException("Truncated JAR Source constants");
        }
        int endConstants=at;
        Set<String> allowed=new HashSet<>(Arrays.asList("<init>(Ljava/io/File;Ljava/lang/String;)V","close()V",
            "seek(J)V","readFully([BII)V","read([BII)I","length()J"));
        for(int n=1;n<count;n++) {
            if(tags[n]==7&&"java/io/RandomAccessFile".equals(utf[u2(bytes,offsets[n]+1)]))rafClass=n;
            if(tags[n]!=10)continue;
            int owner=u2(bytes,offsets[n]+1),nt=u2(bytes,offsets[n]+3);
            String type=utf[u2(bytes,offsets[owner]+1)],name=utf[u2(bytes,offsets[nt]+1)],descriptor=utf[u2(bytes,offsets[nt]+3)];
            if("java/io/RandomAccessFile".equals(type)) {
                if(!allowed.contains(name+descriptor))throw new IOException("Unsupported JAR backing operation: "+name+descriptor);
                if("<init>".equals(name))rafConstructor=n;
            }
            if("java/io/File".equals(type)&&"delete".equals(name)&&"()Z".equals(descriptor))fileDelete=n;
        }
        if(rafClass==0||rafConstructor==0||fileDelete==0||count>65531)throw new IOException("Unexpected JAR Source constants");
        byte[] patched=bytes.clone();int matches=0;
        at+=6;int interfaces=u2(bytes,at);at+=2+2*interfaces;
        int fields=u2(bytes,at);at+=2;for(int i=0;i<fields;i++)at=skipMember(bytes,at);
        int methods=u2(bytes,at);at+=2;
        for(int i=0;i<methods;i++) {
            String method=utf[u2(bytes,at+2)];int attributes=u2(bytes,at+6);at+=8;
            for(int j=0;j<attributes;j++) {
                String attribute=utf[u2(bytes,at)];int length=u4(bytes,at+2);at+=6;
                if("<init>".equals(method)&&"Code".equals(attribute)) {
                    int start=at+8,end=start+u4(bytes,at+4),deletion=-1;
                    List<Integer> news=new ArrayList<>(),constructors=new ArrayList<>();
                    for(int instruction=start;instruction<end;) {
                        int opcode=bytes[instruction]&255;
                        if(opcode==187&&u2(bytes,instruction+1)==rafClass)news.add(instruction);
                        if(opcode==183&&u2(bytes,instruction+1)==rafConstructor)constructors.add(instruction);
                        if(opcode==182&&u2(bytes,instruction+1)==fileDelete)deletion=instruction;
                        instruction=next(bytes,instruction,start,end);
                    }
                    // The first branch deletes its file. Leave it and Windows
                    // openAndDelete untouched; pool only the later READ branch.
                    if(news.size()!=2||constructors.size()!=2||!(news.get(0)<constructors.get(0)&&
                        constructors.get(0)<deletion&&deletion<news.get(1)&&news.get(1)<constructors.get(1)))
                        throw new IOException("Unexpected JAR READ/DELETE constructor layout");
                    put2(patched,news.get(1)+1,count+1);put2(patched,constructors.get(1)+1,count+2);matches++;
                }
                if(length<0||at+length>bytes.length)throw new IOException("Invalid JAR Source attribute length");at+=length;
            }
        }
        if(matches!=1)throw new IOException("JAR READ constructor was not uniquely redirected");
        ByteArrayOutputStream output=new ByteArrayOutputStream(bytes.length+80);DataOutputStream data=new DataOutputStream(output);
        data.write(patched,0,8);data.writeShort(count+3);data.write(patched,10,endConstants-10);
        data.writeByte(1);data.writeUTF("org/prosperomc/zip/ArchiveFile");data.writeByte(7);data.writeShort(count);
        data.writeByte(10);data.writeShort(count+1);data.writeShort(u2(bytes,offsets[rafConstructor]+3));
        data.write(patched,endConstants,patched.length-endConstants);data.flush();return output.toByteArray();
    }
    private static int skipMember(byte[] bytes,int at)throws IOException {
        int attributes=u2(bytes,at+6);at+=8;
        for(int i=0;i<attributes;i++){int size=u4(bytes,at+2);if(size<0)throw new IOException("Invalid member attribute");at+=6+size;}return at;
    }
    private static int next(byte[] bytes,int at,int start,int end)throws IOException {
        int op=bytes[at]&255,size=1;
        if(op==170||op==171) {
            int aligned=at+1;while((aligned-start)%4!=0)aligned++;
            long entries=op==170?(long)u4(bytes,aligned+8)-u4(bytes,aligned+4)+1:u4(bytes,aligned+4);
            long next=aligned+(op==170?12:8)+entries*(op==170?4:8);
            if(entries<0||next>end)throw new IOException("Invalid JAR switch");return (int)next;
        }
        if(op==196)size=(bytes[at+1]&255)==132?6:4;
        else if(op==185||op==186||op==200||op==201)size=5;
        else if(op==197)size=4;
        else if(op==17||op==19||op==20||op==132||(op>=153&&op<=168)||(op>=178&&op<=184)||
            op==187||op==189||op==192||op==193||op==198||op==199)size=3;
        else if(op==16||op==18||(op>=21&&op<=25)||(op>=54&&op<=58)||op==169||op==188)size=2;
        if(op>201||at+size>end)throw new IOException("Invalid JAR bytecode");return at+size;
    }
}
