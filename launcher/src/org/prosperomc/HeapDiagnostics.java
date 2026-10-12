package org.prosperomc;

import java.lang.management.ManagementFactory;

/** Report the configured budget separately from the collector's usable estimate. */
final class HeapDiagnostics {
    static void probe() {
        String configured="unknown";
        for(String arg:ManagementFactory.getRuntimeMXBean().getInputArguments())
            if(arg.matches("-Xmx[0-9]+[mMgGkK]?"))configured=arg.substring(4);
        Runtime runtime=Runtime.getRuntime();
        System.out.println("PS5 JVM heap: configured="+configured+" reportedMiB="+
            runtime.maxMemory()/(1024*1024)+" committedMiB="+runtime.totalMemory()/(1024*1024));
    }
}
