"""Exercise the real worker-local shader lookup with concurrent mutation checks."""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
s = (root / 'artifacts/graphics-batching/ps5_agc_native_runtime.c').read_text()
structure = s[s.index('static struct runtime_shader_pair {'):s.index('/* Prepared draws write every')]
wrapper = re.search(r'static struct runtime_shader_pair \*runtime_shader_pair_get\(.*?\n\}', s, re.S).group()
start = s.index('    uintptr_t key =', s.index('static struct runtime_shader_pair *runtime_shader_pair_get_unlocked'))
end = s.index('    if (runtime_shader_pair_count ==', start)
lookup = s[start:end]
clear = s[s.index('static int runtime_shader_pair_clear(void)'):s.index('static int runtime_work_take(')]
assert clear.index('runtime_shader_pair_last = NULL') < clear.index('free(p->source)')
shutdown = s[s.index('int ps5_agc_gate2_shutdown_present('):s.index('static int runtime_video_prepare_draw(')]
assert shutdown.index('runtime_async_stop();') < shutdown.index('runtime_shader_pair_clear()')
c = r'''
#define _POSIX_C_SOURCE 200809L
#define PS5_ASYNC_NATIVE_PREP 1
#include <assert.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {int unused;} agc_api_t;
static _Thread_local const uint8_t *runtime_vs_package, *runtime_ps_package;
static _Thread_local unsigned runtime_vs_package_len, runtime_ps_package_len;
static _Thread_local uint32_t runtime_primitive_type;
static atomic_uint locks;
static int tracked_lock(pthread_mutex_t *m) {
 atomic_fetch_add(&locks,1); return pthread_mutex_lock(m);
}
#define pthread_mutex_lock tracked_lock
''' + structure + r'''
static struct runtime_shader_pair *runtime_shader_pair_get_unlocked(
 const agc_api_t *agc, int64_t direct_limit,
 const uint8_t *a,size_t b,const uint8_t *d,size_t e,
 const uint8_t *f,size_t g,const uint8_t *h,size_t i) {
 (void)direct_limit;(void)a;(void)b;(void)d;(void)e;(void)f;(void)g;(void)h;(void)i;
''' + lookup + r'''
 assert(!agc); return NULL; /* Allocation is not needed for this lookup fixture. */
}
''' + wrapper + r'''
static struct runtime_shader_pair *get(void) {
 return runtime_shader_pair_get(NULL,0,NULL,0,NULL,0,NULL,0,NULL,0);
}
static void *worker(void *arg) {
 unsigned n=(unsigned)(uintptr_t)arg;
 struct runtime_shader_pair *p=&runtime_shader_pairs[n];
 uint8_t *vs=(uint8_t *)p->vs_key, *ps=(uint8_t *)p->ps_key;
 runtime_vs_package=vs;runtime_ps_package=ps;
 runtime_vs_package_len=p->vs_size;runtime_ps_package_len=p->ps_size;
 runtime_primitive_type=p->primitive;
 assert(!runtime_shader_pair_last && get()==p);
 for(unsigned i=0;i<50000;i++) assert(get()==p);
 /* A hot TLS pointer must still detect in-place edits and reused addresses. */
 vs[91]^=1;assert(!get());vs[91]^=1;assert(get()==p);
 ps[337]^=1;assert(!get());ps[337]^=1;assert(get()==p);
 runtime_primitive_type++;assert(!get());runtime_primitive_type--;assert(get()==p);
 runtime_vs_package_len--;assert(!get());runtime_vs_package_len++;assert(get()==p);
 runtime_ps_package_len--;assert(!get());runtime_ps_package_len++;assert(get()==p);
 uint8_t copy[1024];memcpy(copy,vs,1024);
 runtime_vs_package=copy;assert(!get());runtime_vs_package=vs;assert(get()==p);
 for(unsigned i=0;i<50000;i++) assert(get()==p);
 return NULL;
}
int main(void) {
 uint8_t bytes[2][2048];
 for(unsigned n=0;n<2;n++) {
  for(unsigned i=0;i<2048;i++)bytes[n][i]=(uint8_t)(i*7+n);
  struct runtime_shader_pair *p=&runtime_shader_pairs[n];
  *p=(struct runtime_shader_pair){.vs_key=bytes[n],.ps_key=bytes[n]+1024,
      .vs_size=1024,.ps_size=1024,.primitive=4+n};
  p->source=malloc(2048);assert(p->source);memcpy(p->source,bytes[n],2048);
 }
 runtime_shader_pair_count=2;
 pthread_t threads[2];
 for(unsigned n=0;n<2;n++)assert(!pthread_create(&threads[n],NULL,worker,(void *)(uintptr_t)n));
 for(unsigned n=0;n<2;n++)assert(!pthread_join(threads[n],NULL));
 unsigned acquired=atomic_load(&locks);
 assert(acquired==26); /* Warmups and twelve changed/restored cases per worker. */
 assert(runtime_pair_lookups==26 && !runtime_shader_pair_last);
 for(unsigned n=0;n<2;n++)free(runtime_shader_pairs[n].source);
 printf("PASS: 200000 concurrent byte-verified hits bypass shared lock; %u cold/mutation lookups retain mutex; topology, sizes, bytes, reused keys and thread ownership checked\n",acquired);
}
'''
with tempfile.TemporaryDirectory(prefix='prosperomc-worker-cache-') as tmp:
    path = Path(tmp)
    (path / 'check.c').write_text(c)
    subprocess.run(['clang-18', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-pthread',
                    str(path / 'check.c'), '-o', str(path / 'check')], check=True)
    subprocess.run([str(path / 'check')], check=True)
