"""Execute the real UI sound generator and capture every output sample."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'vendor/prospero-win/native/wine64_main.c').read_text()
start = source.index('static void pm_play_click(')
end = source.index('\nstatic void pm_click_worker(', start)
code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef enum { PM_KEY_NONE, PM_KEY_UP, PM_KEY_CONFIRM, PM_KEY_BACK } PmKey;
#define PW_AUDIO_PS5_GRAIN 256
#define PW_AUDIO_PS5_RATE 48000
static int audio_port=7, peak, outputs, first, last;
static int capture(int port,const int16_t *samples) {
 assert(port==7);
 if(!outputs)first=samples[0];
 for(int i=0;i<PW_AUDIO_PS5_GRAIN;i++) {
  assert(samples[i*2]==samples[i*2+1]);
  int value=abs(samples[i*2]);if(value>peak)peak=value;
  assert(value<32767);
 }
 last=samples[(PW_AUDIO_PS5_GRAIN-1)*2];outputs++;return 0;
}
static struct { int (*output)(int,const int16_t *); } audio_ops={capture};
''' + source[start:end] + r'''
int main(void) {
 for(int key=PM_KEY_UP;key<=PM_KEY_BACK;key++) {
  peak=outputs=first=last=0;pm_play_click((PmKey)key);
  assert(peak>3000 && peak<=5000 && !first && !last);
  assert(outputs==(key==PM_KEY_CONFIRM?4:2));
  printf("UI_AUDIO_PASS key=%d peak=%d grains=%d\n",key,peak,outputs);
 }
 outputs=0;pm_play_click(PM_KEY_NONE);audio_port=-1;pm_play_click(PM_KEY_CONFIRM);assert(!outputs);
}
'''
with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    (folder / 'check.c').write_text(code)
    subprocess.run(['clang-18', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined,address', '-fno-sanitize-recover=all',
                    str(folder / 'check.c'), '-o', str(folder / 'check')], check=True)
    subprocess.run([str(folder / 'check')], check=True)
