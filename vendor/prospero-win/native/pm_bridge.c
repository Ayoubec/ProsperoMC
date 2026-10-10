/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "pm_bridge.h"
#include "prospero_win.h"
#include <ctype.h>
#include <errno.h>
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void copy(char *dst, size_t cap, const char *src)
{
    size_t n = strlen(src);
    if (n >= cap) n = cap - 1;
    memcpy(dst, src, n); dst[n] = 0;
}
static int path(char *out, size_t cap, const char *root, const char *file)
{
    int n = snprintf(out, cap, "%s/%s", root, file);
    return n > 0 && (size_t)n < cap ? 0 : -1;
}
static int make_dir(const char *name)
{
    struct stat st;
    if (!stat(name, &st)) return S_ISDIR(st.st_mode) ? 0 : -1;
    return mkdir(name, 0700);
}
static int regular(const char *name)
{
    struct stat st;
    return !stat(name, &st) && S_ISREG(st.st_mode);
}
static int windows(char *out, size_t cap, const char *unix_path)
{
    size_t n = strlen(unix_path);
    if (n + 3 > cap || unix_path[0] != '/' || strchr(unix_path, '"')) return -1;
    out[0] = 'Z'; out[1] = ':';
    for (size_t i = 0; i <= n; i++) out[i+2] = unix_path[i] == '/' ? '\\' : unix_path[i];
    return 0;
}
static int copy_file(const char *source, const char *target)
{
    char tmp[768], buffer[16384];
    FILE *input = fopen(source, "rb"), *output;
    size_t n; int failed = 0;
    if (!input) return -1;
    if (snprintf(tmp, sizeof(tmp), "%s.tmp", target) >= (int)sizeof(tmp)) { fclose(input); return -1; }
    output = fopen(tmp, "wb");
    if (!output) { fclose(input); return -1; }
    while ((n = fread(buffer, 1, sizeof(buffer), input)))
        if (fwrite(buffer, 1, n, output) != n) { failed = 1; break; }
    failed |= ferror(input) || ferror(output);
    fclose(input); failed |= fclose(output) != 0;
    if (failed || rename(tmp, target)) { unlink(tmp); return -1; }
    chmod(target, 0600); return 0;
}
static int same_file_contents(const char *source, const char *target)
{
    unsigned char a[16384], b[16384];
    FILE *input = fopen(source, "rb"), *existing;
    int same = 0;
    if (!input) return 0;
    existing = fopen(target, "rb");
    if (existing) {
        for (;;) {
            size_t na = fread(a, 1, sizeof(a), input);
            size_t nb = fread(b, 1, sizeof(b), existing);
            if (na != nb || memcmp(a, b, na)) break;
            if (na < sizeof(a)) { same = !ferror(input) && !ferror(existing); break; }
        }
        fclose(existing);
    }
    fclose(input);
    return same;
}
int pm_bridge_initialize(const char *root, const char *app0)
{
    static const char *const dirs[] = {"profiles", "launcher", "runtimes", "instances", "imports"};
    char name[768], source[768];
    if (make_dir(root)) return -1;
    for (size_t i = 0; i < sizeof(dirs)/sizeof(dirs[0]); i++) {
        if (path(name, sizeof(name), root, dirs[i]) || make_dir(name)) return -1;
    }
    if (path(name, sizeof(name), root, "launcher/prosperomc-launcher.jar") ||
        path(source, sizeof(source), app0, "launcher/prosperomc-launcher.jar")) return -1;
    /* Refresh when the app is upgraded, independent of the selected game JVM. */
    /* A pre-staged matching JAR needs no rename over a loader-owned file. */
    if (same_file_contents(source, name)) return 0;
    /* Homebrew loaders may expose runtime modules without the app's extra
     * files. Deployment also installs this verified JAR in the data root. */
    FILE *packaged=fopen(source,"rb");
    if (!packaged) {
        FILE *staged=fopen(name,"rb");
        if (staged) {
            int a=fgetc(staged), b=fgetc(staged); fclose(staged);
            if (a=='P' && b=='K') return 0;
        }
        return -1;
    }
    fclose(packaged);
    return copy_file(source, name);
}

typedef void (*Property)(void *, const char *, const char *);
static int properties(const char *name, Property callback, void *context)
{
    char line[4096]; FILE *file = fopen(name, "rb");
    if (!file) return -1;
    while (fgets(line, sizeof(line), file)) {
        char *equal, *end;
        if (!strchr(line, '\n') && !feof(file)) { fclose(file); return -1; }
        end = line + strlen(line);
        while (end > line && (end[-1] == '\n' || end[-1] == '\r')) *--end = 0;
        if (!line[0] || line[0] == '#' || !(equal = strchr(line, '='))) continue;
        *equal++ = 0; callback(context, line, equal);
    }
    fclose(file); return 0;
}
static int integer(const char *s, int max)
{
    unsigned value = 0;
    for (; *s; s++) { if (*s < '0' || *s > '9' || value > (unsigned)max / 10) return 0; value = value*10 + (unsigned)(*s-'0'); }
    return value <= (unsigned)max ? (int)value : 0;
}
static const char *resolution_name(int height)
{
    switch(height) {
    case 720:return "1280x720"; case 1080:return "1920x1080";
    case 1440:return "2560x1440"; case 2160:return "3840x2160";
    default:return NULL;
    }
}
static void view_property(void *context, const char *key, const char *value)
{
    PmView *view = context;
    unsigned i; int chars = 0;
#define TEXT(k,f) if (!strcmp(key,k)) { copy(view->f, sizeof(view->f), value); return; }
    TEXT("status", status); TEXT("detail", detail); TEXT("javaPath", java_path);
    TEXT("settings.java8", java_path);
    TEXT("settings.accountMode", account_mode);
    TEXT("accountMode", account_mode);
    TEXT("settings.username", username);
    TEXT("username", username); TEXT("auth.username", account_username); TEXT("auth.url", auth_url); TEXT("auth.code", auth_code);
    TEXT("auth.verificationUri", auth_url); TEXT("auth.userCode", auth_code);
    TEXT("account.status", account_status);
    TEXT("auth.provider", auth_provider);
    TEXT("remote.projectId", remote_project);
#undef TEXT
    if (!strcmp(key,"instance.count")) { int n=integer(value,2147483647); view->instance_count=n>PM_MAX_INSTANCES?PM_MAX_INSTANCES:n; }
    else if (!strcmp(key,"version.count")) { int n=integer(value,2147483647); view->version_count=n>PM_MAX_VERSIONS?PM_MAX_VERSIONS:n; }
    else if (!strcmp(key,"mod.count")) { int n=integer(value,2147483647); view->mod_count=n>PM_MAX_MODS?PM_MAX_MODS:n; }
    else if (!strcmp(key,"java.count")) { int n=integer(value,2147483647); view->java_count=n>PM_MAX_JAVA?PM_MAX_JAVA:n; }
    else if (!strcmp(key,"remote.pack.count")) view->remote_count=integer(value,24);
    else if (!strcmp(key,"remote.version.count")) view->remote_version_count=integer(value,64);
    else if (!strcmp(key,"remote.offset")) view->remote_offset=integer(value,100000);
    else if (!strcmp(key,"remote.total")) view->remote_total=integer(value,2147483647);
    else if (!strcmp(key,"memoryMb") || !strcmp(key,"settings.memoryMb")) view->memory_mb = integer(value,32768);
    else if (!strcmp(key,"resolution") || !strcmp(key,"settings.resolution")) view->resolution_height=!strcmp(value,"3840x2160")?2160:!strcmp(value,"2560x1440")?1440:!strcmp(value,"1920x1080")?1080:720;
    else if (!strcmp(key,"auth.signedIn")) copy(view->account_status,sizeof(view->account_status),!strcmp(value,"true") ? "Signed in" : "Sign in to Minecraft");
    else if (!strcmp(key,"done")) view->progress_done = integer(value,2147483647);
    else if (!strcmp(key,"total")) view->progress_total = integer(value,2147483647);
    else if (sscanf(key,"instance.%u.%n", &i, &chars) == 1 && chars && i < PM_MAX_INSTANCES) {
        PmInstance *item = &view->instances[i]; const char *field = key + chars;
        if (!strcmp(field,"id")) copy(item->id,sizeof(item->id),value);
        else if (!strcmp(field,"name")) copy(item->name,sizeof(item->name),value);
        else if (!strcmp(field,"version")) copy(item->version,sizeof(item->version),value);
        else if (!strcmp(field,"loader")) copy(item->loader,sizeof(item->loader),value);
        else if (!strcmp(field,"installed")) item->installed = !strcmp(value,"true") || !strcmp(value,"1");
    } else if (sscanf(key,"version.%u.%n", &i, &chars) == 1 && chars && i < PM_MAX_VERSIONS) {
        PmVersion *item = &view->versions[i]; const char *field = key + chars;
        if (!strcmp(field,"id")) copy(item->id,sizeof(item->id),value);
        else if (!strcmp(field,"type")) copy(item->type,sizeof(item->type),value);
        else if (!strcmp(field,"java")) item->java = integer(value,99);
    } else if (sscanf(key,"mod.%u.%n", &i, &chars) == 1 && chars && i < PM_MAX_MODS) {
        PmMod *item = &view->mods[i]; const char *field = key + chars;
        if (!strcmp(field,"name")) copy(item->name,sizeof(item->name),value);
        else if (!strcmp(field,"enabled")) item->enabled = !strcmp(value,"true") || !strcmp(value,"1");
    } else if (sscanf(key,"remote.pack.%u.%n", &i, &chars) == 1 && chars && i < 24) {
        PmRemotePack *item=&view->remote_packs[i];const char *field=key+chars;
        if(!strcmp(field,"id"))copy(item->id,sizeof(item->id),value);
        else if(!strcmp(field,"name"))copy(item->name,sizeof(item->name),value);
        else if(!strcmp(field,"description"))copy(item->description,sizeof(item->description),value);
    } else if (sscanf(key,"remote.version.%u.%n", &i, &chars) == 1 && chars && i < 64) {
        PmPackRelease *item=&view->remote_versions[i];const char *field=key+chars;
        if(!strcmp(field,"id"))copy(item->id,sizeof(item->id),value);
        else if(!strcmp(field,"name"))copy(item->name,sizeof(item->name),value);
        else if(!strcmp(field,"game"))copy(item->game,sizeof(item->game),value);
        else if(!strcmp(field,"loader"))copy(item->loader,sizeof(item->loader),value);
    } else if (sscanf(key,"java.%u.%n", &i, &chars) == 1 && chars && i < PM_MAX_JAVA) {
        PmJavaRuntime *item=&view->java_runtimes[i]; const char *field=key+chars;
        if (!strcmp(field,"major")) item->major=integer(value,99);
        else if (!strcmp(field,"valid")) item->valid=!strcmp(value,"true") || !strcmp(value,"1");
        else if (!strcmp(field,"version")) copy(item->version,sizeof(item->version),value);
        else if (!strcmp(field,"path")) copy(item->path,sizeof(item->path),value);
        else if (!strcmp(field,"detail")) copy(item->detail,sizeof(item->detail),value);
    }
}
static int scan_packs(const char *root,PmView *view)
{
    char folder[768],full[1024]; DIR *dir; struct dirent *e;
    view->pack_count=0;
    if(path(folder,sizeof(folder),root,"imports") || !(dir=opendir(folder)))return 1;
    while((e=readdir(dir))) {
        size_t n=strlen(e->d_name);struct stat st;
        if(n<5 || n>=PM_TEXT || strchr(e->d_name,'\n') || strchr(e->d_name,'\r') ||
           (strcmp(e->d_name+n-4,".zip") && (n<7 || strcmp(e->d_name+n-7,".mrpack"))) ||
           view->pack_count>=PM_MAX_INSTANCES ||
           snprintf(full,sizeof(full),"%s/%s",folder,e->d_name)>=(int)sizeof(full) ||
           lstat(full,&st) || !S_ISREG(st.st_mode))continue;
        PmPack *pack=&view->packs[view->pack_count];
        if(windows(pack->source,sizeof(pack->source),full))continue;
        copy(pack->name,sizeof(pack->name),e->d_name);view->pack_count++;
    }
    closedir(dir);
    for(int i=1;i<view->pack_count;i++) {
        PmPack p=view->packs[i];int j=i;
        while(j>0 && strcmp(view->packs[j-1].name,p.name)>0){view->packs[j]=view->packs[j-1];j--;}
        view->packs[j]=p;
    }
    return 1;
}
int pm_bridge_view(const char *root, PmView *view)
{
    char name[768]; int status;
    memset(view, 0, sizeof(*view)); view->memory_mb = 2048;
    copy(view->account_mode,sizeof(view->account_mode),"offline");
    copy(view->status,sizeof(view->status),"Ready");
    copy(view->detail,sizeof(view->detail),"Choose a Minecraft version or import your local installation.");
    path(name,sizeof(name),root,"launcher-view.properties");
    status = properties(name,view_property,view);
    path(name,sizeof(name),root,"progress.properties");
    (void)properties(name,view_property,view);
    path(name,sizeof(name),root,"runtime-notice.properties");
    (void)properties(name,view_property,view);
    path(name,sizeof(name),root,"settings.properties");
    (void)properties(name,view_property,view);
    (void)scan_packs(root,view);
    return status;
}
static int value_safe(const char *value) { return !strchr(value,'\n') && !strchr(value,'\r'); }
static int write_property(FILE *file, const char *key, const char *value)
{
    if (!value_safe(value)) return -1;
    return value[0] && fprintf(file,"%s=%s\n",key,value) < 0 ? -1 : 0;
}
int pm_bridge_request(const char *root, const PmAction *action)
{
    PmAction resolved;
    if((!strcmp(action->command,"import-pack") || !strcmp(action->command,"create-install")) && !action->id[0]) {
        char candidate[768];struct stat st;unsigned n;
        resolved=*action;
        for(n=1;n<10000;n++) {
            snprintf(resolved.id,sizeof(resolved.id),"%s-%04u",!strcmp(action->command,"import-pack")?"pack":"instance",n);
            snprintf(candidate,sizeof(candidate),"%s/instances/%s",root,resolved.id);
            if(lstat(candidate,&st) && errno==ENOENT)break;
        }
        if(n==10000)return -1;
        action=&resolved;
    }
    static const char *const commands[] = {"catalog","create","create-install","install","install-java","detect-java","import","prepare-launch","mods","mod-toggle","mod-add","settings","auth-device","auth-poll","clone","export","import-pack","pack-search","pack-versions","pack-download"};
    char name[768], temporary[768]; FILE *file; int allowed = 0, failed = 0;
    for (size_t i=0; i<sizeof(commands)/sizeof(commands[0]); i++) allowed |= !strcmp(action->command,commands[i]);
    if (!allowed || action->java_major<0 || action->java_major>99 ||
        (action->resolution_height && !resolution_name(action->resolution_height)) ||
        path(name,sizeof(name),root,"request.properties") ||
        path(temporary,sizeof(temporary),root,"request.properties.tmp")) return -1;
    path(name,sizeof(name),root,"response.properties"); unlink(name);
    path(name,sizeof(name),root,"runtime-notice.properties"); unlink(name);
    path(name,sizeof(name),root,"pending-launch"); unlink(name);
    path(name,sizeof(name),root,"request.properties");
    if (!(file=fopen(temporary,"wb"))) return -1;
#define FIELD(k,f) failed |= write_property(file,k,action->f) != 0
    FIELD("command",command); FIELD("id",id); FIELD("version",version); FIELD("name",name);
    FIELD("loader",loader); FIELD("loaderVersion",loader_version); FIELD("source",source);
    FIELD("username",username); FIELD("mod",mod); FIELD("enabled",enabled); FIELD("java8",java_path);
    FIELD("accountMode",account_mode);
    FIELD("projectId",project_id);FIELD("packVersion",pack_version);FIELD("query",query);
#undef FIELD
    if (action->memory_mb) failed |= fprintf(file,"memoryMb=%d\n",action->memory_mb) < 0;
    if (!strcmp(action->command,"pack-search")) failed |= fprintf(file,"offset=%d\n",action->offset)<0;
    if(action->resolution_height)failed |= fprintf(file,"resolution=%s\n",resolution_name(action->resolution_height))<0;
    if (action->java_major) failed |= fprintf(file,"major=%d\n",action->java_major) < 0;
    if (!strcmp(action->command,"install-java")) failed |= write_property(file,"repair","true") != 0;
    failed |= fclose(file) != 0;
    if (failed) { unlink(temporary); return -1; }
    if (!strcmp(action->command,"prepare-launch")) {
        char prepared[768];
        path(prepared,sizeof(prepared),root,"profiles/launch.profile"); unlink(prepared);
        path(name,sizeof(name),root,"pending-launch");
        if (!(file=fopen(name,"wb"))) { unlink(temporary); return -1; }
        failed = fputs("prepare-launch\n",file) < 0; failed |= fclose(file) != 0;
        if (failed) { unlink(temporary); return -1; }
        chmod(name,0600);
    }
    path(name,sizeof(name),root,"request.properties");
    if (rename(temporary,name)) { unlink(temporary); return -1; }
    chmod(name,0600);
    return 0;
}
int pm_bridge_backend(const char *root, PwGameProfile *profile)
{
    char exe[768], jar[768], request[768], winroot[768], winjar[768], winrequest[768];
    memset(profile,0,sizeof(*profile)); pw_game_input_init(&profile->input);
    if (path(exe,sizeof(exe),root,"runtimes/java8/bin/java.exe") || !regular(exe) ||
        path(jar,sizeof(jar),root,"launcher/prosperomc-launcher.jar") || !regular(jar) ||
        path(request,sizeof(request),root,"request.properties") ||
        windows(profile->app.executable,sizeof(profile->app.executable),exe) ||
        windows(winroot,sizeof(winroot),root) || windows(winjar,sizeof(winjar),jar) ||
        windows(winrequest,sizeof(winrequest),request)) return -1;
    copy(profile->app.id,sizeof(profile->app.id),"launcher");
    copy(profile->app.name,sizeof(profile->app.name),"ProsperoMC");
    copy(profile->app.prefix,sizeof(profile->app.prefix),"minecraft");
    copy(profile->app.runtime,sizeof(profile->app.runtime),"wine-wow64");
    copy(profile->app.working_directory,sizeof(profile->app.working_directory),winroot);
    profile->app.architecture=PW_APP_ARCH_PE64; profile->app.graphics=PW_APP_GRAPHICS_GDI;
    profile->runtime.thread_scheduling=1;
    return snprintf(profile->app.arguments,sizeof(profile->app.arguments),
      "-Xms32M -Xmx256M -XX:-UseCompressedOops -XX:-UseCompressedClassPointers -XX:ReservedCodeCacheSize=64M -Djava.awt.headless=true -jar \"%s\" --root \"%s\" --serve",winjar,winroot) < (int)sizeof(profile->app.arguments) ? 0 : -1;
}
static int allowed_java(const char *root, const char *exe)
{
    char base[768]; const char *suffix; size_t n;
    if (windows(base,sizeof(base),root)) return 0;
    n=strlen(base);
    if (strncmp(exe,base,n) || strncmp(exe+n,"\\runtimes\\java",14)) return 0;
    suffix=exe+n+14;
    if (!isdigit((unsigned char)*suffix)) return 0;
    while (isdigit((unsigned char)*suffix)) suffix++;
    return !strcmp(suffix,"\\bin\\java.exe");
}
int pm_bridge_game(const char *root, PwGameProfile *profile)
{
    char name[768]; static uint8_t content[PW_APP_PROFILE_MAX_BYTES]; FILE *file; size_t n;
    if (path(name,sizeof(name),root,"profiles/launch.profile") || !(file=fopen(name,"rb"))) return -1;
    n=fread(content,1,sizeof(content),file);
    if (ferror(file) || fgetc(file)!=EOF) { fclose(file); return -1; } fclose(file);
    if (pw_game_profile_parse(content,n,profile)!=PW_OK || strcmp(profile->app.id,"minecraft") ||
        !allowed_java(root,profile->app.executable) || profile->app.architecture!=PW_APP_ARCH_PE64 ||
        (profile->app.graphics!=PW_APP_GRAPHICS_OPENGL && profile->app.graphics!=PW_APP_GRAPHICS_ZINK) ||
        strcmp(profile->app.prefix,"minecraft")) return -1;
    profile->runtime.thread_scheduling=1;
    return 0;
}
typedef struct Response { int ok, command; } Response;
static void response_property(void *context, const char *key, const char *value)
{
    Response *response=context;
    if (!strcmp(key,"ok")) response->ok=!strcmp(value,"true");
    else if (!strcmp(key,"command")) response->command=!strcmp(value,"prepare-launch");
}
int pm_bridge_consume_launch(const char *root)
{
    char name[768]; Response response={0,0};
    path(name,sizeof(name),root,"pending-launch");
    if (!regular(name)) return 0;
    unlink(name); /* Consume exactly once, including failed requests. */
    path(name,sizeof(name),root,"response.properties");
    return !properties(name,response_property,&response) && response.ok && response.command;
}
int pm_bridge_frontend_save(const char *root, const PmFrontend *frontend)
{
    char name[768],temporary[768]; FILE *file; int failed;
    if (path(name,sizeof(name),root,"frontend-state.properties") ||
        path(temporary,sizeof(temporary),root,"frontend-state.properties.tmp") || !(file=fopen(temporary,"wb"))) return -1;
    failed=fprintf(file,"screen=%d\ninstance=%d\nversion=%d\nmod=%d\njava=%d\nfilter=%d\nfocus=%d\nloader=%d\n",(int)frontend->screen,
       frontend->selected_instance,frontend->selected_version,frontend->selected_mod,frontend->selected_java,frontend->version_filter,frontend->focus,frontend->loader_index)<0;
    failed |= fclose(file)!=0;
    if (failed || rename(temporary,name)) { unlink(temporary); return -1; }
    return 0;
}
static void frontend_property(void *context, const char *key, const char *value)
{
    PmFrontend *frontend=context;
    if (!strcmp(key,"screen")) frontend->screen=(PmScreen)integer(value,PM_SCREEN_COUNT-1);
    else if (!strcmp(key,"instance")) frontend->selected_instance=integer(value,PM_MAX_INSTANCES-1);
    else if (!strcmp(key,"version")) frontend->selected_version=integer(value,PM_MAX_VERSIONS-1);
    else if (!strcmp(key,"mod")) frontend->selected_mod=integer(value,PM_MAX_MODS-1);
    else if (!strcmp(key,"java")) frontend->selected_java=integer(value,PM_MAX_JAVA-1);
    else if (!strcmp(key,"filter")) frontend->version_filter=integer(value,2);
    else if (!strcmp(key,"focus")) frontend->focus=integer(value,PM_MAX_JAVA+4);
    else if (!strcmp(key,"loader")) frontend->loader_index=integer(value,3);
}
void pm_bridge_frontend_load(const char *root, PmFrontend *frontend)
{
    char name[768]; if (!path(name,sizeof(name),root,"frontend-state.properties")) (void)properties(name,frontend_property,frontend);
}
void pm_bridge_notice(const char *root, const char *message)
{
    char name[768],temporary[768]; FILE *file; int failed;
    if (path(name,sizeof(name),root,"runtime-notice.properties") ||
        path(temporary,sizeof(temporary),root,"runtime-notice.properties.tmp") || !(file=fopen(temporary,"wb"))) return;
    failed=write_property(file,"status","error") || write_property(file,"detail",message);
    failed |= fclose(file)!=0;
    if (failed || rename(temporary,name)) unlink(temporary);
}
int pm_bridge_auto_catalog(const char *root, const PmView *view)
{
    char name[768]; FILE *file; int failed;
    if (view->version_count>0 || path(name,sizeof(name),root,"catalog-auto.attempted") || regular(name)) return 0;
    if (!(file=fopen(name,"wb"))) return 0;
    failed=fputs("catalog\n",file)<0; failed |= fclose(file)!=0;
    if (failed) { unlink(name); return 0; }
    return 1;
}
int pm_bridge_response_ready(const char *root)
{
    char name[768];
    return !path(name,sizeof(name),root,"response.properties") && regular(name);
}
static int component_safe(const char *name)
{
    if (!name[0] || !strcmp(name,".") || !strcmp(name,"..")) return 0;
    for (const unsigned char *p=(const unsigned char *)name; *p; p++)
        if (!(isalnum(*p) || *p=='_' || *p=='-' || *p=='.' || *p=='+')) return 0;
    return 1;
}
static int local_settings(const char *root, const PmAction *action, PmView *view)
{
    char name[768], temporary[768], line[4096]; FILE *input, *output; int failed=0;
    if ((action->memory_mb && (action->memory_mb<512 || action->memory_mb>8192)) ||
        (action->resolution_height && !resolution_name(action->resolution_height)) ||
        (action->account_mode[0] && strcmp(action->account_mode,"offline") && strcmp(action->account_mode,"microsoft")) ||
        !value_safe(action->username) || path(name,sizeof(name),root,"settings.properties") ||
        path(temporary,sizeof(temporary),root,"settings.properties.tmp")) { errno=EINVAL; return -1; }
    input=fopen(name,"rb");
    if (!input && errno!=ENOENT) return -1;
    output=fopen(temporary,"wb");
    if (!output) { if (input) fclose(input); return -1; }
    if (input) {
        while (fgets(line,sizeof(line),input)) {
            if (!strchr(line,'\n') && !feof(input)) { failed=1; break; }
            if ((action->memory_mb && !strncmp(line,"memoryMb=",9)) ||
                (action->resolution_height && !strncmp(line,"resolution=",11)) ||
                (action->account_mode[0] && !strncmp(line,"accountMode=",12)) ||
                (action->username[0] && !strncmp(line,"username=",9))) continue;
            if (fputs(line,output)<0) { failed=1; break; }
            size_t n=strlen(line);
            if (n && line[n-1]!='\n' && fputc('\n',output)==EOF) failed=1;
        }
        failed |= ferror(input)!=0; fclose(input);
    }
    if (action->memory_mb) failed |= fprintf(output,"memoryMb=%d\n",action->memory_mb)<0;
    if(action->resolution_height)failed |= fprintf(output,"resolution=%s\n",resolution_name(action->resolution_height))<0;
    failed |= write_property(output,"accountMode",action->account_mode)!=0;
    failed |= write_property(output,"username",action->username)!=0;
    failed |= fclose(output)!=0;
    if (failed || rename(temporary,name)) { int saved=errno; unlink(temporary); errno=saved; return -1; }
    (void)properties(name,view_property,view);
    copy(view->status,sizeof(view->status),"ready");
    copy(view->detail,sizeof(view->detail),"Launcher settings saved");
    return 1;
}
static int local_mods(const char *root, const PmAction *action, PmView *view)
{
    char directory[768], source[1024], target[1024]; DIR *mods; struct dirent *entry;
    if (!component_safe(action->id) || snprintf(directory,sizeof(directory),"%s/instances/%s/.minecraft/mods",root,action->id)>=(int)sizeof(directory)) { errno=EINVAL; return -1; }
    if (!strcmp(action->command,"mod-toggle")) {
        size_t n=strlen(action->mod); struct stat st;
        int disabled=n>13 && !strcmp(action->mod+n-13,".jar.disabled");
        int enabled=n>4 && !strcmp(action->mod+n-4,".jar");
        if (!component_safe(action->mod) || (!disabled && !enabled) ||
            (strcmp(action->enabled,"true") && strcmp(action->enabled,"false")) ||
            snprintf(source,sizeof(source),"%s/%s",directory,action->mod)>=(int)sizeof(source) ||
            lstat(source,&st) || !S_ISREG(st.st_mode)) { errno=EINVAL; return -1; }
        if (!strcmp(action->enabled,"true")) snprintf(target,sizeof(target),"%s/%.*s",directory,(int)(disabled?n-9:n),action->mod);
        else snprintf(target,sizeof(target),"%s/%s%s",directory,action->mod,disabled?"":".disabled");
        if (strcmp(source,target)) {
            if (!lstat(target,&st)) { errno=EEXIST; return -1; }
            if (errno!=ENOENT || rename(source,target)) return -1;
        }
    }
    view->mod_count=0;
    mods=opendir(directory);
    if (!mods && errno!=ENOENT) return -1;
    if (mods) {
        while ((entry=readdir(mods))) {
            size_t n=strlen(entry->d_name); struct stat st;
            int disabled=n>13 && !strcmp(entry->d_name+n-13,".jar.disabled");
            if ((!disabled && !(n>4 && !strcmp(entry->d_name+n-4,".jar"))) || !component_safe(entry->d_name) ||
                n>=sizeof(view->mods[0].name) || view->mod_count>=PM_MAX_MODS) continue;
            if (snprintf(source,sizeof(source),"%s/%s",directory,entry->d_name)>=(int)sizeof(source) ||
                lstat(source,&st) || !S_ISREG(st.st_mode)) continue;
            PmMod *item=&view->mods[view->mod_count++];
            copy(item->name,sizeof(item->name),entry->d_name); item->enabled=!disabled;
        }
        closedir(mods);
    }
    for (int i=1; i<view->mod_count; i++) {
        PmMod item=view->mods[i]; int j=i;
        while (j>0 && strcmp(view->mods[j-1].name,item.name)>0) { view->mods[j]=view->mods[j-1]; j--; }
        view->mods[j]=item;
    }
    copy(view->status,sizeof(view->status),"ready");
    copy(view->detail,sizeof(view->detail),"Mods loaded");
    return 1;
}
int pm_bridge_local(const char *root, const PmAction *action, PmView *view)
{
    if(!strcmp(action->command,"scan-packs")) {
        int result=scan_packs(root,view);
        copy(view->status,sizeof(view->status),"ready");
        snprintf(view->detail,sizeof(view->detail),"Found %d modpacks in /data/ProsperoMC/imports",view->pack_count);
        return result;
    }
    if (!strcmp(action->command,"settings")) return local_settings(root,action,view);
    if (!strcmp(action->command,"mods") || !strcmp(action->command,"mod-toggle")) return local_mods(root,action,view);
    return 0;
}
int pm_bridge_prepare_prefix(const char *root)
{
    static const char *const folders[]={"prefixes","prefixes/minecraft","prefixes/minecraft/drive_c","prefixes/minecraft/dosdevices"};
    static const char table[]="c:\t../drive_c\nz:\t/\n";
    char name[768], temporary[768], present[128], normalized[128];
    for (size_t i=0;i<sizeof(folders)/sizeof(folders[0]);i++)
        if (path(name,sizeof(name),root,folders[i]) || make_dir(name)) return -1;
    if (path(name,sizeof(name),root,"prefixes/minecraft/dosdevices/.pw-symlinks") ||
        path(temporary,sizeof(temporary),root,"prefixes/minecraft/dosdevices/.pw-symlinks.tmp")) return -1;
    FILE *input=fopen(name,"rb");
    if (input) {
        size_t n=fread(present,1,sizeof(present),input), kept=0;
        int failed=ferror(input); fclose(input);
        if (failed || n>=sizeof(present)) {errno=EINVAL;return -1;}
        if (n==sizeof(table)-1 && !memcmp(present,table,n)) return 0;
        for (size_t i=0;i<n;i++) if (present[i]!='\r') normalized[kept++]=present[i];
        if (kept!=sizeof(table)-1 || memcmp(normalized,table,kept)) {errno=EINVAL;return -1;}
    } else if (errno!=ENOENT) return -1;
    FILE *output=fopen(temporary,"wb"); if (!output) return -1;
    int failed=fwrite(table,1,sizeof(table)-1,output)!=sizeof(table)-1;
    failed |= fclose(output)!=0;
    if (failed || rename(temporary,name)) {unlink(temporary);return -1;}
    return 0;
}
