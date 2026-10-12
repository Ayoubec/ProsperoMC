package org.prosperomc;

import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.nio.file.Path;

/** Java 8 name service for Wine titles whose native resolver is numeric-only.
 * HTTPS bootstraps from the resolver's numeric address. Both resolver and
 * destination certificates retain the JVM's normal verification.
 */
public final class Ps5Dns implements InvocationHandler {
    final String[] endpoints;
    Ps5Dns(String[] endpoints) { this.endpoints=endpoints.clone(); }
    static Ps5Dns configured() {
        String endpoint=System.getProperty("prosperomc.dnsEndpoint");
        return new Ps5Dns(endpoint==null?new String[]{"https://1.1.1.1/dns-query","https://1.0.0.1/dns-query"}:new String[]{endpoint});
    }
    static void launchArguments(Path root,List<String> arguments,int javaMajor) {
        if(root.toString().replace('\\','/').equalsIgnoreCase("Z:/data/ProsperoMC")) {
            arguments.add("-Dprosperomc.ps5Dns=true");
            // Java 17 predates the public resolver SPI introduced in Java 18.
            if(javaMajor==17)arguments.add("--add-opens=java.base/java.net=ALL-UNNAMED");
        }
    }
    /** Initialize the JVM-wide resolver before a game replaces the context loader. */
    public static void initializeModern()throws Exception {
        try { Class.forName("java.net.spi.InetAddressResolverProvider"); }
        catch(ClassNotFoundException olderJava) {
            if("17".equals(System.getProperty("java.specification.version")))installJava17();
            return;
        }
        InetAddress.getByName("localhost");
    }
    private static boolean java17Installed;
    private static synchronized void installJava17()throws Exception {
        if(java17Installed)return;
        InetAddress.getByName("localhost");
        Class<?> service=Class.forName("java.net.InetAddress$NameService");
        Object proxy=java.lang.reflect.Proxy.newProxyInstance(service.getClassLoader(),new Class<?>[]{service},configured());
        Field field=InetAddress.class.getDeclaredField("nameService");field.setAccessible(true);
        field.set(null,proxy);java17Installed=true;
        System.out.println("PS5 DNS: Java 17 IPv4 hostname resolver active");
    }
    public static void install(String... endpoints)throws Exception {
        if(endpoints.length==0)endpoints=new String[]{"https://1.1.1.1/dns-query","https://1.0.0.1/dns-query"};
        Class<?> service=Class.forName("sun.net.spi.nameservice.NameService");
        Object proxy=java.lang.reflect.Proxy.newProxyInstance(service.getClassLoader(),new Class<?>[]{service},new Ps5Dns(endpoints));
        Field field=InetAddress.class.getDeclaredField("nameServices");field.setAccessible(true);
        @SuppressWarnings("unchecked") List<Object> services=(List<Object>)field.get(null);
        services.add(0,proxy);
    }
    public Object invoke(Object proxy,Method method,Object[] args)throws Exception {
        if(method.getName().equals("lookupAllHostAddr"))return lookup((String)args[0]);
        if(method.getName().equals("getHostByAddr"))return InetAddress.getByAddress((byte[])args[0]).getHostAddress();
        if(method.getName().equals("toString"))return "ProsperoMC DNS over HTTPS";
        if(method.getName().equals("hashCode"))return System.identityHashCode(proxy);
        if(method.getName().equals("equals"))return proxy==args[0];
        throw new UnsupportedOperationException(method.getName());
    }
    InetAddress[] lookup(String hostname)throws IOException {
        if(hostname.isEmpty()||"localhost".equalsIgnoreCase(hostname))return new InetAddress[]{InetAddress.getByAddress(hostname,new byte[]{127,0,0,1})};
        List<InetAddress> addresses=new ArrayList<InetAddress>();
        for(String ip:records(hostname,1))addresses.add(InetAddress.getByAddress(hostname,ipv4(ip)));
        if(addresses.isEmpty())throw new UnknownHostException(hostname);
        return addresses.toArray(new InetAddress[addresses.size()]);
    }
    static byte[] ipv4(String ip)throws IOException {
        if(!ip.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}"))throw new IOException("Invalid DNS IPv4 answer");
        byte[] bytes=new byte[4];String[] parts=ip.split("\\.");
        for(int j=0;j<4;j++) {int value=Integer.parseInt(parts[j]);if(value>255)throw new IOException("Invalid DNS IPv4 answer");bytes[j]=(byte)value;}
        return bytes;
    }
    static String dnsName(String hostname,boolean service)throws IOException {
        try {
            if(hostname.endsWith("."))hostname=hostname.substring(0,hostname.length()-1);
            StringBuilder name=new StringBuilder();
            for(String label:hostname.split("\\.",-1)) {
                boolean underscore=service&&label.startsWith("_");
                String ascii=IDN.toASCII(underscore?label.substring(1):label,IDN.USE_STD3_ASCII_RULES);
                if(ascii.isEmpty()||ascii.length()+(underscore?1:0)>63)throw new IllegalArgumentException("Invalid DNS label");
                if(name.length()>0)name.append('.');if(underscore)name.append('_');name.append(ascii);
            }
            if(name.length()>253)throw new IllegalArgumentException("DNS name too long");
            return name.toString();
        }catch(IllegalArgumentException invalid){throw new IOException("Invalid DNS name",invalid);}
    }
    /** SRV/TXT use the same verified HTTPS transport as hostname lookups. */
    List<String> records(String hostname,int type)throws IOException {
        if(type!=1&&type!=33&&type!=16)throw new IOException("Unsupported DNS record type");
        String name=dnsName(hostname,type!=1);
        IOException failure=null;
        for(String endpoint:endpoints) {
            HttpURLConnection connection=null;
            try {
                String record=type==1?"A":type==33?"SRV":"TXT";
                connection=(HttpURLConnection)new URL(endpoint+"?name="+URLEncoder.encode(name,"UTF-8")+"&type="+record).openConnection();
                connection.setConnectTimeout(5000);connection.setReadTimeout(5000);connection.setInstanceFollowRedirects(false);
                connection.setRequestProperty("Accept","application/dns-json");
                connection.setRequestProperty("User-Agent","Ayoubec/ProsperoMC");
                if(connection.getResponseCode()!=200)throw new IOException("DNS HTTPS response "+connection.getResponseCode());
                ByteArrayOutputStream data=new ByteArrayOutputStream();
                try(InputStream input=connection.getInputStream()) {
                    byte[] buffer=new byte[4096];int n;
                    while((n=input.read(buffer))!=-1) {if(data.size()+n>65536)throw new IOException("DNS response too large");data.write(buffer,0,n);}
                }
                Map<String,Object> response=Json.obj(Json.parse(new String(data.toByteArray(),StandardCharsets.UTF_8)));
                if(!(response.get("Status") instanceof Number)||Boolean.TRUE.equals(response.get("TC")))throw new IOException("Invalid DNS response status");
                int status=((Number)response.get("Status")).intValue();
                if(status==3)return Collections.emptyList(); // Genuine NXDOMAIN, no fabricated address.
                if(status!=0)throw new IOException("DNS response status "+status);
                List<String> records=new ArrayList<String>();
                for(Object item:Json.arr(response.get("Answer"))) {
                    Map<String,Object> answer=Json.obj(item);
                    if(!(answer.get("type") instanceof Number)||((Number)answer.get("type")).intValue()!=type)continue;
                    String value=Json.text(answer,"data");
                    if(value.length()>4096||value.matches("(?s).*[\\x00\\r\\n].*"))throw new IOException("Invalid DNS answer");
                    if(type==1)ipv4(value);
                    if(type==33) {
                        String[] parts=value.trim().split("\\s+");
                        if(parts.length!=4)throw new IOException("Invalid DNS SRV answer");
                        for(int j=0;j<3;j++)if(!parts[j].matches("[0-9]{1,5}")||Integer.parseInt(parts[j])>65535)
                            throw new IOException("Invalid DNS SRV number");
                        if(parts[3].equals("."))continue; // Service explicitly unavailable.
                        dnsName(parts[3],false);
                        if(Integer.parseInt(parts[2])==0)throw new IOException("Invalid DNS SRV port");
                        value=String.join(" ",parts);
                    }
                    records.add(value);
                }
                return records;
            } catch(IOException e) {failure=e;}
            catch(IllegalArgumentException e) {failure=new IOException("Invalid DNS response",e);}
            finally {if(connection!=null)connection.disconnect();}
        }
        UnknownHostException error=new UnknownHostException(hostname+": DNS over HTTPS unavailable");
        error.initCause(failure);throw error;
    }
}
