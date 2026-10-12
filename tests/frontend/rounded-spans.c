#define _POSIX_C_SOURCE 200809L
#include "../../app/native/pm_frontend.c"
#include <assert.h>
#include <stdlib.h>
#include <time.h>

static void reference(Canvas *c,int x,int y,int w,int h,int rad,uint32_t rgb)
{
    int left=sx(c,x),top=sy(c,y),right=sx(c,x+w),bottom=sy(c,y+h);
    int rx=sx(c,rad),ry=sy(c,rad);
    if(rx<1||ry<1){box(c,x,y,w,h,rgb);return;}
    for(int yy=bound(top,0,c->t->height);yy<bound(bottom,0,c->t->height);yy++)
        for(int xx=bound(left,0,c->t->width);xx<bound(right,0,c->t->width);xx++) {
            int dx=xx<left+rx?left+rx-xx:xx>=right-rx?xx-(right-rx-1):0;
            int dy=yy<top+ry?top+ry-yy:yy>=bottom-ry?yy-(bottom-ry-1):0;
            if(!dx||!dy||(int64_t)dx*dx*ry*ry+(int64_t)dy*dy*rx*rx<=(int64_t)rx*rx*ry*ry)
                px(c,xx,yy,rgb,255);
        }
}
int main(void)
{
    enum {W=512,H=288,BYTES=W*H*4};
    uint8_t *a=malloc(BYTES),*b=malloc(BYTES);assert(a&&b);
    PwPresentTarget ta={a,W,H,W*4,BYTES},tb={b,W,H,W*4,BYTES};
    Canvas ca={.t=&ta,.opacity=255},cb={.t=&tb,.opacity=255};
    unsigned seed=771;
    for(unsigned j=0;j<5000;j++) {
        seed=seed*1664525u+1013904223u;int x=(int)(seed%2200)-140;
        seed=seed*1664525u+1013904223u;int y=(int)(seed%1300)-100;
        int radius=1+(int)(seed%25),w=radius*2+40+(int)(seed%430),h=radius*2+20+(int)(seed%160);
        memset(a,0x33,BYTES);memset(b,0x33,BYTES);
        reference(&ca,x,y,w,h,radius,0x70e6dc);roundbox(&cb,x,y,w,h,radius,0x70e6dc);
        assert(!memcmp(a,b,BYTES));
    }
    puts("ROUNDED_SPAN_EQUIVALENCE_PASS 5000 clipped/scaled layouts");
    free(a);free(b);return 0;
}
