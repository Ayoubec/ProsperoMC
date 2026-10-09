"""Run the real empty-cache retirement gate with ready and in-flight batches."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
s = (root / 'artifacts/graphics-batching/ps5_screen.c').read_text()
draw_start = s.index('static bool\nps5_try_deferred_draw(')
start = s.index('   if (ps5_inflight_count &&', draw_start)
end = s.index('   if (!ps5_batch_copy_descriptors(', start)
gate = s[start:end]
assert s.index('simple_mtx_lock(&ps5_deferred_mutex);', draw_start) < start
start = s.index('static void\nps5_draw_batch_retire_locked(bool wait)\n{')
end = s.index('\n}', start) + 2
retire = s[start:end]
c = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
struct ps5_context {unsigned descriptor_cache_count[3];};
static unsigned ps5_inflight_count, polls, releases, creates;
static bool ready;
static struct ps5_context *owner;
static bool ps5_draw_batch_retire_one_locked(bool wait) {
 assert(!wait); /* This gate must never block or submit the queued draw. */
 ++polls;
 if (!ps5_inflight_count || !ready) return false;
 --ps5_inflight_count; ++releases;
 for(unsigned i=0;i<3;i++)owner->descriptor_cache_count[i]+=256;
 return true;
}
''' + retire + r'''
static void copy(struct ps5_context *context) {
 owner=context;
''' + gate + r'''
 for(unsigned i=0;i<3;i++) {
  if(context->descriptor_cache_count[i]) --context->descriptor_cache_count[i];
  else ++creates;
 }
}
int main(void) {
 struct ps5_context ctx={0};
 ready=true;ps5_inflight_count=1;copy(&ctx);
 assert(releases==1 && !creates && !ps5_inflight_count);
 for(unsigned i=0;i<3;i++)assert(ctx.descriptor_cache_count[i]==255);
 unsigned previous=polls;ps5_inflight_count=1;copy(&ctx);
 assert(polls==previous && ps5_inflight_count==1); /* Nonempty caches do no poll. */
 for(unsigned i=0;i<3;i++)ctx.descriptor_cache_count[i]=0;
 ready=false;copy(&ctx);
 assert(releases==1 && creates==3 && ps5_inflight_count==1);
 ready=true;copy(&ctx);
 assert(releases==2 && creates==3 && !ps5_inflight_count);
 /* Exhaust just one stage: the same ready FIFO supplies the missing stage. */
 ctx.descriptor_cache_count[1]=0;ps5_inflight_count=1;copy(&ctx);
 assert(releases==3 && creates==3);
 for(unsigned i=0;i<3;i++)ctx.descriptor_cache_count[i]=0;
 previous=polls;copy(&ctx);
 assert(polls==previous && creates==6); /* No submitted work: allocate normally. */
 puts("PASS: actual deferred gate reclaims ready FIFO before allocation, never waits; unretired resources stay owned, nonempty/no-inflight paths do not poll");
}
'''
with tempfile.TemporaryDirectory(prefix='prosperomc-ready-descriptors-') as tmp:
    path = Path(tmp)
    (path / 'check.c').write_text(c)
    subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    str(path / 'check.c'), '-o', str(path / 'check')], check=True)
    subprocess.run([str(path / 'check')], check=True)
