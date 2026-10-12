package org.prosperomc;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import jdk.jfr.consumer.*;

/** Host-only analysis: emit code locations/timing, never recorded file contents or paths. */
public final class GameplayProfileAnalysis {
    static void count(Map<String,Long> map,String key) {
        if(key==null)key="unnamed";
        if(map.size()<4096||map.containsKey(key))map.put(key,map.getOrDefault(key,0L)+1);
    }
    static String method(RecordedFrame frame) {
        RecordedMethod method=frame.getMethod();
        return method==null?"unknown":method.getType().getName()+"."+method.getName();
    }
    static List<String> frames(RecordedEvent event) {
        List<String> result=new ArrayList<>();RecordedStackTrace trace=event.getStackTrace();
        if(trace!=null)for(RecordedFrame frame:trace.getFrames()) {
            if(result.size()==20)break;result.add(method(frame));
        }
        return result;
    }
    static List<Map<String,Object>> ranked(Map<String,Long> input,int limit) {
        List<Map.Entry<String,Long>> entries=new ArrayList<>(input.entrySet());
        entries.sort((a,b)->Long.compare(b.getValue(),a.getValue()));
        List<Map<String,Object>> result=new ArrayList<>();
        for(Map.Entry<String,Long> entry:entries) {
            if(result.size()==limit)break;Map<String,Object> item=new LinkedHashMap<>();
            item.put("location",entry.getKey());item.put("samples",entry.getValue());result.add(item);
        }
        return result;
    }
    public static Map<String,Object> analyze(Path file)throws Exception {
        Map<String,Long> events=new TreeMap<>(),threads=new TreeMap<>(),renderTop=new HashMap<>(),renderStacks=new HashMap<>();
        List<Map<String,Object>> stalls=new ArrayList<>(),cpu=new ArrayList<>();Instant first=null,last=null;
        long renderSamples=0;
        try(RecordingFile recording=new RecordingFile(file)) {
            while(recording.hasMoreEvents()) {
                RecordedEvent event=recording.readEvent();String name=event.getEventType().getName();count(events,name);
                if(first==null||event.getStartTime().isBefore(first))first=event.getStartTime();
                if(last==null||event.getEndTime().isAfter(last))last=event.getEndTime();
                if(name.equals("jdk.ExecutionSample")||name.equals("jdk.NativeMethodSample")) {
                    RecordedThread thread=event.getThread("sampledThread");if(thread==null)continue;
                    count(threads,thread.getJavaName());
                    if("Render thread".equals(thread.getJavaName())) {
                        renderSamples++;List<String> trace=frames(event);
                        if(!trace.isEmpty())count(renderTop,name+": "+trace.get(0));
                        count(renderStacks,String.join(" <- ",trace));
                    }
                }
                double ms=event.getDuration().toNanos()/1000000.0;
                if(ms>=20&&!name.equals("jdk.ActiveRecording")) {
                    Map<String,Object> item=new LinkedHashMap<>();item.put("event",name);
                    item.put("time",event.getStartTime().toString());item.put("ms",ms);
                    RecordedThread thread=event.getThread();item.put("thread",thread==null?"":thread.getJavaName());
                    item.put("frames",frames(event));stalls.add(item);
                    stalls.sort((a,b)->Double.compare((Double)b.get("ms"),(Double)a.get("ms")));
                    if(stalls.size()>80)stalls.remove(stalls.size()-1);
                }
                if(name.equals("jdk.CPULoad")&&cpu.size()<360) {
                    Map<String,Object> item=new LinkedHashMap<>();item.put("time",event.getStartTime().toString());
                    for(String field:new String[]{"jvmUser","jvmSystem","machineTotal"}) {
                        float value=event.getFloat(field);item.put(field,Float.isFinite(value)?value:null);
                    }
                    cpu.add(item);
                }
            }
        }
        Map<String,Object> output=new LinkedHashMap<>();output.put("firstEventUTC",first==null?"":first.toString());
        output.put("lastEventUTC",last==null?"":last.toString());output.put("events",events);
        output.put("sampledThreads",threads);output.put("renderSamples",renderSamples);
        output.put("renderTop",ranked(renderTop,40));output.put("renderStacks",ranked(renderStacks,60));
        output.put("longestEvents",stalls);output.put("cpuLoad",cpu);
        output.put("limits","Samples identify active code; counts are not FPS or exclusive GPU time. CPU load may be unavailable under Wine. Durations can overlap.");
        return output;
    }
    public static void main(String[] args)throws Exception {
        Map<String,Object> result=analyze(Paths.get(args[0]));
        Files.write(Paths.get(args[1]),Json.stringify(result).getBytes(StandardCharsets.UTF_8));
        System.out.println("GAMEPLAY_PROFILE_ANALYZED renderSamples="+result.get("renderSamples")+" events="+result.get("events"));
    }
}
