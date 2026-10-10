package org.prosperomc.testing;

import java.net.InetAddress;
import java.net.spi.InetAddressResolver;
import java.net.spi.InetAddressResolverProvider;
import java.nio.file.Paths;
import java.lang.reflect.Method;
import java.util.ServiceLoader;
import net.fabricmc.api.EnvType;

/** Exercise the installed Fabric loader's raw class/resource loading, without a game. */
public final class FabricDnsSmoke {
    public static void main(String[] args)throws Exception {
        System.setProperty("prosperomc.ps5Dns","true");
        Class<?> type=Class.forName("net.fabricmc.loader.impl.launch.knot.KnotClassLoaderInterface");
        Method create=type.getDeclaredMethod("create",boolean.class,boolean.class,EnvType.class,Class.forName("net.fabricmc.loader.impl.game.GameProvider"));
        create.setAccessible(true);
        Object knot=create.invoke(null,false,false,EnvType.CLIENT,null);
        Method add=type.getDeclaredMethod("addCodeSource",java.nio.file.Path.class);add.setAccessible(true);
        add.invoke(knot,Paths.get(args[0]));
        Method loader=type.getDeclaredMethod("getClassLoader");loader.setAccessible(true);
        InetAddressResolverProvider provider=ServiceLoader.load(InetAddressResolverProvider.class,(ClassLoader)loader.invoke(knot)).findFirst().orElseThrow();
        InetAddress address=provider.get(null).lookupByName("localhost",InetAddressResolver.LookupPolicy.of(InetAddressResolver.LookupPolicy.IPV4)).findFirst().orElseThrow();
        if(!address.isLoopbackAddress())throw new AssertionError();
        System.out.println("FABRIC_DNS_PASS "+provider.name()+" Java "+System.getProperty("java.specification.version"));
    }
}
