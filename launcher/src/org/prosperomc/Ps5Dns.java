package org.prosperomc;

import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Java 8 name service for Wine titles whose native resolver is numeric-only.
 * HTTPS bootstraps from the resolver's numeric address. Both resolver and
 * destination certificates retain the JVM's normal verification.
 */
public final class Ps5Dns implements InvocationHandler {
    final String[] endpoints;
    Ps5Dns(String[] endpoints) { this.endpoints=endpoints.clone(); }
    /** Initialize the JVM-wide resolver before a game replaces the context loader. */
    public static void initializeModern()throws Exception {
        try { Class.forName("java.net.spi.InetAddressResolverProvider"); }
        catch(ClassNotFoundException olderJava) { return; }
        InetAddress.getByName("localhost");
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
        String name=IDN.toASCII(hostname,IDN.USE_STD3_ASCII_RULES);
        IOException failure=null;
        for(String endpoint:endpoints) {
            HttpURLConnection connection=null;
            try {
                connection=(HttpURLConnection)new URL(endpoint+"?name="+URLEncoder.encode(name,"UTF-8")+"&type=A").openConnection();
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
                if(!(response.get("Status") instanceof Number)||((Number)response.get("Status")).intValue()!=0||Boolean.TRUE.equals(response.get("TC")))
                    throw new UnknownHostException(name);
                List<InetAddress> addresses=new ArrayList<InetAddress>();
                for(Object item:Json.arr(response.get("Answer"))) {
                    Map<String,Object> answer=Json.obj(item);
                    if(!(answer.get("type") instanceof Number)||((Number)answer.get("type")).intValue()!=1)continue;
                    String ip=Json.text(answer,"data");
                    if(!ip.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}"))throw new IOException("Invalid DNS IPv4 answer");
                    byte[] bytes=new byte[4];String[] parts=ip.split("\\.");
                    for(int j=0;j<4;j++) {int value=Integer.parseInt(parts[j]);if(value>255)throw new IOException("Invalid DNS IPv4 answer");bytes[j]=(byte)value;}
                    addresses.add(InetAddress.getByAddress(hostname,bytes));
                }
                if(addresses.isEmpty())throw new UnknownHostException(name);
                return addresses.toArray(new InetAddress[addresses.size()]);
            } catch(IOException e) {failure=e;}
            catch(IllegalArgumentException e) {failure=new IOException("Invalid DNS response",e);}
            finally {if(connection!=null)connection.disconnect();}
        }
        UnknownHostException error=new UnknownHostException(hostname+": DNS over HTTPS unavailable");
        error.initCause(failure);throw error;
    }
}
