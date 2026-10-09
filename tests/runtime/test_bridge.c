/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "pm_bridge.h"
#include "pw_wine_launch.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static void write_file(const char *name,const char *text)
{ FILE *f=fopen(name,"wb"); assert(f); assert(fputs(text,f)>=0); assert(!fclose(f)); }
int main(void)
{
    char root[]="/tmp/prosperomc-bridge-test.XXXXXX", name[1024], content[65536];
    static PmView view; static PwGameProfile game;
    PmAction action={0}; PwWineLaunch launch; PmFrontend frontend={0},loaded={0};
    PwWineApp app={"minecraft","Minecraft","Java","Z:\\data\\prosperomc\\runtimes\\java8\\bin\\java.exe"};
    assert(mkdtemp(root));
    snprintf(name,sizeof(name),"%s/launcher-view.properties",root);
    write_file(name,"instance.count=99\ninstance.0.id=owned\ninstance.0.installed=true\nversion.count=2050\nversion.2047.id=1.12.2\nmod.count=129\njava.count=20\njava.0.major=8\njava.0.valid=true\njava.0.version=1.8.0_504\njava.0.path=Z:\\data\\prosperomc\\runtimes\\java8\\bin\\java.exe\njava.1.major=21\njava.1.valid=false\njava.1.detail=Download required\njava.16.major=99\nsettings.memoryMb=4096\nauth.userCode=ABCD-EFGH\nauth.verificationUri=https://microsoft.com/link\n");
    assert(!pm_bridge_view(root,&view));
    assert(view.instance_count==PM_MAX_INSTANCES && view.version_count==PM_MAX_VERSIONS && view.mod_count==PM_MAX_MODS);
    assert(view.instances[0].installed && !strcmp(view.versions[2047].id,"1.12.2") && view.memory_mb==4096);
    assert(!strcmp(view.auth_code,"ABCD-EFGH"));
    assert(view.java_count==PM_MAX_JAVA && view.java_runtimes[0].valid && view.java_runtimes[0].major==8);
    assert(!strcmp(view.java_runtimes[0].version,"1.8.0_504") && view.java_runtimes[1].major==21 && !view.java_runtimes[1].valid);
    assert(!pm_bridge_auto_catalog(root,&view));
    view.version_count=0; assert(pm_bridge_auto_catalog(root,&view)); assert(!pm_bridge_auto_catalog(root,&view));
    strcpy(action.command,"install-java"); action.java_major=21; assert(!pm_bridge_request(root,&action));
    snprintf(name,sizeof(name),"%s/request.properties",root);
    FILE *request=fopen(name,"rb"); assert(request); size_t request_bytes=fread(content,1,sizeof(content)-1,request); fclose(request); content[request_bytes]=0;
    assert(strstr(content,"command=install-java\n") && strstr(content,"major=21\n") && strstr(content,"repair=true\n"));
    action.java_major=-1; assert(pm_bridge_request(root,&action)); action.java_major=0;
    strcpy(action.command,"detect-java"); assert(!pm_bridge_request(root,&action));
    strcpy(action.command,"create-install"); strcpy(action.version,"1.12.2"); assert(!pm_bridge_request(root,&action));
    strcpy(action.command,"catalog"); assert(!pm_bridge_request(root,&action));
    strcpy(action.name,"bad\ncommand=export"); assert(pm_bridge_request(root,&action));
    action.name[0]=0; strcpy(action.command,"run-exe"); assert(pm_bridge_request(root,&action));
    snprintf(name,sizeof(name),"%s/profiles",root); assert(!mkdir(name,0700));
    strcpy(action.command,"prepare-launch"); strcpy(action.id,"owned"); assert(!pm_bridge_request(root,&action));
    snprintf(name,sizeof(name),"%s/response.properties",root); write_file(name,"ok=false\ncommand=prepare-launch\n");
    assert(!pm_bridge_consume_launch(root)); assert(!pm_bridge_consume_launch(root));
    assert(!pm_bridge_request(root,&action)); write_file(name,"ok=true\ncommand=prepare-launch\n");
    assert(pm_bridge_consume_launch(root)); assert(!pm_bridge_consume_launch(root));
    char *raw[]={"path=Z:\\random.exe"}; assert(!pw_wine_launch_parse(1,raw,&app,1,&launch)); assert(launch.refused);
    char *override[]={"profile=minecraft","path=Z:\\random.exe"};
    assert(!pw_wine_launch_parse(2,override,&app,1,&launch)); assert(launch.refused);
    char *valid[]={"profile=minecraft"}; assert(!pw_wine_launch_parse(1,valid,&app,1,&launch)); assert(launch.mode==PW_WINE_LAUNCH_GAME);
    char long_arguments[16384],split_storage[16384]; const char *words[PW_WINE_LAUNCH_WORDS];
    size_t used=0;
    for(unsigned i=0;i<100;i++) used+=(size_t)snprintf(long_arguments+used,sizeof(long_arguments)-used,"-Doption%u=abcdefghijklmnopqrstuvwxyz ",i);
    assert(pw_wine_launch_split(long_arguments,split_storage,sizeof(split_storage),words,PW_WINE_LAUNCH_WORDS)==100);
    snprintf(content,sizeof(content),"[application]\nid=minecraft\nname=Minecraft\nexecutable=Z:%s\\runtimes\\java8\\bin\\java.exe\nworking_directory=Z:%s\narguments=-Xmx2048M -cp a;b;c org.prosperomc.Main\nprefix=minecraft\nruntime=wine-wow64\narchitecture=pe64\ngraphics=opengl\n",root,root);
    for(char *p=content;*p;p++) if(*p=='/') *p='\\';
    snprintf(name,sizeof(name),"%s/profiles/launch.profile",root); write_file(name,content);
    assert(!pm_bridge_game(root,&game));
    char *id=strstr(content,"id=minecraft"); memcpy(id,"id=othergame",12); write_file(name,content); assert(pm_bridge_game(root,&game));
    frontend.screen=PM_MODS; frontend.selected_instance=3; frontend.selected_java=5; frontend.version_filter=2;
    assert(!pm_bridge_frontend_save(root,&frontend)); pm_bridge_frontend_load(root,&loaded);
    assert(loaded.screen==PM_MODS && loaded.selected_instance==3 && loaded.selected_java==5 && loaded.version_filter==2);
    char initialized[]="/tmp/prosperomc-init-test.XXXXXX", package[]="/tmp/prosperomc-package-test.XXXXXX";
    assert(mkdtemp(initialized) && mkdtemp(package));
    snprintf(name,sizeof(name),"%s/launcher",package); assert(!mkdir(name,0700));
    snprintf(name,sizeof(name),"%s/launcher/prosperomc-launcher.jar",package); write_file(name,"old jar");
    assert(!pm_bridge_initialize(initialized,package));
    char destination[1024]; struct stat before, after;
    snprintf(destination,sizeof(destination),"%s/launcher/prosperomc-launcher.jar",initialized);
    assert(!stat(destination,&before));
    assert(!pm_bridge_initialize(initialized,package)); assert(!stat(destination,&after));
    assert(before.st_ino==after.st_ino); /* Equal bytes must not replace the file. */
    write_file(name,"new jar"); assert(!pm_bridge_initialize(initialized,package));
    FILE *updated=fopen(destination,"rb"); assert(updated);
    size_t updated_bytes=fread(content,1,sizeof(content)-1,updated); fclose(updated); content[updated_bytes]=0;
    assert(!strcmp(content,"new jar"));
    assert(pm_bridge_initialize(initialized,"/nonexistent/prosperomc-package"));
    write_file(destination,"PK staged jar");
    assert(!pm_bridge_initialize(initialized,"/nonexistent/prosperomc-package"));
    snprintf(name,sizeof(name),"%s/settings.properties",root);
    write_file(name,"java8=Z:\\data\\prosperomc\\runtimes\\java8\\bin\\java.exe\nmicrosoftClientId=keep-this\nmemoryMb=2048\naccountMode=microsoft\n");
    memset(&action,0,sizeof(action)); strcpy(action.command,"settings"); action.memory_mb=4096; action.resolution_height=1080;
    assert(pm_bridge_local(root,&action,&view)==1 && view.memory_mb==4096 && view.resolution_height==1080);
    action.resolution_height=900; assert(pm_bridge_local(root,&action,&view)==-1); assert(pm_bridge_request(root,&action));
    action.resolution_height=0;
    action.memory_mb=0; strcpy(action.account_mode,"offline"); strcpy(action.username,"Player");
    assert(pm_bridge_local(root,&action,&view)==1 && !strcmp(view.account_mode,"offline"));
    assert(!pm_bridge_view(root,&view) && view.memory_mb==4096 && !strcmp(view.account_mode,"offline"));
    FILE *settings=fopen(name,"rb"); assert(settings);
    size_t setting_bytes=fread(content,1,sizeof(content)-1,settings); fclose(settings);content[setting_bytes]=0;
    assert(strstr(content,"microsoftClientId=keep-this\n") && strstr(content,"java8=Z:"));
    assert(strstr(content,"resolution=1920x1080\n"));
    for(int r=0;r<4;r++) {
        const int heights[]={720,1080,1440,2160};
        action.resolution_height=heights[r];
        assert(pm_bridge_local(root,&action,&view)==1 && view.resolution_height==heights[r]);
        assert(!pm_bridge_view(root,&view) && view.resolution_height==heights[r] && view.memory_mb==4096);
        assert(!pm_bridge_request(root,&action));
    }
    action.resolution_height=0;
    action.memory_mb=1; assert(pm_bridge_local(root,&action,&view)==-1); action.memory_mb=0;
    strcpy(action.account_mode,"invalid"); assert(pm_bridge_local(root,&action,&view)==-1);
    snprintf(name,sizeof(name),"%s/instances",root); assert(!mkdir(name,0700));
    snprintf(name,sizeof(name),"%s/instances/owned",root); assert(!mkdir(name,0700));
    snprintf(name,sizeof(name),"%s/instances/owned/.minecraft",root); assert(!mkdir(name,0700));
    snprintf(name,sizeof(name),"%s/instances/owned/.minecraft/mods",root); assert(!mkdir(name,0700));
    snprintf(name,sizeof(name),"%s/instances/owned/.minecraft/mods/example.jar",root); write_file(name,"mod");
    memset(&action,0,sizeof(action)); strcpy(action.command,"mods"); strcpy(action.id,"owned");
    assert(pm_bridge_local(root,&action,&view)==1 && view.mod_count==1 && view.mods[0].enabled);
    strcpy(action.command,"mod-toggle"); strcpy(action.mod,"example.jar"); strcpy(action.enabled,"false");
    assert(pm_bridge_local(root,&action,&view)==1 && !view.mods[0].enabled);
    strcpy(action.mod,"example.jar.disabled"); strcpy(action.enabled,"true");
    assert(pm_bridge_local(root,&action,&view)==1 && view.mods[0].enabled);
    strcpy(action.mod,"../example.jar"); assert(pm_bridge_local(root,&action,&view)==-1);
    strcpy(action.command,"catalog"); assert(pm_bridge_local(root,&action,&view)==0);
    snprintf(name,sizeof(name),"%s/imports",root); assert(!mkdir(name,0700));
    snprintf(name,sizeof(name),"%s/imports/My pack.mrpack",root);write_file(name,"pack");
    snprintf(name,sizeof(name),"%s/imports/ignored.jar",root);write_file(name,"jar");
    snprintf(name,sizeof(name),"%s/imports/not-a-file.zip",root);assert(!mkdir(name,0700));
    snprintf(name,sizeof(name),"%s/imports/alias.zip",root);assert(!symlink("/etc/passwd",name));
    memset(&action,0,sizeof(action));strcpy(action.command,"scan-packs");
    assert(pm_bridge_local(root,&action,&view)==1 && view.pack_count==1);
    assert(!strcmp(view.packs[0].name,"My pack.mrpack") && strstr(view.packs[0].source,"Z:"));
    strcpy(action.command,"import-pack");strcpy(action.source,view.packs[0].source);
    assert(!pm_bridge_request(root,&action));
    snprintf(name,sizeof(name),"%s/request.properties",root);
    FILE *pack_request=fopen(name,"rb");assert(pack_request);
    size_t pack_bytes=fread(content,1,sizeof(content)-1,pack_request);fclose(pack_request);content[pack_bytes]=0;
    assert(strstr(content,"id=pack-0001\n") && strstr(content,"My pack.mrpack\n"));
    assert(!pm_bridge_prepare_prefix(root)); assert(!pm_bridge_prepare_prefix(root));
    snprintf(name,sizeof(name),"%s/prefixes/minecraft/dosdevices/.pw-symlinks",root);
    write_file(name,"c:\t../drive_c\r\nz:\t/\r\n");
    assert(!pm_bridge_prepare_prefix(root));
    FILE *links=fopen(name,"rb"); assert(links);
    size_t link_bytes=fread(content,1,sizeof(content)-1,links);fclose(links);content[link_bytes]=0;
    assert(!strcmp(content,"c:\t../drive_c\nz:\t/\n") && !strchr(content,'\r'));
    write_file(name,"c:\t../drive_c\nz:\t/incorrect\n");
    assert(pm_bridge_prepare_prefix(root));
    puts("Minecraft runtime bridge tests passed");
    return 0;
}
