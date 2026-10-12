package org.prosperomc;

import java.util.List;

/** Bounded startup samples identify a loading stall without a second JVM or debugger. */
final class StartupDiagnostics {
    static void codeCacheArguments(int major,List<String> arguments) {
        if(major<17)return;
        arguments.add("-XX:ReservedCodeCacheSize=384M");
        // Java 25 can force a Parallel full GC after allocating only ~12% of
        // the cache, even with >70% still free. Defer heuristic collections;
        // keep method flushing and the default 10%-free emergency threshold.
        if(major>=25)arguments.add("-XX:SweeperThreshold=50");
    }
    static Thread renderThread(Thread gameThread) {
        ThreadGroup group=gameThread.getThreadGroup();
        if(group==null)return gameThread;
        // Enumerate references, not every thread's stack. IxerIs moves the
        // game loop away from the original main thread, which then waits.
        try {
            while(group.getParent()!=null)group=group.getParent();
            Thread[] threads=new Thread[Math.min(1024,Math.max(64,group.activeCount()+32))];
            int count=group.enumerate(threads,true);
            for(int i=0;i<count;i++)if(threads[i]!=null&&threads[i].isAlive()&&
                "Render thread".equals(threads[i].getName()))return threads[i];
        } catch(SecurityException unavailable) {return gameThread;}
        return gameThread;
    }
    static void start(final Thread gameThread) {
        Thread samples=new Thread(new Runnable() {
            public void run() {
                int previous=0;
                for(int seconds:new int[]{45,120,240}) {
                    try {Thread.sleep((seconds-previous)*1000L);}
                    catch(InterruptedException stopped) {return;}
                    previous=seconds;
                    if(!gameThread.isAlive())return;
                    Thread sampled=renderThread(gameThread);
                    StackTraceElement[] stack=sampled.getStackTrace();
                    System.out.println("PS5 startup sample: elapsed="+seconds+" state="+sampled.getState()+
                        " role="+(sampled==gameThread?"original-main":"render"));
                    // Frames contain code locations only, never game arguments or account values.
                    for(int i=0;i<Math.min(stack.length,20);++i)System.out.println("PS5 startup frame: "+stack[i]);
                }
            }
        },"ProsperoMC startup diagnostics");
        samples.setDaemon(true);
        samples.start();
    }
}
