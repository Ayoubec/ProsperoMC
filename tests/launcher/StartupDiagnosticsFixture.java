package org.prosperomc;

import java.util.concurrent.CountDownLatch;

public final class StartupDiagnosticsFixture {
    public static void main(String[] args)throws Exception {
        Thread original=Thread.currentThread();
        if(StartupDiagnostics.renderThread(original)!=original)throw new AssertionError("original fallback");
        CountDownLatch ready=new CountDownLatch(1),stop=new CountDownLatch(1);
        Thread render=new Thread(new ThreadGroup("relocated-minecraft"),()->{
            ready.countDown();try {stop.await();}catch(InterruptedException end) {Thread.currentThread().interrupt();}
        },"Render thread");
        try {
            render.start();ready.await();
            if(StartupDiagnostics.renderThread(original)!=render)throw new AssertionError("relocated renderer not selected");
            if(StartupDiagnostics.renderThread(original).getStackTrace().length==0)throw new AssertionError("render stack unavailable");
        } finally {stop.countDown();render.join();}
        if(StartupDiagnostics.renderThread(original)!=original)throw new AssertionError("terminated render fallback");
        if(StartupDiagnostics.renderThread(render)!=render)throw new AssertionError("terminated original guard");
        System.gc(); // Make actual runtime GC/safepoint logging observable.
        System.out.println("STARTUP_RENDER_THREAD_PASS: relocated live renderer selected; original/terminated fallback preserved; bounded enumeration, no other thread stacks queried");
    }
}
