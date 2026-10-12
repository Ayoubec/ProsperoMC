package org.prosperomc;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.locks.LockSupport;
import jdk.jfr.consumer.*;

public class GameplayProfileFixture {
    static volatile boolean running=true;
    static volatile long result;
    static void require(boolean ok,String message) {if(!ok)throw new AssertionError(message);}
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[0]);String instance="profile-fixture";
        Path dir=root.resolve("instances/"+instance+"/.minecraft");Files.createDirectories(dir);
        Path marker=dir.resolve(GameplayProfile.MARKER);
        Files.write(marker,GameplayProfile.REQUEST.getBytes(StandardCharsets.US_ASCII));
        require(GameplayProfile.start(root,instance)==null,"Host launches must not consume the request");
        require(Files.exists(marker),"Host launch consumed marker");
        require(GameplayProfile.armed(root,"other-instance",0,1000)==null,"Wrong instance armed");
        require(GameplayProfile.armed(root,"../profile-fixture",0,1000)==null,"Traversal instance armed");
        Files.write(marker,"invalid".getBytes(StandardCharsets.US_ASCII));
        require(GameplayProfile.armed(root,instance,0,1000)==null,"Invalid request armed");
        require(Files.exists(marker),"Invalid request consumed");
        Files.write(marker,GameplayProfile.REQUEST.getBytes(StandardCharsets.US_ASCII));
        Thread render=new Thread(()->{long value=1;while(running){for(int i=0;i<100000;i++)value=value*1664525+1013904223;result=value;}},"Render thread");
        Thread parked=new Thread(()->{while(running)LockSupport.parkNanos(80000000L);},"Profile waits");
        render.start();parked.start();
        GameplayProfile capture=GameplayProfile.armed(root,instance,0,3000);
        require(capture!=null&&!Files.exists(marker),"Request not consumed");
        require(GameplayProfile.armed(root,instance,0,3000)==null,"Second launch profiled");
        Thread.sleep(6500);capture.finish();running=false;render.join();parked.join();
        List<Path> files=new ArrayList<>();try(java.util.stream.Stream<Path> stream=Files.list(root.resolve("diagnostics"))){stream.forEach(files::add);}
        require(files.size()==1,"Unexpected capture count");
        Set<String> types=new TreeSet<>();int samples=0,waits=0;
        for(RecordedEvent event:RecordingFile.readAllEvents(files.get(0))) {
            String name=event.getEventType().getName();types.add(name);
            require(!name.equals("jdk.JVMInformation")&&!name.equals("jdk.InitialEnvironmentVariable")&&
                !name.equals("jdk.InitialSystemProperty")&&!name.equals("jdk.ObjectAllocationSample"),"Unrequested event recorded: "+name);
            if(name.equals("jdk.ExecutionSample")&&event.getThread("sampledThread")!=null&&
                event.getThread("sampledThread").getJavaName().equals("Render thread"))samples++;
            if(name.equals("jdk.ThreadPark"))waits++;
        }
        require(samples>0&&waits>0,"Missing execution/wait samples "+samples+"/"+waits);
        Map<String,Object> analysis=GameplayProfileAnalysis.analyze(files.get(0));
        require(((Long)analysis.get("renderSamples"))>=samples,"Analyzer lost render samples");
        String summary=Json.stringify(analysis);
        require(summary.contains("Profile waits")&&summary.contains("Render thread"),"Analyzer lost thread evidence");
        require(!summary.contains(root.toString()),"Analyzer leaked recording paths");
        Path cancelled=root.resolve("cancelled.jfr");GameplayProfile pending=GameplayProfile.capture(cancelled,300,1000);
        pending.finish();Thread.sleep(600);require(!Files.exists(cancelled),"Early exit started delayed recording");
        Path early=root.resolve("early.jfr");GameplayProfile shorter=GameplayProfile.capture(early,0,10000);
        Thread.sleep(1500);shorter.finish();shorter.finish();require(Files.size(early)>0,"Early exit lost recording");
        Path invalid=root.resolve("missing-parent/unavailable.jfr");
        GameplayProfile unavailable=GameplayProfile.capture(invalid,0,1000);
        Thread.sleep(1500);unavailable.finish();require(!Files.exists(invalid),"Invalid destination unexpectedly created");
        require(Files.size(files.get(0))<32L*1024*1024,"Unexpectedly large fixture recording");
        System.out.println("GAMEPLAY_PROFILE_PASS samples="+samples+" waits="+waits+" events="+types);
    }
}
