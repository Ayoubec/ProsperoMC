"""Exercise actual fallback presentation through startup and later idle gaps."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]

class GameFallbackTests(unittest.TestCase):
    def test_active_game_cannot_be_replaced_by_gdi_or_spinner(self):
        source=(ROOT/'vendor/prospero-win/native/wine64_main.c').read_text()
        function=re.search(r'static int vulkan_frames_show\(.*?\n\}',source,re.S).group()
        c=r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
enum {PW_PRESENT_BGRX8=1,PW_PRESENT_SCALE_FIT=1,PW_WINE64_MAX_FRAME=16,PW_WINE64_PRESENTING_MS=1000};
typedef struct {const uint8_t *pixels;unsigned width,height,stride;} PwPresentView;
typedef struct {const uint8_t *pixels;unsigned width,height,stride;int format;} PwPresentFrame;
typedef struct {uint32_t *tiled;int (*idle)(void);} VulkanFrames;
typedef struct {int content;uint64_t presenting_since;} Loading;
static int frames,frame_shown,idle_value,gdi_value,spinner_value,flips,takes,idle_calls;
static int idle(void){idle_calls++;return idle_value;}
static void loading_done(Loading *l,const char *by){(void)by;l->content=1;}
static int pw_wine_frame_box_take(int *f,uint64_t *s,int p,int max,PwPresentView *v){
 (void)f;(void)s;(void)p;(void)max;takes++;*v=(PwPresentView){0,1,1,4};return gdi_value;
}
static int loading_admits(Loading *l,const PwPresentView *v){(void)v;if(gdi_value)l->content=1;return l->content;}
static const PwPresentFrame *loading_frame(Loading *l,uint64_t now,uint64_t started,PwPresentFrame *f){
 (void)l;(void)now;(void)started;*f=(PwPresentFrame){0};return spinner_value?f:NULL;
}
static int vulkan_frames_flip(VulkanFrames *vf,const PwPresentFrame *f,int scaling){(void)vf;(void)f;(void)scaling;flips++;return 1;}
''' + function + r'''
int main(void){
 uint32_t pixels[1];VulkanFrames vf={pixels,idle};Loading l={0};uint64_t seq=0;
 idle_value=1;spinner_value=1;
 assert(vulkan_frames_show(&vf,&seq,1,&l,1,0)==1&&flips==1&&!l.content);
 idle_value=0;
 assert(!vulkan_frames_show(&vf,&seq,1,&l,1000000,0));
 assert(!vulkan_frames_show(&vf,&seq,1,&l,1001000001,0)&&l.content);
 int before=flips,reads=takes,queries=idle_calls;
 idle_value=1;gdi_value=1;spinner_value=1;
 for(unsigned n=0;n<10000;n++)assert(!vulkan_frames_show(&vf,&seq,1,&l,2000000000ull+n,0));
 assert(flips==before&&takes==reads&&idle_calls==queries);
 /* A genuine startup GDI frame still displays once; later native gaps do not. */
 l=(Loading){0};assert(vulkan_frames_show(&vf,&seq,1,&l,1,0)==1&&l.content);
 before=flips;assert(!vulkan_frames_show(&vf,&seq,1,&l,2,0)&&flips==before);
 vf.tiled=NULL;l=(Loading){0};assert(!vulkan_frames_show(&vf,&seq,1,&l,2,0));
 return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='game-fallback-') as temporary:
            folder=Path(temporary);code=folder/'fixture.c';exe=folder/'fixture'
            code.write_text(c)
            subprocess.run(['clang-18','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                '-fno-sanitize-recover=all',str(code),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
        print('GAME_FALLBACK_PASS: startup spinner/GDI preserved;10000 native idle gaps produce no fallback flips or reads')

if __name__=='__main__':unittest.main()
