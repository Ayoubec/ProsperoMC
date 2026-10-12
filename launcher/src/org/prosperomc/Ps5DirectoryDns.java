package org.prosperomc;

import java.io.IOException;
import java.lang.reflect.*;
import java.util.*;
import javax.naming.*;
import javax.naming.directory.*;
import javax.naming.spi.*;

/** Supply the DNS directory operations used by Minecraft and e4mc, without
 * Windows adapter enumeration. Other initial context factories still delegate. */
final class Ps5DirectoryDns implements InvocationHandler {
    private static boolean installed;
    private final Ps5Dns dns=Ps5Dns.configured();
    private final Hashtable<Object,Object> environment=new Hashtable<Object,Object>();
    private boolean closed;
    private Ps5DirectoryDns(Hashtable<?,?> env) {
        if(env!=null)for(Map.Entry<?,?> entry:env.entrySet())environment.put(entry.getKey(),entry.getValue());
    }
    static synchronized void install()throws NamingException {
        if(installed)return;
        NamingManager.setInitialContextFactoryBuilder(new InitialContextFactoryBuilder() {
            public InitialContextFactory createInitialContextFactory(Hashtable<?,?> env)throws NamingException {
                Object selected=env==null?null:env.get(Context.INITIAL_CONTEXT_FACTORY);
                String factory=selected==null?System.getProperty(Context.INITIAL_CONTEXT_FACTORY):selected.toString();
                Object url=env==null?null:env.get(Context.PROVIDER_URL);
                boolean defaultDns=url==null||url.toString().isEmpty()||url.equals("dns:")||url.equals("dns:/");
                if(defaultDns&&"com.sun.jndi.dns.DnsContextFactory".equals(factory))return new InitialContextFactory() {
                    public Context getInitialContext(Hashtable<?,?> settings) {
                        return (DirContext)Proxy.newProxyInstance(Ps5DirectoryDns.class.getClassLoader(),
                            new Class<?>[]{DirContext.class},new Ps5DirectoryDns(settings));
                    }
                };
                if(factory==null)throw new NoInitialContextException("No initial context factory configured");
                try {
                    ClassLoader loader=Thread.currentThread().getContextClassLoader();
                    for(InitialContextFactory provider:ServiceLoader.load(InitialContextFactory.class,loader))
                        if(provider.getClass().getName().equals(factory))return provider;
                    return (InitialContextFactory)Class.forName(factory,true,loader).getConstructor().newInstance();
                }catch(Exception failure) {
                    NoInitialContextException error=new NoInitialContextException("Initial context factory unavailable: "+factory);
                    error.setRootCause(failure);throw error;
                }
            }
        });
        installed=true;
        System.out.println("PS5 DNS: Minecraft SRV and mod TXT discovery active");
    }
    public Object invoke(Object proxy,Method method,Object[] args)throws Exception {
        String name=method.getName();
        if(name.equals("toString"))return "ProsperoMC HTTPS DNS directory";
        if(name.equals("hashCode"))return System.identityHashCode(proxy);
        if(name.equals("equals"))return proxy==args[0];
        if(name.equals("close")){closed=true;return null;}
        if(closed)throw new NamingException("DNS context is closed");
        if(name.equals("getEnvironment"))return environment.clone();
        if(name.equals("addToEnvironment"))return environment.put(args[0],args[1]);
        if(name.equals("removeFromEnvironment"))return environment.remove(args[0]);
        if(name.equals("getNameInNamespace"))return "";
        if(name.equals("getAttributes")) {
            String host=args[0].toString();
            String[] types=args.length==2?(String[])args[1]:new String[]{"A","SRV","TXT"};
            if(types==null)types=new String[]{"A","SRV","TXT"};
            Attributes attributes=new BasicAttributes(true);
            for(String type:types) {
                int number="A".equalsIgnoreCase(type)?1:"SRV".equalsIgnoreCase(type)?33:"TXT".equalsIgnoreCase(type)?16:0;
                if(number==0)throw new OperationNotSupportedException("Unsupported DNS attribute: "+type);
                try {
                    List<String> values=dns.records(host,number);
                    if(!values.isEmpty()) {
                        BasicAttribute attribute=new BasicAttribute(type.toUpperCase(Locale.ROOT));
                        for(String value:values)attribute.add(value);
                        attributes.put(attribute);
                    }
                }catch(IOException failure) {
                    NamingException error=new NamingException("DNS query failed: "+host);
                    error.setRootCause(failure);throw error;
                }
            }
            return attributes;
        }
        throw new OperationNotSupportedException("DNS context operation: "+name);
    }
}
