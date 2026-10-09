package org.prosperomc;
import java.net.NetworkInterface;
import java.util.Enumeration;
public final class MockNetworkInterfaces {
    public static int calls;
    public static Enumeration<NetworkInterface> getNetworkInterfaces() {
        calls++;
        throw new Error("IP Helper Library GetIfTable function failed");
    }
}
