/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _XOPEN_SOURCE 700
#include "pm_icons.h"
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_ONLY_JPEG
#define STBI_NO_STDIO
#define STBI_NO_HDR
#define STBI_NO_LINEAR
#define STBI_NO_THREAD_LOCALS
#ifdef __PROSPERO__
/* The PS5 payload runtime has no emulated TLS or libc assertion export.
 * Input validation remains in the decoder; host sanitizer builds retain its
 * internal assertions. This cache is used only by the launcher UI thread. */
#define STBI_ASSERT(condition) ((void)0)
#endif
#define STBI_MAX_DIMENSIONS 2048
#include "../../vendor/stb/stb_image.h"
#include "src/webp/decode.h"

enum { ICON_COUNT=64, ICON_SIZE=128, ICON_FILE_LIMIT=4*1024*1024 };
typedef struct Icon {
    char path[512];
    uint8_t *pixels;
    unsigned width,height;
    unsigned long used,retry;
    int pending;
} Icon;
static Icon icons[ICON_COUNT];
static char root[PATH_MAX];
static unsigned long frame,access_count;

void pm_icons_invalidate(void)
{
    for(unsigned i=0;i<ICON_COUNT;i++) { free(icons[i].pixels); memset(&icons[i],0,sizeof(icons[i])); }
}
void pm_icons_init(const char *data_root)
{
    struct stat info;
    pm_icons_invalidate(); root[0]=0; frame=access_count=0;
    if(data_root&&data_root[0]=='/'&&strlen(data_root)<sizeof(root)&&
       !lstat(data_root,&info)&&S_ISDIR(info.st_mode))
        memcpy(root,data_root,strlen(data_root)+1);
}
static int icon_path(const char *path,char *normalized,size_t capacity)
{
    size_t length;
    if(!path||!root[0])return 0;
    if((path[0]=='Z'||path[0]=='z')&&path[1]==':')path+=2;
    length=strlen(path);
    if(!length||length>=capacity)return 0;
    for(size_t i=0;i<=length;i++)normalized[i]=path[i]=='\\'?'/':path[i];
    length=strlen(root);
    if(strncmp(normalized,root,length)||normalized[length]!='/')return 0;
    /* Refuse traversal before it can occupy a cache entry. The canonical
     * path is checked again on load so symlinks cannot leave app data. */
    for(const char *p=normalized;*p;p++)
        if(*p=='/'&&p[1]=='.'&&(p[2]=='/'||!p[2]||(p[2]=='.'&&(p[3]=='/'||!p[3]))))return 0;
    return 1;
}
const uint8_t *pm_icon_pixels(const char *path,unsigned *width,unsigned *height)
{
    char normalized[512];
    Icon *chosen=NULL;
    if(width)*width=0;
    if(height)*height=0;
    if(!icon_path(path,normalized,sizeof(normalized)))return NULL;
    for(unsigned i=0;i<ICON_COUNT;i++)if(!strcmp(icons[i].path,normalized)) {
        chosen=&icons[i]; break;
    }
    if(!chosen) {
        chosen=&icons[0];
        for(unsigned i=0;i<ICON_COUNT;i++) {
            if(!icons[i].path[0]) {chosen=&icons[i];break;}
            if(icons[i].used<chosen->used)chosen=&icons[i];
        }
        free(chosen->pixels);memset(chosen,0,sizeof(*chosen));
        memcpy(chosen->path,normalized,strlen(normalized)+1);
        chosen->pending=1;
    } else if(!chosen->pixels&&!chosen->pending&&frame>=chosen->retry)chosen->pending=1;
    chosen->used=++access_count;
    if(width)*width=chosen->width;
    if(height)*height=chosen->height;
    return chosen->pixels;
}
static void load_icon(Icon *icon)
{
    char checked[512];
    struct stat info;
    FILE *file=NULL;
    uint8_t *bytes=NULL,*decoded=NULL,*small=NULL;
    int width=0,height=0,channels=0;
    size_t root_length=strlen(root);
    icon->pending=0;icon->retry=frame+120;
    memcpy(checked,icon->path,strlen(icon->path)+1);
    /* Every parent inside app data must be a real directory, so a symlink
     * in an imported instance cannot redirect reads to another location. */
    for(size_t i=root_length+1;checked[i];i++)if(checked[i]=='/') {
        checked[i]=0;
        int invalid=lstat(checked,&info)||!S_ISDIR(info.st_mode);
        checked[i]='/';if(invalid)return;
    }
    if(lstat(checked,&info)||!S_ISREG(info.st_mode)||info.st_size<=0||info.st_size>ICON_FILE_LIMIT)return;
    bytes=malloc((size_t)info.st_size);
    if(!bytes)return;
    file=fopen(checked,"rb");
    if(!file)goto done;
    if(fread(bytes,1,(size_t)info.st_size,file)!=(size_t)info.st_size)goto done;
    fclose(file);file=NULL;
    int webp=info.st_size>=12&&!memcmp(bytes,"RIFF",4)&&!memcmp(bytes+8,"WEBP",4);
    if(webp) {
        if(!WebPGetInfo(bytes,(size_t)info.st_size,&width,&height)||width<=0||height<=0||width>2048||height>2048)goto done;
        decoded=malloc((size_t)width*height*4);
        if(decoded&&!WebPDecodeRGBAInto(bytes,(size_t)info.st_size,decoded,(size_t)width*height*4,width*4)) {
            free(decoded);decoded=NULL;
        }
    } else {
        if(!stbi_info_from_memory(bytes,(int)info.st_size,&width,&height,&channels)||width<=0||height<=0||width>2048||height>2048)goto done;
        decoded=stbi_load_from_memory(bytes,(int)info.st_size,&width,&height,&channels,4);
    }
    if(!decoded)goto done;
    unsigned out_width=(unsigned)width,out_height=(unsigned)height;
    if(out_width>ICON_SIZE||out_height>ICON_SIZE) {
        if(out_width>=out_height){out_height=(out_height*ICON_SIZE)/out_width;out_width=ICON_SIZE;}
        else {out_width=(out_width*ICON_SIZE)/out_height;out_height=ICON_SIZE;}
        if(!out_width)out_width=1;
        if(!out_height)out_height=1;
    }
    small=malloc((size_t)out_width*out_height*4);
    if(!small)goto done;
    for(unsigned y=0;y<out_height;y++)for(unsigned x=0;x<out_width;x++) {
        size_t source=((size_t)(y*(unsigned)height/out_height)*(unsigned)width+x*(unsigned)width/out_width)*4;
        memcpy(small+((size_t)y*out_width+x)*4,decoded+source,4);
    }
    icon->pixels=small;icon->width=out_width;icon->height=out_height;small=NULL;
done:
    if(file)fclose(file);
    free(bytes);stbi_image_free(decoded);free(small);
}
void pm_icons_tick(void)
{
    frame++;
    for(unsigned i=0;i<ICON_COUNT;i++)if(icons[i].pending){load_icon(&icons[i]);break;}
}
