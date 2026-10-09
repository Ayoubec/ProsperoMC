"""Exercise the generated driver's actual synchronous descriptor cleanup."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'artifacts/graphics-batching/ps5_screen.c').read_text()
start = source.index('static void\nps5_descriptor_recycle(')
end = source.index('\nstatic void', start + 1)
recycle = source[start:end]
start = source.index('release:\n', source.index('static bool\nps5_try_multi_draw_batch('))
end = source.index('   return handled;', start)
cleanup = source[start:end].replace('release:\n', '')
c = '''#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#define PS5_NATIVE_TITLE_RUNTIME 1
#define PS5_DEFERRED_DRAW_BATCH 1
#define PS5_MULTIDRAW_BATCH_CAPACITY 4
#define PS5_DIRECT_ALIGNMENT 0x4000
#define PIPE_BUFFER 0
struct pipe_resource {struct {int count;} reference; int target; unsigned width0;};
struct ps5_context {struct pipe_resource *descriptor_cache[3][4]; unsigned descriptor_cache_count[3];};
static unsigned freed;
static void pipe_resource_reference(struct pipe_resource **r, void *unused) {
 (void)unused; if (*r) {freed++; *r=NULL;}
}
''' + recycle + '''
static void release_resources(struct ps5_context *context, bool retired,
 unsigned slots, struct pipe_resource *storage[4][3],
 unsigned retained_count, struct pipe_resource **retained) {
''' + cleanup + '''}
int main(void) {
 struct ps5_context ctx={0}; struct pipe_resource r[3]={{{1},0,0x4000},{{1},0,0x4000},{{1},0,0x4000}};
 struct pipe_resource *storage[4][3]={{&r[0],&r[1],&r[2]}};
 struct pipe_resource *retained[1]={NULL};
 release_resources(&ctx,false,1,storage,0,retained);
 assert(!freed && storage[0][0] && !ctx.descriptor_cache_count[0]);
 release_resources(&ctx,true,1,storage,0,retained);
 assert(!freed && !storage[0][0] && ctx.descriptor_cache_count[0]==1);
 assert(ctx.descriptor_cache[0][0]==&r[0]);
 r[0].reference.count=2; r[1].width0=0x8000; ctx.descriptor_cache_count[2]=4;
 for(unsigned i=0;i<3;i++)storage[0][i]=&r[i];
 release_resources(&ctx,true,1,storage,0,retained);
 assert(freed==3 && ctx.descriptor_cache_count[0]==1 && ctx.descriptor_cache_count[2]==4);
 puts("PASS: actual cleanup recycles only retired private descriptors; shared, oversized, full-cache and unretired resources retain conservative handling");
}
'''
with tempfile.TemporaryDirectory(prefix='prosperomc-descriptors-') as tmp:
    path = Path(tmp)
    (path / 'check.c').write_text(c)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(path/'check.c'),'-o',str(path/'check')],check=True)
    subprocess.run([str(path/'check')],check=True)
