/* SPDX-License-Identifier: GPL-3.0-or-later
 * Original Minecraft launcher UI; ProsperoEden's spacing, green palette and
 * console focus language provide visual direction. No emulator code is used.
 */
#include "pm_frontend.h"
#include <stdio.h>
#include <string.h>
#include "pm_font.h"

#define BASE 0x06090a
#define PANEL 0x101c17
#define ROW 0x17241e
#define EDGE 0x354c3a
#define FOCUS 0x294433
#define LIME 0xa9db63
#define TITLE 0xfffcef
#define TEXT 0xe2e8d7
#define MUTED 0xaab8ac
#define FAINT 0x7e9385
#define WARN 0xe8b39a

static int bound(int n,int lo,int hi) { return n<lo?lo:n>hi?hi:n; }
static int count(int n,int cap) { return bound(n,0,cap); }
static void copy(char *to,size_t n,const char *from) { if(n) snprintf(to,n,"%s",from?from:""); }
static const char *loaders[] = {"vanilla","fabric","quilt","forge"};
static const char *tabs[] = {"Home","Library","Versions","Mods","Settings","Accounts"};
static const char *filters[] = {"All versions","Releases","Snapshots"};
static const int java_majors[] = {8,17,21,25};
static const PmJavaRuntime *runtime_for_major(const PmView *v,int major) {
    const PmJavaRuntime *found=NULL;int j;
    for(j=0;j<count(v->java_count,PM_MAX_JAVA);j++) {
        if(v->java_runtimes[j].major==major) {
            found=&v->java_runtimes[j];if(found->valid) break;
        }
    }
    return found;
}
static int visible_version(const PmFrontend *f,const PmVersion *v) {
    return f->version_filter==0||(f->version_filter==1&&(!v->type[0]||!strcmp(v->type,"release")))||
           (f->version_filter==2&&!strcmp(v->type,"snapshot"));
}
static int next_version(const PmFrontend *f,const PmView *v,int from,int delta) {
    int n=count(v->version_count,PM_MAX_VERSIONS),j;
    for(j=from;j>=0&&j<n;j+=delta) if(visible_version(f,&v->versions[j])) return j;
    return -1;
}

void pm_frontend_init(PmFrontend *f) {
    if(!f) return;
    memset(f,0,sizeof(*f)); f->memory_mb=2048;f->version_filter=1;
}

static void normalize(PmFrontend *f,const PmView *v) {
    f->screen=(PmScreen)bound(f->screen,0,PM_SCREEN_COUNT-1);
    f->selected_instance=bound(f->selected_instance,0,count(v->instance_count,PM_MAX_INSTANCES)?count(v->instance_count,PM_MAX_INSTANCES)-1:0);
    f->selected_version=bound(f->selected_version,0,count(v->version_count,PM_MAX_VERSIONS)?count(v->version_count,PM_MAX_VERSIONS)-1:0);
    f->selected_mod=bound(f->selected_mod,0,count(v->mod_count,PM_MAX_MODS)?count(v->mod_count,PM_MAX_MODS)-1:0);
    f->selected_java=bound(f->selected_java,0,count(v->java_count,PM_MAX_JAVA)?count(v->java_count,PM_MAX_JAVA)-1:0);
    f->loader_index=bound(f->loader_index,0,3);
    f->version_filter=bound(f->version_filter,0,2);
    if(count(v->version_count,PM_MAX_VERSIONS)&&!visible_version(f,&v->versions[f->selected_version])) {
        int first=next_version(f,v,0,1);if(first>=0) f->selected_version=first;
    }
    f->focus=bound(f->focus,0,f->screen==PM_SETTINGS?6:f->screen==PM_LIBRARY?4:f->screen==PM_VERSIONS?3:f->screen==PM_ACCOUNTS?2:1);
    f->memory_mb=bound(f->memory_mb,512,8192);
    if(!f->initialized_settings) {
        f->memory_mb=v->memory_mb?bound(v->memory_mb,512,8192):2048;
        f->initialized_settings=1;
    }
}

static int action(PmAction *a,const char *command,const PmInstance *i) {
    copy(a->command,sizeof(a->command),command);
    if(i) copy(a->id,sizeof(a->id),i->id);
    return 1;
}
static int unavailable(PmFrontend *f,const char *reason) {
    copy(f->notice,sizeof(f->notice),reason); return 0;
}

int pm_frontend_update(PmFrontend *f,const PmView *v,PmKey key,PmAction *a) {
    const PmInstance *i;
    int n,delta;
    if(!f||!v||!a) return 0;
    memset(a,0,sizeof(*a)); normalize(f,v);
    n=count(v->instance_count,PM_MAX_INSTANCES);
    i=n?&v->instances[f->selected_instance]:NULL;
    if(key==PM_KEY_NONE) return 0;
    if(key==PM_KEY_PREVIOUS_TAB||key==PM_KEY_NEXT_TAB) {
        f->screen=(PmScreen)((f->screen+(key==PM_KEY_NEXT_TAB?1:PM_SCREEN_COUNT-1))%PM_SCREEN_COUNT);
        f->focus=0; f->notice[0]=0;
        if(f->screen==PM_MODS&&i&&!v->busy) return action(a,"mods",i);
        return 0;
    }
    if(key==PM_KEY_BACK) { f->screen=PM_HOME;f->focus=0;f->notice[0]=0;return 0; }
    if(v->busy) return unavailable(f,"Operation in progress. Navigation remains available.");
    if(key==PM_KEY_REFRESH) return action(a,f->screen==PM_SETTINGS?"detect-java":f->screen==PM_MODS?"mods":"catalog",f->screen==PM_MODS?i:NULL);
    f->notice[0]=0;
    switch(f->screen) {
    case PM_HOME:
        if(key==PM_KEY_LEFT||key==PM_KEY_RIGHT) f->focus=1-f->focus;
        if(key==PM_KEY_UP||key==PM_KEY_DOWN) {
            if(n) f->selected_instance=(f->selected_instance+(key==PM_KEY_DOWN?1:n-1))%n;
        }
        if(key==PM_KEY_CONFIRM) {
            if(f->focus==1||!i) {f->screen=PM_VERSIONS;f->focus=0;return 0;}
            return action(a,i->installed?"prepare-launch":"install",i);
        }
        if(key==PM_KEY_SECONDARY) {f->screen=PM_LIBRARY;f->focus=0;}
        break;
    case PM_LIBRARY:
        if(key==PM_KEY_LEFT) f->focus=0;
        if(key==PM_KEY_RIGHT) f->focus=1;
        if(key==PM_KEY_UP||key==PM_KEY_DOWN) {
            delta=key==PM_KEY_DOWN?1:-1;
            if(f->focus==0) f->selected_instance=bound(f->selected_instance+delta,0,n?n-1:0);
            else f->focus=bound(f->focus+delta,1,4);
        }
        if(key==PM_KEY_SECONDARY) {f->screen=PM_VERSIONS;f->focus=0;return 0;}
        if(key==PM_KEY_CONFIRM) {
            if(!i) {f->screen=PM_VERSIONS;f->focus=0;return 0;}
            if(f->focus<=1) return action(a,i->installed?"prepare-launch":"install",i);
            if(f->focus==2) {f->screen=PM_MODS;f->focus=0;return action(a,"mods",i);}
            if(f->focus==3) return action(a,"clone",i);
            if(f->focus==4) return action(a,"export",i);
        }
        break;
    case PM_VERSIONS:
        n=count(v->version_count,PM_MAX_VERSIONS);
        if(key==PM_KEY_SECONDARY) {
            f->version_filter=(f->version_filter+1)%3;
            normalize(f,v);return 0;
        }
        if(key==PM_KEY_LEFT) {
            if(f->focus==1) f->loader_index=(f->loader_index+3)%4;
            else f->focus=0;
        }
        if(key==PM_KEY_RIGHT) {
            if(f->focus==1) f->loader_index=(f->loader_index+1)%4;
            else f->focus=1;
        }
        if(key==PM_KEY_UP||key==PM_KEY_DOWN) {
            delta=key==PM_KEY_DOWN?1:-1;
            if(f->focus==0) {
                int next=next_version(f,v,f->selected_version+delta,delta);
                if(next>=0) f->selected_version=next;
            }
            else f->focus=bound(f->focus+delta,1,3);
        }
        if(key==PM_KEY_CONFIRM) {
            if(f->focus==3||!n||next_version(f,v,0,1)<0) return action(a,"catalog",NULL);
            if(f->focus==1) {f->loader_index=(f->loader_index+1)%4;return 0;}
            if(f->loader_index==3&&strcmp(v->versions[f->selected_version].id,"1.12.2"))
                return unavailable(f,"Legacy Forge supports Minecraft 1.12.2 in this build.");
            copy(a->version,sizeof(a->version),v->versions[f->selected_version].id);
            copy(a->loader,sizeof(a->loader),loaders[f->loader_index]);
            snprintf(a->name,sizeof(a->name),"Minecraft %s - %s",a->version,a->loader);
            return action(a,"create-install",NULL);
        }
        break;
    case PM_MODS:
        n=count(v->mod_count,PM_MAX_MODS);
        if(key==PM_KEY_UP||key==PM_KEY_DOWN) f->selected_mod=bound(f->selected_mod+(key==PM_KEY_DOWN?1:-1),0,n?n-1:0);
        if(key==PM_KEY_CONFIRM) {
            if(!i) return unavailable(f,"Create or import an instance first.");
            if(!n) return unavailable(f,"Place a .jar in this instance's mods folder, then refresh.");
            copy(a->mod,sizeof(a->mod),v->mods[f->selected_mod].name);
            copy(a->enabled,sizeof(a->enabled),v->mods[f->selected_mod].enabled?"false":"true");
            return action(a,"mod-toggle",i);
        }
        if(key==PM_KEY_SECONDARY&&i) return action(a,"mods",i);
        break;
    case PM_SETTINGS:
        if(key==PM_KEY_SECONDARY) {
            n=count(v->java_count,PM_MAX_JAVA);
            if(n)f->selected_java=(f->selected_java+1)%n;
            return 0;
        }
        if(key==PM_KEY_UP) f->focus=f->focus>4?1:0;
        if(key==PM_KEY_DOWN) f->focus=f->focus==0?1:f->focus<=4?5:6;
        if(key==PM_KEY_LEFT||key==PM_KEY_RIGHT) {
            delta=key==PM_KEY_RIGHT?1:-1;
            if(f->focus==0) f->memory_mb=bound(f->memory_mb+delta*256,512,8192);
            else if(f->focus<=4) f->focus=bound(f->focus+delta,1,4);
            else f->focus=bound(f->focus+delta,5,6);
        }
        if(key==PM_KEY_CONFIRM) {
            if(f->focus>=1&&f->focus<=4) {
                a->java_major=java_majors[f->focus-1];return action(a,"install-java",NULL);
            }
            if(f->focus==5) return action(a,"detect-java",NULL);
            a->memory_mb=f->memory_mb;
            return action(a,"settings",NULL);
        }
        break;
    case PM_ACCOUNTS:
        if(key==PM_KEY_UP||key==PM_KEY_DOWN) f->focus=bound(f->focus+(key==PM_KEY_DOWN?1:-1),0,2);
        if(key==PM_KEY_CONFIRM) {
            if(f->focus==0) {
                copy(a->account_mode,sizeof(a->account_mode),!strcmp(v->account_mode,"offline")?"microsoft":"offline");
                copy(a->username,sizeof(a->username),v->username[0]?v->username:"Player");
                return action(a,"settings",NULL);
            }
            if(!strcmp(v->account_mode,"offline"))return unavailable(f,"Switch to Microsoft mode to sign in.");
            return action(a,f->focus==1?"auth-device":"auth-poll",NULL);
        }
        break;
    default: break;
    }
    return 0;
}

/* CPU draw primitives. Work in 1080p design coordinates; targets may vary. */
typedef struct Canvas { const PwPresentTarget *t; } Canvas;
static uint32_t mix(uint32_t a,uint32_t b,unsigned alpha) {
    unsigned r=((a>>16&255)*(255-alpha)+(b>>16&255)*alpha)/255;
    unsigned g=((a>>8&255)*(255-alpha)+(b>>8&255)*alpha)/255;
    unsigned bl=((a&255)*(255-alpha)+(b&255)*alpha)/255;
    return (r<<16)|(g<<8)|bl;
}
static void px(Canvas *c,int x,int y,uint32_t rgb,unsigned alpha) {
    uint8_t *p;
    if(x<0||y<0||x>=(int)c->t->width||y>=(int)c->t->height) return;
    p=c->t->pixels+(size_t)y*c->t->stride+(size_t)x*4;
    if(alpha<255) rgb=mix(((uint32_t)p[2]<<16)|((uint32_t)p[1]<<8)|p[0],rgb,alpha);
    p[0]=(uint8_t)rgb;p[1]=(uint8_t)(rgb>>8);p[2]=(uint8_t)(rgb>>16);p[3]=255;
}
static int sx(Canvas *c,int x) {return (int)((int64_t)x*c->t->width/1920);}
static int sy(Canvas *c,int y) {return (int)((int64_t)y*c->t->height/1080);}
static void box(Canvas *c,int x,int y,int w,int h,uint32_t rgb) {
    int left=bound(sx(c,x),0,c->t->width),top=bound(sy(c,y),0,c->t->height);
    int right=bound(sx(c,x+w),0,c->t->width),bottom=bound(sy(c,y+h),0,c->t->height),xx,yy;
    for(yy=top;yy<bottom;yy++) for(xx=left;xx<right;xx++) px(c,xx,yy,rgb,255);
}
static void roundbox(Canvas *c,int x,int y,int w,int h,int rad,uint32_t rgb) {
    int xx,yy,dx,dy,left=sx(c,x),top=sy(c,y),right=sx(c,x+w),bottom=sy(c,y+h);
    int rx=sx(c,rad),ry=sy(c,rad);
    if(rx<1||ry<1) {box(c,x,y,w,h,rgb);return;}
    for(yy=bound(top,0,c->t->height);yy<bound(bottom,0,c->t->height);yy++) {
        for(xx=bound(left,0,c->t->width);xx<bound(right,0,c->t->width);xx++) {
            dx=xx<left+rx?left+rx-xx:xx>=right-rx?xx-(right-rx-1):0;
            dy=yy<top+ry?top+ry-yy:yy>=bottom-ry?yy-(bottom-ry-1):0;
            if(!dx||!dy||(int64_t)dx*dx*ry*ry+(int64_t)dy*dy*rx*rx<=(int64_t)rx*rx*ry*ry) px(c,xx,yy,rgb,255);
        }
    }
}
static void panel(Canvas *c,int x,int y,int w,int h,int focused) {
    roundbox(c,x,y,w,h,20,focused?LIME:EDGE);
    roundbox(c,x+2,y+2,w-4,h-4,18,focused?FOCUS:PANEL);
}
static int text_width(const char *s,int size) {
    int width=0;
    while(*s) {unsigned ch=(unsigned char)*s++;if(ch<32||ch>126) ch='?';width+=pm_glyphs[ch-32].advance*size/48;}
    return width;
}
static void text(Canvas *c,const char *s,int x,int y,int size,uint32_t rgb,int max_width) {
    int pen=x;
    if(!s) return;
    while(*s) {
        unsigned ch=(unsigned char)*s++;const PmGlyph *g;int l,t,w,h,xx,yy,gx,gy;
        if(ch<32||ch>126) ch='?';
        g=&pm_glyphs[ch-32];
        if(max_width>0&&pen+g->advance*size/48>x+max_width) break;
        l=sx(c,pen+g->left*size/48);t=sy(c,y+(46+g->top)*size/48);
        w=sx(c,g->width*size/48);h=sy(c,g->height*size/48);
        if(w&&h) for(yy=0;yy<h;yy++) for(xx=0;xx<w;xx++) {
            gx=xx*g->width/w;gy=yy*g->height/h;
            px(c,l+xx,t+yy,rgb,pm_font_pixels[g->offset+gy*g->width+gx]);
        }
        pen+=g->advance*size/48;
    }
}
static void small(Canvas *c,const char *s,int x,int y,uint32_t color,int maxw) {text(c,s,x,y,24,color,maxw);}
static float segment_distance_squared(float x,float y,float ax,float ay,float bx,float by) {
    float dx=bx-ax,dy=by-ay,t=((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy);
    if(t<0)t=0;
    if(t>1)t=1;
    dx=x-ax-t*dx;dy=y-ay-t*dy;return dx*dx+dy*dy;
}
/* Shared size, stroke, color and antialiasing for every controller symbol. */
static void controller_symbol(Canvas *c,char shape,int x,int y) {
    int w=sx(c,26),h=sy(c,26),left=sx(c,x),top=sy(c,y);
    if(w<=0||h<=0)return;
    for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++) {
        unsigned hits=0;
        for(int j=0;j<4;j++)for(int i=0;i<4;i++) {
            float px0=(xx+(i+.5f)/4)*26/w,py0=(yy+(j+.5f)/4)*26/h,d=1000;
#define EDGE_DISTANCE(ax,ay,bx,by) do {float v=segment_distance_squared(px0,py0,ax,ay,bx,by);if(v<d)d=v;} while(0)
            if(shape=='X') {EDGE_DISTANCE(5,5,21,21);EDGE_DISTANCE(5,21,21,5);}
            else if(shape=='O') {float dx=px0-13,dy=py0-13,r=dx*dx+dy*dy;d=(r>=81&&r<=121)?0:1000;}
            else if(shape=='T') {EDGE_DISTANCE(13,2,1,24);EDGE_DISTANCE(1,24,25,24);EDGE_DISTANCE(25,24,13,2);}
            else {EDGE_DISTANCE(3,3,23,3);EDGE_DISTANCE(23,3,23,23);EDGE_DISTANCE(23,23,3,23);EDGE_DISTANCE(3,23,3,3);}
#undef EDGE_DISTANCE
            if(d<=1)hits++;
        }
        if(hits)px(c,left+xx,top+yy,TEXT,hits*255/16);
    }
}
static void button(Canvas *c,const char *s,int x,int y,int w,int focused,int primary) {
    roundbox(c,x,y,w,66,12,focused?LIME:primary?0x527444:EDGE);
    if(!primary) roundbox(c,x+2,y+2,w-4,62,10,focused?FOCUS:ROW);
    text(c,s,x+(w-text_width(s,24))/2,y+17,24,primary?0x111b14:focused?TITLE:TEXT,w-20);
}
static void chip(Canvas *c,const char *s,int x,int y,int accent) {
    int w=text_width(s,20)+30;
    roundbox(c,x,y,w,38,10,accent?0x294433:ROW);
    text(c,s,x+15,y+9,20,accent?LIME:MUTED,w-22);
}

static void terrain(Canvas *c,int x,int y,int w,int h) {
    int row,col,v,by,bh;
    for(row=0;row<h;row++) box(c,x,y+row,w,1,mix(0x14322e,0x44765e,(unsigned)(row*100/h)));
    /* Quiet block landscape, built directly into the native framebuffer. */
    box(c,x+w-162,y+64,58,58,0xb8c99c);box(c,x+w-153,y+72,58,58,0x9eb987);
    for(col=0;col<w/32+1;col++) {
        v=(col*13+col*col*7)%9;
        by=y+h-150-v*13;
        int width=bound(w-col*32,0,32);
        box(c,x+col*32,by,width,y+h-by,0x315343);
        box(c,x+col*32,by,width,14,0x507954);
    }
    for(col=0;col<w/48+1;col++) {
        int width=bound(w-col*48,0,48);
        v=(col*col*17+col*31)%7;by=y+h-104-v*13;bh=y+h-by;
        box(c,x+col*48,by,width,bh,0x24382b);box(c,x+col*48,by,width,17,0x83a159);
        for(row=1;row<bh/24;row++) box(c,x+col*48+(row%2)*6,by+row*24,bound(width-(row%2)*6,0,24),5,0x314730);
    }
    box(c,x+w-298,y+h-330,24,180,0x435139);
    box(c,x+w-356,y+h-338,136,52,0x426745);
    box(c,x+w-337,y+h-378,97,58,0x527b49);
    box(c,x+w-316,y+h-403,58,42,0x729357);
    box(c,x+74,y+h-217,18,90,0x49553a);
    box(c,x+44,y+h-240,80,49,0x385b3a);
    box(c,x+59,y+h-265,48,44,0x507545);
    for(row=0;row<h;row++) {
        unsigned a=(unsigned)(160*(h-row)/h);
        int xx,yy=sy(c,y+row);
        for(xx=sx(c,x);xx<sx(c,x+w);xx++) px(c,xx,yy,0x0e1b16,a/2);
    }
}
static void cube(Canvas *c,int x,int y,int size,int variant) {
    uint32_t soil=variant==1?0x576477:variant==2?0x6c4864:0x665442;
    uint32_t grass=variant==1?0x9db9c7:variant==2?0xc189b1:0x9eb76c;
    roundbox(c,x,y,size,size,12,soil);
    roundbox(c,x,y,size,size/3+6,12,grass);
    box(c,x,y+size/4,size,size/9,grass);
    box(c,x+size/7,y+size/2,size/5,size/8,mix(soil,BASE,50));
    box(c,x+size/2,y+size*2/3,size/5,size/9,mix(soil,TITLE,30));
}

static void header(Canvas *c,const PmFrontend *f,const PmView *v) {
    int j,x=578,issue=strstr(v->status,"error")!=NULL||strstr(v->status,"fail")!=NULL;
    cube(c,86,55,46,0);
    text(c,"PROSPERO",150,53,30,TITLE,260);text(c,"MC",358,53,30,LIME,70);
    small(c,"JAVA EDITION / PS5",151,92,FAINT,330);
    for(j=0;j<PM_SCREEN_COUNT;j++) {
        int w=text_width(tabs[j],26)+34;
        if(f->screen==(PmScreen)j) {roundbox(c,x-12,54,w,51,13,ROW);box(c,x+5,109,w-33,3,LIME);}
        text(c,tabs[j],x+4,65,26,f->screen==(PmScreen)j?TITLE:MUTED,w-10);x+=w+19;
    }
    box(c,84,145,1752,1,EDGE);
    roundbox(c,1687,67,14,14,7,v->busy||issue?WARN:LIME);
    small(c,v->busy?"WORKING":issue?"ISSUE":"READY",1713,59,v->busy||issue?WARN:MUTED,134);
}
static void footer(Canvas *c,const PmFrontend *f,const PmView *v) {
    const char *hint=f->screen==PM_MODS?"Toggle mod":f->screen==PM_VERSIONS?"Download version":f->screen==PM_SETTINGS?"Apply / download":"Select";
    box(c,84,961,1752,1,EDGE);
    small(c,"L1 / R1  Navigate",88,990,TEXT,300);
    controller_symbol(c,'X',438,990);small(c,hint,478,990,TEXT,285);
    controller_symbol(c,'O',783,990);small(c,"Home",823,990,TEXT,220);
    controller_symbol(c,'T',1047,990);
    small(c,f->screen==PM_SETTINGS?"Detect Java":"Refresh",1086,990,TEXT,330);
    if(f->screen==PM_SETTINGS||f->screen==PM_VERSIONS) {
        controller_symbol(c,'S',1510,990);
        small(c,f->screen==PM_SETTINGS?"Runtime info":"Filter",1550,990,TEXT,295);
    } else small(c,"D-PAD / ARROWS",1510,990,FAINT,335);
    if(f->notice[0]) {
        roundbox(c,114,896,1692,48,12,0x40392c);
        small(c,f->notice,140,906,WARN,1640);
    } else if(v->detail[0]&&strcmp(v->status,"idle")!=0) {
        small(c,v->detail,116,907,v->busy?LIME:MUTED,1680);
        if(v->busy&&v->progress_total>0) {
            box(c,114,940,1692,4,EDGE);
            box(c,114,940,(int)((int64_t)1692*bound(v->progress_done,0,v->progress_total)/v->progress_total),4,LIME);
        }
    }
}
static void home(Canvas *c,const PmFrontend *f,const PmView *v) {
    char buffer[256];int n=count(v->instance_count,PM_MAX_INSTANCES),j;
    const PmInstance *i=n?&v->instances[bound(f->selected_instance,0,n-1)]:NULL;
    panel(c,108,187,1704,470,0);
    terrain(c,1110,190,698,462);
    chip(c,"MINECRAFT JAVA",150,227,1);
    text(c,i?i->name:"Your next world awaits.",150,294,48,TITLE,936);
    small(c,i?"A world of your own, ready when you are.":"Create an instance. Choose a version. Make it yours.",153,368,TEXT,935);
    if(i) {
        snprintf(buffer,sizeof(buffer),"%s  /  %s  /  %s",i->version,i->loader,i->installed?"Installed":"Needs installation");
        small(c,buffer,153,419,MUTED,930);
    } else small(c,"Vanilla, Fabric, Quilt and legacy Forge instances.",153,419,MUTED,930);
    button(c,i?(i->installed?"PLAY INSTANCE":"INSTALL INSTANCE"):"CHOOSE A VERSION",152,519,326,f->focus==0,1);
    button(c,"NEW INSTANCE",500,519,274,f->focus==1,0);
    small(c,"YOUR INSTANCES",112,700,FAINT,900);
    snprintf(buffer,sizeof(buffer),"%d INSTANCE%s",n,n==1?"":"S");small(c,buffer,1620,700,FAINT,195);
    for(j=0;j<3;j++) {
        int index=n?(bound(f->selected_instance,0,n-1)+j)%n:0;int x=108+j*573;
        panel(c,x,746,550,126,j==0&&n);
        if(j<n) {
            cube(c,x+25,774,68,j);text(c,v->instances[index].name,x+115,766,26,TITLE,408);
            snprintf(buffer,sizeof(buffer),"%s  /  %s",v->instances[index].version,v->instances[index].loader);
            small(c,buffer,x+115,816,MUTED,390);
        } else {
            text(c,j==0?"Build your library":"Room for another world",x+26,770,26,j==0?TEXT:FAINT,494);
            small(c,j==0?"Open Versions to get started.":"Your instances will appear here.",x+26,819,FAINT,494);
        }
    }
}
static void screen_title(Canvas *c,const char *title,const char *subtitle) {
    text(c,title,112,183,42,TITLE,1580);small(c,subtitle,115,243,MUTED,1590);
}
static void empty(Canvas *c,const char *title,const char *body) {
    text(c,title,150,406,30,TEXT,650);small(c,body,150,467,MUTED,652);
}
static void library(Canvas *c,const PmFrontend *f,const PmView *v) {
    int n=count(v->instance_count,PM_MAX_INSTANCES),selected=bound(f->selected_instance,0,n?n-1:0),start,j;
    char b[256];const PmInstance *i=n?&v->instances[selected]:NULL;
    screen_title(c,"Your library","Every instance has its own Minecraft files, mods and settings.");
    panel(c,108,302,820,578,0);panel(c,968,302,844,578,0);
    if(!n) empty(c,"No instances yet","Open Versions to create your first instance.");
    start=selected>4?selected-4:0;
    for(j=start;j<n&&j<start+5;j++) {
        int y=326+(j-start)*100;int focused=j==selected;
        if(focused) {roundbox(c,128,y,780,88,13,f->focus==0?LIME:EDGE);roundbox(c,130,y+2,776,84,11,FOCUS);}
        cube(c,148,y+14,57,j%3);text(c,v->instances[j].name,229,y+12,27,TITLE,648);
        snprintf(b,sizeof(b),"%s  /  %s",v->instances[j].version,v->instances[j].loader);small(c,b,230,y+51,MUTED,628);
        if(v->instances[j].installed) box(c,878,y+41,8,8,LIME);
    }
    if(i) {
        cube(c,1010,335,77,selected%3);text(c,i->name,1110,341,32,TITLE,658);
        snprintf(b,sizeof(b),"Minecraft %s / %s",i->version,i->loader);small(c,b,1111,389,MUTED,653);
        chip(c,i->installed?"INSTALLED":"INSTALL REQUIRED",1012,453,i->installed);
        button(c,i->installed?"PLAY INSTANCE":"DOWNLOAD AND INSTALL",1010,533,758,f->focus==1,1);
        button(c,"MANAGE MODS",1010,609,758,f->focus==2,0);
        button(c,"CLONE INSTANCE",1010,685,758,f->focus==3,0);
        button(c,"EXPORT INSTANCE",1010,761,758,f->focus==4,0);
    } else {
        text(c,"A clean start.",1011,343,36,TITLE,744);small(c,"Use the version catalog to create an instance.",1011,407,MUTED,744);
        button(c,"OPEN VERSIONS",1010,761,758,1,1);
    }
}
static void versions(Canvas *c,const PmFrontend *f,const PmView *v) {
    int n=count(v->version_count,PM_MAX_VERSIONS),sel=bound(f->selected_version,0,n?n-1:0),j,start=sel,rows=0,k;
    char b[256];const PmVersion *version=next_version(f,v,0,1)>=0?&v->versions[sel]:NULL;
    snprintf(b,sizeof(b),"%s / Square changes filter. Each instance keeps its own Minecraft files.",filters[f->version_filter]);
    screen_title(c,"Choose your Minecraft",b);
    panel(c,108,302,820,578,0);panel(c,968,302,844,578,0);
    if(!version) empty(c,n?"No matching versions":"Version catalog is empty",n?"Press Square to change the version filter.":"Press Triangle to download the Mojang catalog.");
    for(k=0;k<5;k++) {int prev=next_version(f,v,start-1,-1);if(prev<0) break;start=prev;}
    for(j=start;j<n&&rows<6;j++) {
        int y;
        if(!visible_version(f,&v->versions[j])) continue;
        y=325+rows++*86;
        if(j==sel) {roundbox(c,128,y,780,74,12,f->focus==0?LIME:EDGE);roundbox(c,130,y+2,776,70,10,FOCUS);}
        text(c,v->versions[j].id,153,y+16,28,TITLE,482);small(c,v->versions[j].type,674,y+18,FAINT,202);
    }
    text(c,version?version->id:"Find a version",1010,342,46,TITLE,752);
    if(version&&version->java>0) snprintf(b,sizeof(b),"%s   /   Java %d",version->type,version->java);
    else snprintf(b,sizeof(b),"%s   /   Java automatic",version?version->type:"Minecraft Java");
    small(c,b,1013,409,MUTED,730);
    small(c,"MOD LOADER",1013,475,FAINT,730);
    snprintf(b,sizeof(b),"<   %s   >",f->loader_index==3?"Legacy Forge (1.12.2)":loaders[bound(f->loader_index,0,3)]);button(c,b,1010,517,758,f->focus==1,0);
    small(c,"Downloads Minecraft and the Java it needs.",1013,618,MUTED,746);
    small(c,"Legacy Forge is available for Minecraft 1.12.2.",1013,659,FAINT,746);
    button(c,"DOWNLOAD VERSION",1010,725,758,f->focus==2||f->focus==0,1);
    button(c,"REFRESH CATALOG",1010,801,758,f->focus==3,0);
}
static void mods(Canvas *c,const PmFrontend *f,const PmView *v) {
    int n=v->instance_count>0?count(v->mod_count,PM_MAX_MODS):0,sel=bound(f->selected_mod,0,n?n-1:0),j,start=sel>5?sel-5:0;
    int instances=count(v->instance_count,PM_MAX_INSTANCES);char b[256];
    screen_title(c,"Make it your own","Enable and disable individual .jar mods for the selected instance.");
    panel(c,108,302,1704,578,0);
    snprintf(b,sizeof(b),"INSTANCE / %s",instances?v->instances[bound(f->selected_instance,0,instances-1)].name:"None selected");small(c,b,150,328,LIME,1610);
    if(!n) {
        text(c,"No mods in this instance.",150,428,36,TITLE,1512);
        small(c,"Place compatible .jar files in the instance's mods folder, then refresh.",150,496,MUTED,1570);
        small(c,"Choose Fabric, Quilt or legacy Forge for a modded instance.",150,543,FAINT,1570);
        small(c,"Add mod files and import modpacks through the host launcher CLI.",150,638,FAINT,1570);
    }
    for(j=start;j<n&&j<start+6;j++) {
        int y=378+(j-start)*77;
        if(j==sel) {roundbox(c,130,y,1660,67,12,LIME);roundbox(c,132,y+2,1656,63,10,FOCUS);}
        text(c,v->mods[j].name,155,y+15,27,TITLE,1347);
        roundbox(c,1604,y+17,144,33,10,v->mods[j].enabled?0x32513d:ROW);
        text(c,v->mods[j].enabled?"ENABLED":"DISABLED",1615,y+24,18,v->mods[j].enabled?LIME:FAINT,126);
    }
}
static void settings(Canvas *c,const PmFrontend *f,const PmView *v) {
    char b[256];int mb=bound(f->memory_mb,512,8192),j;
    screen_title(c,"Launcher settings","Java is detected automatically. Minecraft downloads include the required runtime.");
    panel(c,108,302,1704,578,0);
    panel(c,137,327,1646,125,f->focus==0);
    text(c,"Minecraft memory",168,345,30,TITLE,1330);
    small(c,"Left / right adjusts in 256 MB steps.",171,391,MUTED,1146);
    snprintf(b,sizeof(b),"%d MB",mb);text(c,b,1500,352,30,LIME,250);
    box(c,173,435,1569,4,EDGE);box(c,173,435,(mb-512)*1569/(8192-512),4,LIME);
    text(c,"Java runtimes",140,479,30,TITLE,980);
    small(c,"Windows 64-bit / detected in launcher data",1150,484,FAINT,630);
    for(j=0;j<4;j++) {
        const PmJavaRuntime *runtime=runtime_for_major(v,java_majors[j]);
        int x=137+j*416,valid=runtime&&runtime->valid;
        panel(c,x,538,398,139,f->focus==j+1);
        snprintf(b,sizeof(b),"Java %d",java_majors[j]);text(c,b,x+23,553,30,TITLE,350);
        roundbox(c,x+348,565,11,11,5,valid?LIME:FAINT);
        small(c,valid?runtime->version:runtime?"Needs repair":"Not installed",x+23,603,valid?LIME:MUTED,351);
        text(c,valid?"GET / VERIFY":"DOWNLOAD",x+23,644,20,FAINT,350);
    }
    if(count(v->java_count,PM_MAX_JAVA)) {
        int total=count(v->java_count,PM_MAX_JAVA),index=bound(f->selected_java,0,total-1);
        const PmJavaRuntime *selected=&v->java_runtimes[index];
        snprintf(b,sizeof(b),"Detected %d / %d: Java %d / %.64s / %s",index+1,total,selected->major,selected->version,selected->valid?"Ready":"Needs repair");
        small(c,b,140,698,selected->valid?MUTED:WARN,1610);
        text(c,selected->detail[0]?selected->detail:selected->path,140,740,20,FAINT,1610);
    } else {
        small(c,"No Java runtimes detected. Select a card to download Java, or refresh.",140,702,MUTED,1610);
        text(c,"The Minecraft installer chooses and downloads the required Java automatically.",140,740,20,FAINT,1610);
    }
    button(c,"REFRESH RUNTIMES",137,771,790,f->focus==5,0);
    button(c,"SAVE MEMORY SETTINGS",959,771,824,f->focus==6,1);
}
static void accounts(Canvas *c,const PmFrontend *f,const PmView *v) {
    int offline=!strcmp(v->account_mode,"offline");
    screen_title(c,"Your Minecraft account","Choose local offline play or sign in using Microsoft's device flow.");
    panel(c,108,302,1704,578,0);
    text(c,v->username[0]?v->username:offline?"Player":"Microsoft sign-in",151,339,38,TITLE,1580);
    small(c,offline?"Local offline play / username shown above":v->account_status[0]?v->account_status:"A Minecraft Java license is required for online authentication.",153,399,MUTED,1580);
    button(c,offline?"MODE: OFFLINE  /  SWITCH TO MICROSOFT":"MODE: MICROSOFT  /  SWITCH TO OFFLINE",151,463,1490,f->focus==0,0);
    if(v->auth_code[0]&&!offline) {
        text(c,v->auth_code,150,558,58,LIME,700);
        small(c,"Open this address and enter the code:",968,549,TEXT,792);
        text(c,v->auth_url[0]?v->auth_url:"https://microsoft.com/link",968,592,29,LIME,792);
        small(c,"Return here, then choose Check sign-in.",968,650,MUTED,792);
    } else {
        small(c,offline?"Offline mode opens local worlds using the configured username.":"Start sign-in to receive a short code and a verification address.",153,575,TEXT,1520);
        small(c,offline?"Online servers may require a licensed Microsoft account.":"Configure a Microsoft client ID on the host before the first sign-in.",153,629,FAINT,1520);
    }
    button(c,"START SIGN-IN",151,749,530,f->focus==1,1);
    button(c,"CHECK SIGN-IN",710,749,530,f->focus==2,0);
}

void pm_frontend_render(const PmFrontend *frontend,const PmView *v,const PwPresentTarget *target) {
    PmFrontend f;Canvas c;int y;
    if(!frontend||!v||!target||!target->pixels||!target->width||!target->height||target->width>16384||target->height>16384) return;
    if(target->stride<(uint64_t)target->width*4||target->bytes<(uint64_t)target->stride*target->height) return;
    c.t=target;f=*frontend;normalize(&f,v);
    for(y=0;y<1080;y++) box(&c,0,y,1920,1,mix(BASE,0x112016,(unsigned)(y*26/1080)));
    header(&c,&f,v);
    switch(f.screen) {
    case PM_HOME:home(&c,&f,v);break;
    case PM_LIBRARY:library(&c,&f,v);break;
    case PM_VERSIONS:versions(&c,&f,v);break;
    case PM_MODS:mods(&c,&f,v);break;
    case PM_SETTINGS:settings(&c,&f,v);break;
    case PM_ACCOUNTS:accounts(&c,&f,v);break;
    default:break;
    }
    footer(&c,&f,v);
}
