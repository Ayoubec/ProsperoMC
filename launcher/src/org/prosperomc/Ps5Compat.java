package org.prosperomc;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.net.InetAddress;
import java.io.DataInputStream;
import java.io.FileInputStream;
import java.io.IOException;
import java.security.Provider;
import java.security.ProviderException;
import java.security.SecureRandomSpi;
import java.security.Security;

/** Local-address compatibility for the bundled Java 8 on PS5 Wine. */
public final class Ps5Compat {
    static void localAddress() throws Exception {
        System.setProperty("java.net.preferIPv4Stack", "true");
        // Java 8's native local-host fallback enumerates unsupported IP Helper
        // tables. The app's Wine hostname is localhost, so supply that address.
        Field cache=InetAddress.class.getDeclaredField("cachedLocalHost");
        cache.setAccessible(true);
        Constructor<?> constructor=cache.getType().getDeclaredConstructor(String.class,InetAddress.class);
        constructor.setAccessible(true);
        Object local=constructor.newInstance("localhost",InetAddress.getByAddress("localhost",new byte[]{127,0,0,1}));
        Field expiry=cache.getType().getDeclaredField("expiryTime");
        expiry.setAccessible(true);
        expiry.setLong(local,Long.MAX_VALUE);
        cache.set(null,local);
        // The Windows seeder falls back to the same unsupported adapter call.
        // Read actual kernel entropy; fail explicitly if the device is absent.
        KernelRandom.entropy(new byte[32]);
        Security.insertProviderAt(new Provider("PS5Kernel",1.0,"PS5 kernel random device") {
            private static final long serialVersionUID=1L;
            { put("SecureRandom.PS5Kernel",KernelRandom.class.getName()); }
        },1);
        Ps5Dns.install();
        // Netty otherwise enumerates adapters to identify even local channels.
        // Its supported override uses a random local identifier, as its own
        // fallback does on a machine with no suitable adapter.
        if(System.getProperty("io.netty.machineId")==null) {
            byte[] identity=new byte[8];
            KernelRandom.entropy(identity);
            identity[0]=(byte)((identity[0]&0xfe)|0x02);
            StringBuilder machine=new StringBuilder(23);
            for(byte value:identity) {
                if(machine.length()>0)machine.append(':');
                int octet=value&255;
                machine.append("0123456789abcdef".charAt(octet>>>4));
                machine.append("0123456789abcdef".charAt(octet&15));
            }
            System.setProperty("io.netty.machineId",machine.toString());
        }
    }

    public static final class KernelRandom extends SecureRandomSpi {
        private static final long serialVersionUID=1L;
        protected void engineSetSeed(byte[] seed) { /* Kernel manages its own seed. */ }
        protected void engineNextBytes(byte[] bytes) { entropy(bytes); }
        protected byte[] engineGenerateSeed(int size) { byte[] bytes=new byte[size]; entropy(bytes); return bytes; }
        static void entropy(byte[] bytes) {
            IOException failure=null;
            for(String path:new String[]{"Z:\\dev\\urandom","Z:\\dev\\random"}) {
                try(DataInputStream input=new DataInputStream(new FileInputStream(path))) {
                    input.readFully(bytes);
                    return;
                } catch(IOException e) { failure=e; }
            }
            throw new ProviderException("PS5 kernel random device unavailable",failure);
        }
    }
}
