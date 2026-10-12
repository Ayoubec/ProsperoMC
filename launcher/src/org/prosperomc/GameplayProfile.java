package org.prosperomc;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;

/** Explicit, one-run profiling. No JFR dependency is loaded on normal launches. */
final class GameplayProfile {
    static final String MARKER="prosperomc-profile-next";
    static final String REQUEST="render-v1\n";
    private final Path destination;
    private Object recording;
    private Class<?> type;
    private boolean finished;

    private GameplayProfile(Path destination) {this.destination=destination;}

    static GameplayProfile start(Path root,String instance) {
        if(!root.toString().replace('\\','/').equalsIgnoreCase("Z:/data/ProsperoMC"))return null;
        try {
            return armed(root,instance,150000L,180000L);
        } catch(Exception unavailable) {
            // Do not print paths, arguments, account data or exception messages.
            System.out.println("PS5 gameplay profile unavailable: "+unavailable.getClass().getSimpleName());
            return null;
        }
    }

    static GameplayProfile armed(Path root,String instance,long delay,long duration)throws Exception {
        if(!instance.matches("[A-Za-z0-9_-]+"))return null;
        String version=System.getProperty("java.specification.version");
        if(version.startsWith("1.")||Integer.parseInt(version)<17)return null;
        Path marker=root.resolve("instances").resolve(instance).resolve(".minecraft").resolve(MARKER);
        if(!Files.isRegularFile(marker)||Files.size(marker)>32)return null;
        if(!REQUEST.equals(new String(Files.readAllBytes(marker),StandardCharsets.US_ASCII)))return null;
        Path output=root.resolve("diagnostics");
        Files.createDirectories(output);
        // Consume before scheduling: subsequent launches never keep profiling.
        if(!Files.deleteIfExists(marker))return null;
        return capture(output.resolve("gameplay-"+System.currentTimeMillis()+".jfr"),delay,duration);
    }

    static Map<String,String> settings() {
        Map<String,String> settings=new LinkedHashMap<String,String>();
        for(String name:new String[]{"jdk.ExecutionSample","jdk.NativeMethodSample"}) {
            settings.put(name+"#enabled","true");settings.put(name+"#period","20 ms");
        }
        for(String name:new String[]{"jdk.JavaMonitorEnter","jdk.ThreadPark","jdk.ThreadSleep",
                                     "jdk.FileRead","jdk.FileWrite"}) {
            settings.put(name+"#enabled","true");settings.put(name+"#threshold","20 ms");
            settings.put(name+"#stackTrace","true");
        }
        for(String name:new String[]{"jdk.GarbageCollection","jdk.GCPhasePause"})
            settings.put(name+"#enabled","true");
        for(String name:new String[]{"jdk.CPULoad","jdk.ThreadCPULoad"}) {
            settings.put(name+"#enabled","true");settings.put(name+"#period","1 s");
        }
        return settings;
    }

    static GameplayProfile capture(Path destination,final long delay,final long duration) {
        final GameplayProfile profile=new GameplayProfile(destination);
        Thread worker=new Thread(new Runnable() {
            public void run() {
                try {
                    Thread.sleep(delay);
                    if(!profile.begin(duration))return;
                    Thread.sleep(duration);
                } catch(InterruptedException stopped) {
                    Thread.currentThread().interrupt();
                } catch(Exception unavailable) {
                    System.out.println("PS5 gameplay profile unavailable: "+unavailable.getClass().getSimpleName());
                } catch(LinkageError unavailable) {
                    System.out.println("PS5 gameplay profile unavailable: "+unavailable.getClass().getSimpleName());
                } finally {profile.finish();}
            }
        },"ProsperoMC gameplay profile");
        worker.setDaemon(true);worker.start();
        System.out.println("PS5 gameplay profile armed: one run, delayMs="+delay+", durationMs="+duration);
        return profile;
    }

    private synchronized boolean begin(long duration)throws Exception {
        if(finished)return false;
        type=Class.forName("jdk.jfr.Recording");
        recording=type.getConstructor(Map.class).newInstance(settings());
        type.getMethod("setName",String.class).invoke(recording,"ProsperoMC gameplay");
        type.getMethod("setMaxSize",long.class).invoke(recording,32L*1024*1024);
        type.getMethod("setMaxAge",Duration.class).invoke(recording,Duration.ofMillis(duration));
        type.getMethod("setDuration",Duration.class).invoke(recording,Duration.ofMillis(duration));
        type.getMethod("setDestination",Path.class).invoke(recording,destination);
        type.getMethod("setDumpOnExit",boolean.class).invoke(recording,true);
        type.getMethod("start").invoke(recording);
        System.out.println("PS5 gameplay profile started");
        return true;
    }

    synchronized void finish() {
        if(finished)return;
        finished=true;
        if(recording==null)return;
        try {
            String state=String.valueOf(type.getMethod("getState").invoke(recording));
            if("RUNNING".equals(state))type.getMethod("stop").invoke(recording);
            if(Files.isRegularFile(destination)&&Files.size(destination)>0)
                System.out.println("PS5 gameplay profile saved");
            else System.out.println("PS5 gameplay profile ended without recording data");
        } catch(Exception unavailable) {
            System.out.println("PS5 gameplay profile save unavailable: "+unavailable.getClass().getSimpleName());
        } finally {
            try {type.getMethod("close").invoke(recording);}catch(Exception ignored) {}
        }
    }
}
