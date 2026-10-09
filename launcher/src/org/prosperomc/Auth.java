package org.prosperomc;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
/** Microsoft device authorization. Requires the developer's own registered public client ID. */
final class Auth {
    final Main app;
    final Path privateDir;
    Auth(Main a) {
        app=a;
        privateDir=a.root.resolve("private");
    }
    static Map<String, Object> map(Object... kv) {
        Map<String, Object> m=new LinkedHashMap<String, Object>();
        for(int i=0; i<kv.length; i+=2)m.put((String)kv[i], kv[i+1]);
        return m;
    }
    String client()throws IOException {
        String s=app.settings.getOrDefault("microsoftClientId", "");
        if(s.isEmpty())throw new IOException("Set microsoftClientId to your registered Microsoft public client application ID before signing in");
        return s;
    }
    static String form(Map<String, Object> m)throws IOException {
        StringBuilder b=new StringBuilder();
        for(Map.Entry<String, Object> e:m.entrySet()) {
            if(b.length()>0)b.append('&');
            b.append(URLEncoder.encode(e.getKey(), "UTF-8")).append('=').append(URLEncoder.encode(Json.str(e.getValue()), "UTF-8"));
        }
        return b.toString();
    }
    Map<String, Object> request(String url, String method, Object body, String token)throws IOException {
        HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();
        c.setConnectTimeout(20000);
        c.setReadTimeout(30000);
        c.setRequestMethod(method);
        c.setRequestProperty("User-Agent", "ProsperoMC/0.1");
        c.setRequestProperty("Accept", "application/json");
        if(token!=null)c.setRequestProperty("Authorization", "Bearer "+token);
        if(body!=null) {
            c.setDoOutput(true);
            boolean isForm=body instanceof String;
            c.setRequestProperty("Content-Type", isForm?"application/x-www-form-urlencoded":"application/json");
            byte[] bytes=(isForm?(String)body:Json.stringify(body)).getBytes(StandardCharsets.UTF_8);
            try(OutputStream out=c.getOutputStream()) {
                out.write(bytes);
            }
        }
        int status=c.getResponseCode();
        InputStream stream=status>=400?c.getErrorStream():c.getInputStream();
        if(stream==null)throw new IOException("Authentication service returned HTTP "+status);
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        try(InputStream in=stream) {
            byte[] b=new byte[8192];
            int n;
            while((n=in.read(b))>=0) {
                if(out.size()+n>2*1024*1024)throw new IOException("Authentication response exceeds limit");
                out.write(b, 0, n);
            }
        }
        Map<String, Object> result=Json.obj(Json.parse(new String(out.toByteArray(), StandardCharsets.UTF_8)));
        if(status>=400) {
            String error=Json.text(result, "error");
            if(error.equals("authorization_pending")||error.equals("slow_down"))return result;
            throw new IOException("Authentication rejected (HTTP "+status+"): "+(error.matches("[a-zA-Z0-9_]+")?error:"service error"));
        }
        return result;
    }
    void device()throws IOException {
        Map<String, Object> r=request("https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode", "POST", form(map("client_id", client(), "scope", "XboxLive.signin offline_access")), null);
        long expires=((Number)r.get("expires_in")).longValue();
        r.put("expiresAt", System.currentTimeMillis()+expires*1000);
        r.put("nextPollAt", System.currentTimeMillis()+((Number)r.get("interval")).longValue()*1000);
        save("auth-pending.json", r);
        app.authView.put("auth.userCode", Json.text(r, "user_code"));
        app.authView.put("auth.verificationUri", Json.text(r, "verification_uri"));
        app.authView.put("auth.interval", Json.str(r.get("interval")));
        app.authView.put("auth.expiresIn", Long.toString(expires));
        app.message="Open "+Json.text(r, "verification_uri")+" and enter "+Json.text(r, "user_code");
    }
    void poll()throws IOException {
        Path p=privateDir.resolve("auth-pending.json");
        if(!Files.isRegularFile(p))throw new IOException("Start Microsoft device sign-in first");
        Map<String, Object> pending=Json.obj(Json.parse(FilesUtil.read(p)));
        if(System.currentTimeMillis()>((Number)pending.get("expiresAt")).longValue()) {
            Files.delete(p);
            throw new IOException("Device code expired; start sign-in again");
        }
        app.authView.put("auth.userCode", Json.text(pending, "user_code"));
        app.authView.put("auth.verificationUri", Json.text(pending, "verification_uri"));
        app.authView.put("auth.interval", Json.str(pending.get("interval")));
        if(System.currentTimeMillis()<((Number)pending.get("nextPollAt")).longValue()) {
            app.message="Waiting for authorization (poll interval)";
            return;
        }
        Map<String, Object> result=request("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", "POST", form(map("client_id", client(), "grant_type", "urn:ietf:params:oauth:grant-type:device_code", "device_code", pending.get("device_code"))), null);
        if(result.containsKey("error")) {
            long interval=((Number)pending.get("interval")).longValue();
            if("slow_down".equals(result.get("error")))interval+=5;
            pending.put("interval", interval);
            pending.put("nextPollAt", System.currentTimeMillis()+interval*1000);
            save("auth-pending.json", pending);
            app.message="Waiting for Microsoft authorization";
            return;
        }
        exchange(result);
        Files.delete(p);
        app.message="Microsoft account signed in and Minecraft ownership verified";
    }
    void exchange(Map<String, Object> oauth)throws IOException {
        Map<String, Object> xbox=request("https://user.auth.xboxlive.com/user/authenticate", "POST", map("Properties", map("AuthMethod", "RPS", "SiteName", "user.auth.xboxlive.com", "RpsTicket", "d="+Json.text(oauth, "access_token")), "RelyingParty", "http://auth.xboxlive.com", "TokenType", "JWT"), null);
        Map<String, Object> xsts=request("https://xsts.auth.xboxlive.com/xsts/authorize", "POST", map("Properties", map("SandboxId", "RETAIL", "UserTokens", Arrays.asList(xbox.get("Token"))), "RelyingParty", "rp://api.minecraftservices.com/", "TokenType", "JWT"), null);
        List<Object> xui=Json.arr(Json.obj(xsts.get("DisplayClaims")).get("xui"));
        if(xui.isEmpty())throw new IOException("Xbox identity claims missing");
        String hash=Json.text(Json.obj(xui.get(0)), "uhs");
        Map<String, Object> minecraft=request("https://api.minecraftservices.com/authentication/login_with_xbox", "POST", map("identityToken", "XBL3.0 x="+hash+";"+Json.text(xsts, "Token")), null);
        String token=Json.text(minecraft, "access_token");
        Map<String, Object> ownership=request("https://api.minecraftservices.com/entitlements/mcstore", "GET", null, token);
        if(Json.arr(ownership.get("items")).isEmpty())throw new IOException("This Microsoft account has no Minecraft Java entitlement");
        Map<String, Object> profile=request("https://api.minecraftservices.com/minecraft/profile", "GET", null, token);
        String id=Json.text(profile, "id"), name=Json.text(profile, "name");
        if(!id.matches("[0-9a-fA-F]{32}")||!name.matches("[a-zA-Z0-9_]{1,16}"))throw new IOException("Minecraft profile missing or invalid");
        Map<String, Object> account=map("uuid", id, "name", name, "accessToken", token, "refreshToken", oauth.get("refresh_token"), "expiresAt", System.currentTimeMillis()+((Number)minecraft.get("expires_in")).longValue()*1000);
        save("account.json", account);
    }
    void save(String name, Object data)throws IOException {
        FilesUtil.write(privateDir.resolve(name), Json.stringify(data));
        FilesUtil.restrict(privateDir.resolve(name));
    }
    Map<String, Object> account(boolean refresh)throws IOException {
        Path p=privateDir.resolve("account.json");
        if(!Files.isRegularFile(p))throw new IOException("No Minecraft account signed in. Sign in or explicitly choose accountMode=offline for your local single-player instance");
        Map<String, Object> a=Json.obj(Json.parse(FilesUtil.read(p)));
        if(refresh&&System.currentTimeMillis()+60000>((Number)a.get("expiresAt")).longValue()) {
            String token=Json.text(a, "refreshToken");
            if(token.isEmpty())throw new IOException("Microsoft sign-in expired");
            Map<String, Object> r=request("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", "POST", form(map("client_id", client(), "grant_type", "refresh_token", "refresh_token", token, "scope", "XboxLive.signin offline_access")), null);
            if(!r.containsKey("refresh_token"))r.put("refresh_token", token);
            exchange(r);
            a=Json.obj(Json.parse(FilesUtil.read(p)));
        }
        return a;
    }
    void signout()throws IOException {
        Files.deleteIfExists(privateDir.resolve("account.json"));
        Files.deleteIfExists(privateDir.resolve("auth-pending.json"));
        Files.deleteIfExists(app.root.resolve("profiles/launch-plan.json"));
        Files.deleteIfExists(app.root.resolve("profiles/launch.profile"));
        app.message="Signed out";
    }
}
