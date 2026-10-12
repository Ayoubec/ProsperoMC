package org.prosperomc;

import java.io.*;
import java.net.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import javax.naming.*;
import javax.naming.directory.*;
import javax.naming.spi.*;

public final class ServerDnsFixture {
    static void require(boolean value,String message){if(!value)throw new AssertionError(message);}
    public static final class OtherFactory implements InitialContextFactory {
        public Context getInitialContext(Hashtable<?,?> environment) {
            return (Context)java.lang.reflect.Proxy.newProxyInstance(ServerDnsFixture.class.getClassLoader(),new Class<?>[]{Context.class},
                (proxy,method,args)->method.getName().equals("getNameInNamespace")?"delegated":null);
        }
    }
    static Hashtable<String,String> dnsEnvironment() {
        Hashtable<String,String> environment=new Hashtable<String,String>();
        environment.put(Context.INITIAL_CONTEXT_FACTORY,"com.sun.jndi.dns.DnsContextFactory");
        environment.put(Context.PROVIDER_URL,"dns:");return environment;
    }
    static void directory()throws Exception {
        if("1.8".equals(System.getProperty("java.specification.version")))Ps5Dns.install(System.getProperty("prosperomc.dnsEndpoint"));
        else {Ps5Dns.initializeModern();Ps5Dns.initializeModern();}
        require(InetAddress.getByName("target.invalid").isLoopbackAddress(),"hostname lookup bypassed resolver");
        require(InetAddress.getByName("localhost").isLoopbackAddress(),"localhost changed");
        require(InetAddress.getByName("127.0.0.1").isLoopbackAddress(),"numeric lookup changed");
        try {InetAddress.getByName("missing.invalid");throw new AssertionError("NXDOMAIN resolved");}
        catch(UnknownHostException expected){}
        Ps5DirectoryDns.install();Ps5DirectoryDns.install();
        DirContext context=new InitialDirContext(dnsEnvironment());
        Attributes attributes=context.getAttributes("_minecraft._tcp.play.invalid",new String[]{"SRV"});
        require(attributes.isCaseIgnored(),"Minecraft lowercase SRV lookup not supported");
        String value=attributes.get("srv").get().toString();
        require(value.equals("1 1 25566 target.invalid."),"SRV target/port changed");
        require(context.getAttributes(new CompositeName("_minecraft._tcp.play.invalid"),new String[]{"SRV"}).get("SRV")!=null,"Name query refused");
        require(context.getAttributes("_minecraft._tcp.missing.invalid",new String[]{"SRV"}).get("srv")==null,"NXDOMAIN fabricated");
        require(context.getAttributes("_minecraft._tcp.empty.invalid",new String[]{"SRV"}).get("srv")==null,"empty answer fabricated");
        require(context.getAttributes("_minecraft._tcp.disabled.invalid",new String[]{"SRV"}).get("srv")==null,"disabled service fabricated");
        require(context.getAttributes("dialtone.invalid",new String[]{"TXT"}).get("txt").get().toString().equals("\"example-value\""),"mod TXT changed");
        for(String host:new String[]{"_minecraft._tcp.bad-port.invalid","_minecraft._tcp.bad-target.invalid","_minecraft._tcp.truncated.invalid","_minecraft._tcp.oversized.invalid"}) {
            try{context.getAttributes(host,new String[]{"SRV"});throw new AssertionError("Invalid SRV accepted: "+host);}
            catch(NamingException expected){}
        }
        try{context.getAttributes("play.invalid",new String[]{"LDAP"});throw new AssertionError("unsupported attribute accepted");}
        catch(OperationNotSupportedException expected){}
        context.close();
        Hashtable<String,String> other=new Hashtable<String,String>();
        other.put(Context.INITIAL_CONTEXT_FACTORY,OtherFactory.class.getName());
        Context delegated=new InitialContext(other);require(delegated.getNameInNamespace().equals("delegated"),"non-DNS factory intercepted");delegated.close();
        List<String> console=new ArrayList<String>(),host=new ArrayList<String>();
        Ps5Dns.launchArguments(Paths.get("Z:/data/ProsperoMC"),console,17);
        Ps5Dns.launchArguments(Paths.get("C:/host/ProsperoMC"),host,17);
        require(console.contains("-Dprosperomc.ps5Dns=true")&&host.isEmpty(),"early console DNS flag or host guard failed");
        require(console.contains("--add-opens=java.base/java.net=ALL-UNNAMED"),"Java 17 resolver access missing");
        List<String> modern=new ArrayList<String>();Ps5Dns.launchArguments(Paths.get("Z:/data/ProsperoMC"),modern,25);
        require(modern.size()==1,"modern public resolver given reflective access");
        System.out.println("DIRECTORY_DNS_PASS SRV/TXT, NXDOMAIN, malformed/oversized/truncated answers, unrelated JNDI and console launch flag");
    }
    static void actualMinecraft()throws Exception {
        Ps5Dns.initializeModern();Ps5DirectoryDns.install();
        Class<?> address=Class.forName("net.minecraft.client.multiplayer.resolver.ServerAddress");
        Object requested=address.getMethod("parseString",String.class).invoke(null,"play.invalid");
        Class<?> handler=Class.forName("net.minecraft.client.multiplayer.resolver.ServerRedirectHandler");
        Object redirect=handler.getMethod("createDnsSrvRedirectHandler").invoke(null);
        Optional<?> redirected=(Optional<?>)handler.getMethod("lookupRedirect",address).invoke(redirect,requested);
        require(redirected.isPresent(),"actual Minecraft ignored repaired SRV");
        Object target=redirected.get();
        String host=(String)address.getMethod("getHost").invoke(target);
        int port=(Integer)address.getMethod("getPort").invoke(target);
        Class<?> resolver=Class.forName("net.minecraft.client.multiplayer.resolver.ServerAddressResolver");
        Optional<?> result=(Optional<?>)resolver.getMethod("resolve",address).invoke(resolver.getField("SYSTEM").get(null),target);
        require(result.isPresent(),"actual Minecraft failed target hostname");
        Class<?> resolved=Class.forName("net.minecraft.client.multiplayer.resolver.ResolvedServerAddress");
        InetSocketAddress socket=(InetSocketAddress)resolved.getMethod("asInetSocketAddress").invoke(result.get());
        require(socket.getAddress().isLoopbackAddress()&&socket.getPort()==port,"actual client changed redirect socket");
        // A server-list status exchange, with no account token or login packet.
        try(Socket connection=new Socket()) {
            connection.connect(socket,3000);connection.setSoTimeout(3000);
            ByteArrayOutputStream handshake=new ByteArrayOutputStream();DataOutputStream output=new DataOutputStream(handshake);
            varint(output,0);varint(output,-1);byte[] bytes=host.getBytes("UTF-8");varint(output,bytes.length);output.write(bytes);output.writeShort(port);varint(output,1);
            OutputStream stream=connection.getOutputStream();varint(stream,handshake.size());stream.write(handshake.toByteArray());stream.write(new byte[]{1,0});stream.flush();
            InputStream input=connection.getInputStream();int length=varint(input);require(length>0&&length<65536,"invalid status packet size");
            require(varint(input)==0,"not a server status reply");int jsonSize=varint(input);require(jsonSize>0&&jsonSize<65536,"invalid status JSON size");
            byte[] json=new byte[jsonSize];new DataInputStream(input).readFully(json);
            require(new String(json,"UTF-8").contains("Fixture server"),"wrong server status");
        }
        System.out.println("ACTUAL_MINECRAFT_DNS_STATUS_PASS SRV redirect, IPv4 hostname, TCP status request/reply without login");
    }
    static void varint(OutputStream output,int value)throws IOException {
        do{int bits=value&127;value>>>=7;output.write(value==0?bits:bits|128);}while(value!=0);
    }
    static int varint(InputStream input)throws IOException {
        int value=0;for(int shift=0;shift<35;shift+=7){int bits=input.read();if(bits<0)throw new EOFException();value|=(bits&127)<<shift;if((bits&128)==0)return value;}
        throw new IOException("Invalid VarInt");
    }
    public static void main(String[] args)throws Exception {
        if(args[0].equals("directory"))directory();else actualMinecraft();
    }
}
