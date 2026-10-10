package org.prosperomc;

import java.io.IOException;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.net.spi.InetAddressResolver;
import java.net.spi.InetAddressResolverProvider;
import java.util.Arrays;
import java.util.stream.Stream;

/** Supported Java 18+ resolver API; reuse the Java 8 HTTPS DNS implementation. */
public final class Ps5ResolverProvider extends InetAddressResolverProvider {
    public String name() { return "ProsperoMC"; }
    public InetAddressResolver get(Configuration configuration) {
        if(!Boolean.getBoolean("prosperomc.ps5Dns"))return configuration.builtinResolver();
        String endpoint=System.getProperty("prosperomc.dnsEndpoint");
        final Ps5Dns dns=new Ps5Dns(endpoint==null?
                new String[]{"https://1.1.1.1/dns-query","https://1.0.0.1/dns-query"}:new String[]{endpoint});
        return new InetAddressResolver() {
            public Stream<InetAddress> lookupByName(String host,LookupPolicy policy)throws UnknownHostException {
                if((policy.characteristics()&LookupPolicy.IPV4)==0)throw new UnknownHostException(host+": IPv4 required by PS5 Wine");
                try { return Arrays.stream(dns.lookup(host)); }
                catch(IOException failure) {
                    UnknownHostException error=new UnknownHostException(host);
                    error.initCause(failure);throw error;
                }
            }
            public String lookupByAddress(byte[] address)throws UnknownHostException {
                return InetAddress.getByAddress(address).getHostAddress();
            }
        };
    }
}
