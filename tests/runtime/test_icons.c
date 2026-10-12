/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _XOPEN_SOURCE 700
#include "pm_icons.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc,char **argv)
{
    char path[1024],moved[1024];
    unsigned width,height;
    const uint8_t *pixels;
    assert(argc==2);pm_icons_init(argv[1]);
    snprintf(path,sizeof(path),"%s/color.png",argv[1]);
    assert(!pm_icon_pixels(path,&width,&height)&&!width&&!height);
    pm_icons_tick();pixels=pm_icon_pixels(path,&width,&height);
    assert(pixels&&width==4&&height==2);
    assert(pixels[0]==255&&pixels[1]==20&&pixels[2]==30&&pixels[3]==77);
    /* Repeated render lookups use the decoded image, even without its file. */
    snprintf(moved,sizeof(moved),"%s/moved.png",argv[1]);
    assert(!rename(path,moved));
    for(int i=0;i<1000;i++)assert(pm_icon_pixels(path,&width,&height)==pixels);
    assert(!rename(moved,path));
    snprintf(path,sizeof(path),"%s/color.jpg",argv[1]);
    assert(!pm_icon_pixels(path,&width,&height));pm_icons_tick();
    pixels=pm_icon_pixels(path,&width,&height);
    assert(pixels&&width==2&&height==1&&pixels[2]>180&&pixels[0]<30&&pixels[3]==255);
    snprintf(path,sizeof(path),"%s/large.png",argv[1]);
    assert(!pm_icon_pixels(path,&width,&height));pm_icons_tick();
    pixels=pm_icon_pixels(path,&width,&height);assert(pixels&&width==128&&height==64);
    snprintf(path,sizeof(path),"%s/oversized.png",argv[1]);
    assert(!pm_icon_pixels(path,&width,&height));pm_icons_tick();assert(!pm_icon_pixels(path,&width,&height));
    snprintf(path,sizeof(path),"%s/bad.png",argv[1]);
    assert(!pm_icon_pixels(path,&width,&height));pm_icons_tick();assert(!pm_icon_pixels(path,&width,&height));
    snprintf(path,sizeof(path),"%s/link.png",argv[1]);
    assert(!pm_icon_pixels(path,&width,&height));pm_icons_tick();assert(!pm_icon_pixels(path,&width,&height));
    snprintf(path,sizeof(path),"%s/linkdir/color.png",argv[1]);
    assert(!pm_icon_pixels(path,&width,&height));pm_icons_tick();assert(!pm_icon_pixels(path,&width,&height));
    snprintf(path,sizeof(path),"%s/../outside.png",argv[1]);assert(!pm_icon_pixels(path,&width,&height));
    assert(!pm_icon_pixels("/etc/passwd",&width,&height));
    pm_icons_invalidate();
    for(unsigned i=0;i<96;i++) {
        snprintf(path,sizeof(path),"%s/entry-%u.png",argv[1],i);
        assert(!pm_icon_pixels(path,&width,&height));pm_icons_tick();
        assert(pm_icon_pixels(path,&width,&height));
    }
    snprintf(path,sizeof(path),"%s/entry-0.png",argv[1]);
    assert(!pm_icon_pixels(path,&width,&height));pm_icons_tick();assert(pm_icon_pixels(path,&width,&height));
    const char *webps[]={"1KVo5zza.webp","bHUKuhiA.webp"};
    for(unsigned j=0;j<2;j++) {
        snprintf(path,sizeof(path),"%s/%s",argv[1],webps[j]);
        assert(!pm_icon_pixels(path,&width,&height));pm_icons_tick();
        pixels=pm_icon_pixels(path,&width,&height);assert(pixels&&width==128&&height==128);
    }
    snprintf(path,sizeof(path),"%s/bad.webp",argv[1]);
    assert(!pm_icon_pixels(path,&width,&height));pm_icons_tick();assert(!pm_icon_pixels(path,&width,&height));
    pm_icons_invalidate();puts("INSTANCE_ICON_CACHE_PASS PNG/JPEG/WebP");return 0;
}
