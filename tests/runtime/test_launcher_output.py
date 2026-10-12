"""Compile the output-mode guard with a mocked console service."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'vendor/prospero-win/native/pw_videoout_ps5.c').read_text()
start = source.index('int pw_videoout_ps5_fixed_output(')
end = source.index('\nint pw_videoout_ps5_close(', start)
code = r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#define PW_ERR_PRECONDITION -2
typedef struct { int opened, handle, refresh_unpeg_rc, refresh_peg_rc; } PwVideoOutPs5;
int pw_videoout_ps5_stable_refresh(PwVideoOutPs5 *);
static int requests, waits, request_error, wait_error;
int sceVideoOutConfigureOutput(int32_t handle,uint32_t preset,const void *a,const void *b,const void *c) {
 assert(handle==7 && preset==1 && !a && !b && !c); ++requests; return request_error;
}
int sceVideoOutWaitVblank(int32_t handle) { assert(handle==7); ++waits; return wait_error; }
int sceVideoOutVrrUnpegFromFixedRate(int32_t handle) { assert(handle==7); return 0; }
int sceVideoOutVrrPegToFixedRate(int32_t handle,uint64_t a,uint64_t b) { assert(handle==7&&!a&&!b); return 0; }
''' + source[start:end] + r'''
int main(void) {
 PwVideoOutPs5 video={0,-1,0,0};
 assert(pw_videoout_ps5_fixed_output(NULL)==PW_ERR_PRECONDITION);
 assert(pw_videoout_ps5_fixed_output(&video)==PW_ERR_PRECONDITION);
 assert(!requests && !waits);
 video.opened=1;video.handle=7;
 assert(!pw_videoout_ps5_fixed_output(&video));assert(requests==1 && waits==2);
 request_error=-3;assert(pw_videoout_ps5_fixed_output(&video)==-3);assert(waits==2);
 request_error=0;wait_error=-4;assert(pw_videoout_ps5_fixed_output(&video)==-4);assert(waits==3);
 puts("LAUNCHER_NORMAL_OUTPUT_GUARDS_PASS");
}
'''
with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    (folder / 'check.c').write_text(code)
    subprocess.run(['clang-18', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    str(folder / 'check.c'), '-o', str(folder / 'check')], check=True)
    subprocess.run([str(folder / 'check')], check=True)
