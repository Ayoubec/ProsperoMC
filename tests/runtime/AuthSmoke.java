package org.prosperomc;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Fake HTTPS provider: no real codes, credentials, account or network access. */
public final class AuthSmoke {
    static String reply="pending";
    static final AtomicInteger calls=new AtomicInteger();
    static void check(boolean condition,String message) {
        if(!condition)throw new AssertionError(message);
    }
    static Map<String,Object> pending() {
        return Auth.map("device_code","fixture-private-device","user_code","ABCD1234",
            "verification_uri","https://microsoft.com/link","interval",5,
            "expiresAt",0,"nextPollAt",Long.MAX_VALUE,"client_id",Auth.POLYMC_CLIENT_ID);
    }
    static void resetPoll()throws Exception {
        java.lang.reflect.Field gate=Auth.class.getDeclaredField("nextPollNanos");
        gate.setAccessible(true);gate.setLong(null,0);
    }
    public static void main(String[] args)throws Exception {
        URL.setURLStreamHandlerFactory(protocol->!protocol.equals("https")?null:new URLStreamHandler() {
            protected URLConnection openConnection(URL url) {
                return new HttpURLConnection(url) {
                    final ByteArrayOutputStream sent=new ByteArrayOutputStream();
                    public void connect() {} public void disconnect() {} public boolean usingProxy(){return false;}
                    public OutputStream getOutputStream(){return sent;}
                    public int getResponseCode(){calls.incrementAndGet();return 400;}
                    public InputStream getErrorStream(){
                        String error=reply.equals("expired")?"expired_token":"authorization_pending";
                        return new ByteArrayInputStream(("{\"error\":\""+error+"\"}").getBytes(StandardCharsets.UTF_8));
                    }
                };
            }
        });
        Path root=Paths.get(args[0]);Files.createDirectories(root);
        Main app=new Main(root,Collections.emptyMap());
        app.auth.save("auth-pending.json",pending());
        app.auth.poll();
        check(calls.get()==1,"Provider must decide expiry even with a past local deadline");
        check(Files.isRegularFile(root.resolve("private/auth-pending.json")),"Pending authorization survives local deadline");
        app.auth.poll();check(calls.get()==1,"Manual checks respect the monotonic poll interval");
        Main next=new Main(root,Collections.emptyMap());next.auth.pendingView();
        check("ABCD1234".equals(next.authView.get("auth.userCode")),"Code survives new launcher request");
        reply="expired";resetPoll();
        try { next.auth.poll();throw new AssertionError("Provider expiry must fail"); }
        catch(IOException error){check(error.getMessage().contains("expired_token"),"Provider rejection remains explicit");}
        check(!Files.exists(root.resolve("private/auth-pending.json")),"Expired provider code removed");
        check(next.authView.isEmpty(),"Stale QR/code removed");
        reply="pending";app.auth.save("auth-pending.json",pending());resetPoll();
        Path response=root.resolve("response.properties");
        FilesUtil.properties(response,Main.stringMap("command","fixture-user-command","ok","true"));
        int before=calls.get();
        Thread worker=new Thread(()->{try {Main.serve(root);}catch(Exception error){throw new RuntimeException(error);}});
        worker.setDaemon(true);worker.start();
        long limit=System.nanoTime()+10000000000L;
        while(calls.get()==before&&System.nanoTime()<limit)Thread.sleep(50);
        check(calls.get()>before,"Serve polls without Check sign-in or a queued request");
        Thread.sleep(200);
        check("fixture-user-command".equals(FilesUtil.properties(response).get("command")),"Background check cannot complete user command");
        check(!Files.exists(root.resolve("request.properties")),"Background poll needs no queued request file");
        System.out.println("PASS: provider expiry, monotonic interval, persistent code, automatic polling, user-command isolation");
    }
}
