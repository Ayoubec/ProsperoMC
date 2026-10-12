package org.prosperomc;

import java.lang.management.ManagementFactory;
import java.util.*;
import com.sun.management.HotSpotDiagnosticMXBean;

public final class CodeCachePolicyFixture {
    public static void main(String[] args)throws Exception {
        for(int version:new int[]{8,17,21,25}) {
            List<String> flags=new ArrayList<String>();StartupDiagnostics.codeCacheArguments(version,flags);
            if(args.length>0) {if(version==25)System.out.print(String.join("\n",flags));continue;}
            if(version<17&&!flags.isEmpty())throw new AssertionError("Java 8 flags changed");
            if(version>=17&&!flags.contains("-XX:ReservedCodeCacheSize=384M"))throw new AssertionError("Cache budget changed");
            if(flags.contains("-XX:SweeperThreshold=50")!=(version>=25))throw new AssertionError("Unsupported Java policy");
        }
        if(args.length>0)return;
        HotSpotDiagnosticMXBean bean=ManagementFactory.getPlatformMXBean(HotSpotDiagnosticMXBean.class);
        if(!bean.getVMOption("SweeperThreshold").getValue().equals("50.0"))throw new AssertionError("Policy inactive");
        if(!bean.getVMOption("UseCodeCacheFlushing").getValue().equals("true"))throw new AssertionError("Reclamation disabled");
        if(!bean.getVMOption("StartAggressiveSweepingAt").getValue().equals("10"))throw new AssertionError("Emergency collection disabled");
        if(!bean.getVMOption("ReservedCodeCacheSize").getValue().equals("402653184"))throw new AssertionError("Extra cache reserved");
        if(!bean.getVMOption("UseParallelGC").getValue().equals("true"))throw new AssertionError("Collector changed");
        // Replay both captured allocation requests through the upstream policy.
        for(double[] trace:new double[][]{{5.419,17.756},{17.675,28.418}}) {
            double free=1-trace[1]/100,allocated=trace[1]-trace[0];
            double original=15*(trace[1]>15?free:1),revised=50*(trace[1]>50?free:1);
            if(!(allocated>original&&allocated<revised&&free>0.1))throw new AssertionError("Captured premature triggers unchanged");
        }
        long sum=0;for(int i=0;i<1000000;i++)sum+=Long.rotateLeft(i*2654435761L,i&31);
        if(sum==0)throw new AssertionError("JIT workload failed");
        System.out.println("CODE_CACHE_POLICY_PASS Java25; captured triggers deferred; 384M budget, flushing, 10%-free emergency collection and ParallelGC retained");
    }
}
