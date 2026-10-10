/* Native framebuffer preview: no browser, CSS or parallel mock UI. */
#include "pm_frontend.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static PmView view;
static void fixture(void) {
    strcpy(view.status,"idle");view.memory_mb=2048;
    view.instance_count=1;strcpy(view.instances[0].id,"legacy-1.12.2");strcpy(view.instances[0].name,"Minecraft 1.12.2");
    strcpy(view.instances[0].version,"1.12.2");strcpy(view.instances[0].loader,"vanilla");view.instances[0].installed=1;
    view.version_count=6;
    {const char *v[]={"1.21.1","1.20.1","1.19.4","1.18.2","1.16.5","1.12.2"};int j;
    for(j=0;j<6;j++){strcpy(view.versions[j].id,v[j]);strcpy(view.versions[j].type,"release");view.versions[j].java=j<1?21:j<4?17:8;}}
    strcpy(view.java_path,"Java 8 / staged local runtime");strcpy(view.username,"Player");
    view.java_count=2;view.java_runtimes[0].major=8;view.java_runtimes[0].valid=1;
    strcpy(view.java_runtimes[0].version,"1.8.0_451");strcpy(view.java_runtimes[0].detail,"Detected Windows 64-bit Java runtime.");
    view.java_runtimes[1].major=21;view.java_runtimes[1].valid=1;
    strcpy(view.java_runtimes[1].version,"21.0.8");strcpy(view.java_runtimes[1].detail,"Detected Windows 64-bit Java runtime.");
}
static void load(const char *path) {
    FILE *fp=fopen(path,"rb");char line[1024];
    if(!fp) {perror(path);exit(2);}memset(&view,0,sizeof(view));
    while(fgets(line,sizeof(line),fp)) {
        char *value=strchr(line,'=');int n;char prop[100];
        if(!value||line[0]=='#') continue;
        *value++=0;value[strcspn(value,"\r\n")]=0;
        if(!strcmp(line,"status")) snprintf(view.status,sizeof(view.status),"%s",value);
        else if(!strcmp(line,"detail")) snprintf(view.detail,sizeof(view.detail),"%s",value);
        else if(!strcmp(line,"instance.count")) view.instance_count=atoi(value);
        else if(!strcmp(line,"version.count")) view.version_count=atoi(value);
        else if(!strcmp(line,"mod.count")) view.mod_count=atoi(value);
        else if(!strcmp(line,"java.count")) view.java_count=atoi(value);
        else if(!strcmp(line,"memoryMb")||!strcmp(line,"settings.memoryMb")) view.memory_mb=atoi(value);
        else if(!strcmp(line,"settings.java8")) snprintf(view.java_path,sizeof(view.java_path),"%s",value);
        else if(!strcmp(line,"auth.userCode")) snprintf(view.auth_code,sizeof(view.auth_code),"%s",value);
        else if(!strcmp(line,"auth.verificationUri")) snprintf(view.auth_url,sizeof(view.auth_url),"%s",value);
        else if(!strcmp(line,"auth.signedIn")) snprintf(view.account_status,sizeof(view.account_status),"%s",!strcmp(value,"true")?"Signed in":"Not signed in");
        else if(!strcmp(line,"auth.username")) snprintf(view.username,sizeof(view.username),"%s",value);
        else if(!strcmp(line,"username")||!strcmp(line,"settings.username")) snprintf(view.username,sizeof(view.username),"%s",value);
        else if(!strcmp(line,"settings.accountMode")) snprintf(view.account_mode,sizeof(view.account_mode),"%s",value);
        else if(!strcmp(line,"remote.pack.count"))view.remote_count=atoi(value);
        else if(!strcmp(line,"remote.version.count"))view.remote_version_count=atoi(value);
        else if(!strcmp(line,"remote.offset"))view.remote_offset=atoi(value);
        else if(!strcmp(line,"remote.total"))view.remote_total=atoi(value);
        else if(!strcmp(line,"remote.projectId"))snprintf(view.remote_project,sizeof(view.remote_project),"%s",value);
        else if(sscanf(line,"remote.pack.%d.%99s",&n,prop)==2&&n>=0&&n<24) {
            PmRemotePack *p=&view.remote_packs[n];
            if(!strcmp(prop,"id"))snprintf(p->id,sizeof(p->id),"%s",value);
            if(!strcmp(prop,"name"))snprintf(p->name,sizeof(p->name),"%s",value);
            if(!strcmp(prop,"description"))snprintf(p->description,sizeof(p->description),"%s",value);
        } else if(sscanf(line,"remote.version.%d.%99s",&n,prop)==2&&n>=0&&n<64) {
            PmPackRelease *p=&view.remote_versions[n];
            if(!strcmp(prop,"id"))snprintf(p->id,sizeof(p->id),"%s",value);
            if(!strcmp(prop,"name"))snprintf(p->name,sizeof(p->name),"%s",value);
            if(!strcmp(prop,"game"))snprintf(p->game,sizeof(p->game),"%s",value);
            if(!strcmp(prop,"loader"))snprintf(p->loader,sizeof(p->loader),"%s",value);
        } else if(sscanf(line,"instance.%d.%99s",&n,prop)==2&&n>=0&&n<PM_MAX_INSTANCES) {
            PmInstance *i=&view.instances[n];
            if(!strcmp(prop,"id")) snprintf(i->id,sizeof(i->id),"%s",value);
            if(!strcmp(prop,"name")) snprintf(i->name,sizeof(i->name),"%s",value);
            if(!strcmp(prop,"version")) snprintf(i->version,sizeof(i->version),"%s",value);
            if(!strcmp(prop,"loader")) snprintf(i->loader,sizeof(i->loader),"%s",value);
            if(!strcmp(prop,"installed")) i->installed=!strcmp(value,"true");
        } else if(sscanf(line,"version.%d.%99s",&n,prop)==2&&n>=0&&n<PM_MAX_VERSIONS) {
            PmVersion *v=&view.versions[n];
            if(!strcmp(prop,"id")) snprintf(v->id,sizeof(v->id),"%s",value);
            if(!strcmp(prop,"type")) snprintf(v->type,sizeof(v->type),"%s",value);
            if(!strcmp(prop,"java")) v->java=atoi(value);
        } else if(sscanf(line,"mod.%d.%99s",&n,prop)==2&&n>=0&&n<PM_MAX_MODS) {
            PmMod *m=&view.mods[n];if(!strcmp(prop,"name")) snprintf(m->name,sizeof(m->name),"%s",value);
            if(!strcmp(prop,"enabled")) m->enabled=!strcmp(value,"true");
        } else if(sscanf(line,"java.%d.%99s",&n,prop)==2&&n>=0&&n<PM_MAX_JAVA) {
            PmJavaRuntime *runtime=&view.java_runtimes[n];
            if(!strcmp(prop,"major"))runtime->major=atoi(value);
            if(!strcmp(prop,"valid"))runtime->valid=!strcmp(value,"true")||!strcmp(value,"1");
            if(!strcmp(prop,"version"))snprintf(runtime->version,sizeof(runtime->version),"%s",value);
            if(!strcmp(prop,"path"))snprintf(runtime->path,sizeof(runtime->path),"%s",value);
            if(!strcmp(prop,"detail"))snprintf(runtime->detail,sizeof(runtime->detail),"%s",value);
        }
    }
    fclose(fp);
}
int main(int argc,char **argv) {
    PmFrontend f;PwPresentTarget t;FILE *fp;int x,y;
    if(argc<3) {fprintf(stderr,"Usage: render output.ppm screen-number [launcher-view.properties|--empty]\n");return 2;}
    fixture();if(argc>3) {if(!strcmp(argv[3],"--empty")) memset(&view,0,sizeof(view));else if(strcmp(argv[3],"--packs"))load(argv[3]);}
    pm_frontend_init(&f);f.screen=(PmScreen)atoi(argv[2]);
    if(argc>4) {f.remote_browser=1;f.remote_stage=!strcmp(argv[4],"--releases");f.search_editor=!strcmp(argv[4],"--search");}
    if(argc>3 && !strcmp(argv[3],"--packs")) {
        f.pack_picker=1;view.pack_count=2;
        strcpy(view.packs[0].name,"My Forge 1.12.2.zip");strcpy(view.packs[1].name,"Forest adventures.mrpack");
    }
    for(int frame=0;frame<10;frame++)pm_frontend_tick(&f,100);
    t.width=1920;t.height=1080;t.stride=t.width*4;t.bytes=(uint64_t)t.stride*t.height;
    t.pixels=(unsigned char*)calloc(1,(size_t)t.bytes);if(!t.pixels) return 2;
    pm_frontend_render(&f,&view,&t);
    fp=fopen(argv[1],"wb");if(!fp) {perror(argv[1]);return 2;}
    fprintf(fp,"P6\n%d %d\n255\n",t.width,t.height);
    for(y=0;y<(int)t.height;y++) for(x=0;x<(int)t.width;x++) {
        const unsigned char *p=t.pixels+y*t.stride+x*4;fputc(p[2],fp);fputc(p[1],fp);fputc(p[0],fp);
    }
    fclose(fp);free(t.pixels);return 0;
}
