#include "pm_frontend.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static PmView view;
static PmAction a;
static PmFrontend f;
static int press(PmKey k) {return pm_frontend_update(&f,&view,k,&a);}

int main(void) {
    int screen,j;unsigned char *bytes;
    PwPresentTarget target;
    pm_frontend_init(&f);
    /* Empty lists never dispatch an invalid index or a missing id. */
    assert(!press(PM_KEY_CONFIRM));assert(f.screen==PM_VERSIONS);
    assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"catalog"));
    f.screen=PM_LIBRARY;assert(!press(PM_KEY_CONFIRM));assert(f.screen==PM_VERSIONS);
    f.screen=PM_MODS;assert(!press(PM_KEY_CONFIRM));assert(f.notice[0]);
    /* A version selection dispatches the complete create/install operation. */
    view.version_count=1;strcpy(view.versions[0].id,"1.12.2");view.versions[0].java=8;
    f.screen=PM_VERSIONS;f.focus=0;
    assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"create-install"));assert(!strcmp(a.version,"1.12.2"));
    f.loader_index=3;assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.loader,"forge"));
    strcpy(view.versions[0].id,"1.21.1");assert(!press(PM_KEY_CONFIRM));assert(f.notice[0]);strcpy(view.versions[0].id,"1.12.2");f.loader_index=0;
    view.version_count=3;strcpy(view.versions[0].type,"snapshot");strcpy(view.versions[1].type,"release");strcpy(view.versions[2].type,"snapshot");
    press(PM_KEY_NONE);assert(f.selected_version==1);assert(!press(PM_KEY_DOWN));assert(f.selected_version==1);
    assert(!press(PM_KEY_SECONDARY));assert(f.version_filter==2);assert(f.selected_version==0);
    assert(!press(PM_KEY_DOWN));assert(f.selected_version==2);
    assert(!press(PM_KEY_SECONDARY));assert(f.version_filter==0);
    view.instance_count=2;strcpy(view.instances[0].id,"legacy");strcpy(view.instances[1].id,"new");
    view.instances[1].installed=1;
    f.screen=PM_LIBRARY;assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"install"));assert(!strcmp(a.id,"legacy"));
    assert(!press(PM_KEY_DOWN));assert(f.selected_instance==1);
    assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"prepare-launch"));assert(!strcmp(a.id,"new"));
    assert(!press(PM_KEY_RIGHT));assert(!press(PM_KEY_DOWN));
    assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"mods"));assert(f.screen==PM_MODS);
    view.mod_count=1;strcpy(view.mods[0].name,"example.jar");
    assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"mod-toggle"));assert(!strcmp(a.mod,"example.jar"));assert(!strcmp(a.enabled,"true"));
    view.mods[0].enabled=1;assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.enabled,"false"));
    /* Backend work cannot be accidentally launched twice; tabs still work. */
    view.busy=1;assert(!press(PM_KEY_CONFIRM));assert(!a.command[0]);
    assert(!press(PM_KEY_NEXT_TAB));assert(f.screen==PM_SETTINGS);view.busy=0;
    f.memory_mb=512;assert(!press(PM_KEY_LEFT));assert(f.memory_mb==512);
    f.memory_mb=8192;assert(!press(PM_KEY_RIGHT));assert(f.memory_mb==8192);
    assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"settings"));assert(a.memory_mb==8192);
    assert(!press(PM_KEY_DOWN));assert(f.focus==1);
    for(j=0;j<4;j++) {
        const int majors[]={8,17,21,25};
        assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"install-java"));assert(a.java_major==majors[j]);
        if(j<3)assert(!press(PM_KEY_RIGHT));
    }
    assert(!press(PM_KEY_RIGHT));assert(f.focus==4);
    assert(!press(PM_KEY_DOWN));assert(f.focus==5);
    assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"detect-java"));assert(!a.java_major);
    assert(!press(PM_KEY_RIGHT));assert(f.focus==6);
    assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"settings"));assert(a.memory_mb==8192);
    assert(press(PM_KEY_REFRESH));assert(!strcmp(a.command,"detect-java"));
    view.java_count=2;view.java_runtimes[0].major=8;view.java_runtimes[0].valid=1;view.java_runtimes[1].major=16;
    assert(!press(PM_KEY_SECONDARY));assert(f.selected_java==1);
    assert(!press(PM_KEY_SECONDARY));assert(f.selected_java==0);
    view.busy=1;f.focus=2;assert(!press(PM_KEY_CONFIRM));assert(!a.command[0]);view.busy=0;
    f.screen=PM_ACCOUNTS;f.focus=0;
    assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"settings"));assert(!strcmp(a.account_mode,"offline"));assert(!strcmp(a.username,"Player"));
    strcpy(view.account_mode,"offline");assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.account_mode,"microsoft"));
    f.focus=1;assert(!press(PM_KEY_CONFIRM));assert(f.notice[0]);
    strcpy(view.account_mode,"microsoft");assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"auth-device"));
    f.focus=2;assert(press(PM_KEY_CONFIRM));assert(!strcmp(a.command,"auth-poll"));
    /* Out-of-range indices/counts are normalized before any array read. */
    view.instance_count=PM_MAX_INSTANCES+999;view.version_count=PM_MAX_VERSIONS+999;view.mod_count=PM_MAX_MODS+999;view.java_count=PM_MAX_JAVA+999;
    for(screen=0;screen<PM_SCREEN_COUNT;screen++) {
        f.screen=(PmScreen)screen;f.focus=99;f.selected_instance=99999;f.selected_version=99999;f.selected_mod=99999;f.selected_java=99999;
        for(j=0;j<100;j++) press((PmKey)(PM_KEY_UP+j%4));
        assert(f.selected_instance>=0&&f.selected_instance<PM_MAX_INSTANCES);
        assert(f.selected_version>=0&&f.selected_version<PM_MAX_VERSIONS);
        assert(f.selected_mod>=0&&f.selected_mod<PM_MAX_MODS);
        assert(f.selected_java>=0&&f.selected_java<PM_MAX_JAVA);
        assert(f.focus>=0&&f.focus<=(screen==PM_SETTINGS?6:4));
    }
    /* Valid 720p buffer is guarded; undersized buffers are refused. */
    bytes=(unsigned char*)malloc(1280*720*4+32);assert(bytes);
    memset(bytes,0x5a,1280*720*4+32);
    target.pixels=bytes+16;target.width=1280;target.height=720;target.stride=1280*4;target.bytes=1280*720*4;
    for(screen=0;screen<PM_SCREEN_COUNT;screen++) {f.screen=(PmScreen)screen;pm_frontend_render(&f,&view,&target);}
    for(j=0;j<16;j++) {assert(bytes[j]==0x5a);assert(bytes[1280*720*4+16+j]==0x5a);}
    memset(bytes+16,0x5a,1280*720*4);target.bytes=1;pm_frontend_render(&f,&view,&target);assert(bytes[16]==0x5a);
    target.bytes=1280*720*4;target.stride=1;pm_frontend_render(&f,&view,&target);assert(bytes[16]==0x5a);
    free(bytes);
    puts("Frontend navigation and framebuffer guard tests passed.");return 0;
}
