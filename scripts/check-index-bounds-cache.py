"""Check the actual driver's index validation and cache against changing bytes."""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'artifacts/graphics-batching/ps5_screen.c').read_text()
value = re.search(r'static uint32_t\nps5_index_value\(.*?\n\}', source, re.S).group()
bounds = re.search(r'static bool\nps5_index_bounds\(.*?\n\}', source, re.S).group()
cache = (root / 'scripts/graphics-index-bounds-cache.c').read_text()
marker = '/* Index bounds helpers; require ps5_resource. */'
types, helper = cache.split(marker, 1)
assert helper in source
assert source.count('written->index_bounds_gpu_writable = true;') == 3
assert source.count('memset(&buffer->index_bounds_cache') == 2
assert 'if (!read_owned) {\n      resource->buffer_published = false;\n      memset(&resource->index_bounds_cache' in source
assert 'memset(&resource->index_bounds_cache, 0, sizeof(resource->index_bounds_cache));\n   resource->gpu_written = false;' in source
assert '(info->index_size && info->index_size != 2 && info->index_size != 4)' in source
c = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#define MIN2(a,b) ((a)<(b)?(a):(b))
#define MAX2(a,b) ((a)>(b)?(a):(b))
struct cpu_caps {bool has_sse4_1;};
static struct cpu_caps caps;
static struct cpu_caps *util_get_cpu_caps(void) {return &caps;}
static void _mesa_uint_array_min_max(const uint32_t *values,unsigned *minimum,unsigned *maximum,unsigned count) {
 *minimum=UINT_MAX;*maximum=0;
 for(unsigned i=0;i<count;i++){*minimum=MIN2(*minimum,values[i]);*maximum=MAX2(*maximum,values[i]);}
}
static unsigned scans;
''' + value + bounds.replace('ps5_index_bounds(', 'original_bounds(', 1) + r'''
static bool ps5_index_bounds(const void *indices,unsigned size,unsigned count,int bias,unsigned *lo,unsigned *hi,unsigned *elo,unsigned *ehi) {
 ++scans;return original_bounds(indices,size,count,bias,lo,hi,elo,ehi);
}
''' + types + r'''
struct ps5_resource {uint8_t *data;size_t size;bool external_cpu_access,gpu_written,index_bounds_gpu_writable;struct ps5_index_bounds_cache index_bounds_cache;struct ps5_index_bounds_metrics index_bounds_metrics;};
''' + marker + helper + r'''
static void check(struct ps5_resource *r,size_t offset,unsigned size,unsigned count,int bias) {
 unsigned a[4]={0},b[4]={0};
 bool expected=original_bounds(r->data+offset,size,count,bias,a,a+1,a+2,a+3);
 bool actual=ps5_cached_index_bounds(r,offset,size,count,bias,b,b+1,b+2,b+3);
 assert(expected==actual);if(actual)assert(!memcmp(a,b,sizeof(a)));
}
int main(void) {
 uint32_t values[32]={0,1,2,3,100,UINT_MAX-3,UINT_MAX-2,7};
 struct ps5_resource r={.data=(uint8_t *)values,.size=sizeof(values)};
 check(&r,0,4,5,0);assert(scans==1);
 for(unsigned n=0;n<10000;n++)check(&r,0,4,5,0);
 assert(scans==1); /* Every repeated draw preserves complete validation. */
 check(&r,4,4,4,0);assert(scans==2); /* distinct offsets */
 check(&r,0,4,4,0);assert(scans==3); /* distinct counts */
 check(&r,0,4,5,2);assert(scans==3); /* same bytes, different base vertex */
 for(unsigned n=0;n<10000;n++)check(&r,0,4,5,(int)(n%8192));
 assert(scans==3); /* Terrain chunk base vertices reuse the validated raw range. */
 check(&r,0,4,5,-1);check(&r,0,4,7,8); /* negative rejection and uint32 wrap */
 memset(&r.index_bounds_cache,0,sizeof(r.index_bounds_cache));values[4]=200;
 check(&r,0,4,5,0); /* synchronized and unsynchronized writes clear entries */
 r.external_cpu_access=true;unsigned before=scans;
 values[4]=201;check(&r,0,4,5,0);values[4]=202;check(&r,0,4,5,0);
 assert(scans==before+2);
 r.external_cpu_access=false;r.gpu_written=true;before=scans;
 values[4]=203;check(&r,0,4,5,0);assert(scans==before+1);
 memset(&r.index_bounds_cache,0,sizeof(r.index_bounds_cache));r.gpu_written=false;
 r.index_bounds_gpu_writable=true;before=scans;
 values[4]=204;check(&r,0,4,5,0);values[4]=205;check(&r,0,4,5,0);
 assert(scans==before+2); /* Synchronous storage/feedback writes bypass reuse. */
 r.index_bounds_gpu_writable=false;
 check(&r,0,4,5,0);check(&r,0,2,10,0); /* 16-bit and 32-bit ranges differ */
 memset(&r.index_bounds_cache,0,sizeof(r.index_bounds_cache));
 values[0]=2;values[1]=UINT_MAX-2;values[2]=UINT_MAX;
 check(&r,0,4,3,1);check(&r,0,4,3,2);check(&r,0,4,3,0);
 check(&r,0,4,3,INT_MAX);check(&r,0,4,3,INT_MIN); /* cached mixed wrap and overflow rejection */
 memset(&r.index_bounds_cache,0,sizeof(r.index_bounds_cache));
 values[0]=UINT_MAX-3;values[1]=UINT_MAX-2;values[2]=UINT_MAX-1;
 check(&r,0,4,3,8);check(&r,0,4,3,9);check(&r,0,4,3,-1); /* whole range wraps monotonically */
 unsigned state=42;
 for(unsigned iteration=0;iteration<4000;iteration++) {
  memset(&r.index_bounds_cache,0,sizeof(r.index_bounds_cache));
  for(unsigned i=0;i<32;i++){state=state*1664525u+1013904223u;values[i]=state;}
  caps.has_sse4_1=iteration%2;
  for(unsigned size=2;size<=4;size+=2)for(int bias=-3;bias<=3;bias++) {
   check(&r,size,size,12,bias);check(&r,size,size,12,bias);
  }
 }
 /* Actual Sodium 0.9.1 INTEGER pattern, with varied counts/base vertices.
  * The eight-entry exact-range cache cannot cover these 10,000 draw sizes. */
 uint32_t quads[60006];
 const unsigned pattern[6]={0,1,2,2,3,0};
 for(unsigned i=0;i<60006;i++)quads[i]=(i/6)*4+pattern[i%6];
 struct ps5_resource q={.data=(uint8_t *)quads,.size=sizeof(quads)};
 for(unsigned n=0;n<10000;n++)check(&q,0,4,6*(n+1),(int)(n%8192));
 assert(q.index_bounds_metrics.scans==0);
 assert(q.index_bounds_metrics.quad_hits==10000);
 assert(q.index_bounds_metrics.quad_validated==60000);
 struct ps5_resource exact={.data=(uint8_t *)quads,.size=sizeof(quads)};
 exact.index_bounds_cache.quads[0].rejected=exact.index_bounds_cache.quads[1].rejected=true;
 for(unsigned n=0;n<10000;n++)check(&exact,0,4,6*(n+1),(int)(n%8192));
 assert(exact.index_bounds_metrics.scans==10000);
 assert(exact.index_bounds_metrics.scanned_indices==UINT64_C(300030000));
 for(unsigned phase=0;phase<6;phase++)for(unsigned count=1;count<19;count++)
  for(int bias=-3;bias<=3;bias++)check(&q,4*(phase+11),4,count,bias);
 check(&q,0,4,0,0);
 /* Both supported widths, arbitrary recognized permutations and partial
  * groups: no assumption about the order of a quad's triangles. */
 uint16_t short_quads[60006];
 unsigned shuffled[6]={0,1,2,2,3,0};
 for(unsigned iteration=0;iteration<12;iteration++) {
  unsigned tmp=shuffled[iteration%6];shuffled[iteration%6]=shuffled[(iteration+3)%6];shuffled[(iteration+3)%6]=tmp;
  for(unsigned i=0;i<60006;i++){quads[i]=(i/6)*4+shuffled[i%6];short_quads[i]=(uint16_t)quads[i];}
  for(unsigned size=2;size<=4;size+=2) {
   struct ps5_resource t={.data=size==2?(uint8_t *)short_quads:(uint8_t *)quads,
                         .size=size==2?sizeof(short_quads):sizeof(quads)};
   for(unsigned n=0;n<1200;n++) {
    state=state*1664525u+1013904223u;
    unsigned start=state%1024,count=1+(state>>10)%3000;
    check(&t,size*start,size,count,(int)(n%17)-8);
   }
   assert(t.index_bounds_metrics.scans==0);
  }
 }
 /* A mismatching tail (including 16-bit wrap) must use the original scan. */
 memset(&q.index_bounds_cache,0,sizeof(q.index_bounds_cache));
 check(&q,0,4,6,0);quads[37]=99;check(&q,0,4,42,0);
 assert(q.index_bounds_cache.quads[1].rejected);
 unsigned saved_scans=scans;check(&q,0,4,48,0);assert(scans==saved_scans+1);
 memset(&q.index_bounds_cache,0,sizeof(q.index_bounds_cache));
 quads[0]=99;check(&q,0,4,60,0);assert(q.index_bounds_cache.quads[1].rejected);
 uint16_t wrapped[98310];
 for(unsigned i=0;i<98310;i++)wrapped[i]=(uint16_t)((i/6)*4+pattern[i%6]);
 struct ps5_resource w={.data=(uint8_t *)wrapped,.size=sizeof(wrapped)};
 check(&w,0,2,98310,0);assert(w.index_bounds_cache.quads[0].rejected);
 /* Reset after a write enables recognition again; independent metrics must
  * survive invalidations. Exported and GPU-written bytes are never reused. */
 for(unsigned i=0;i<60006;i++)quads[i]=(i/6)*4+pattern[i%6];
 memset(&q.index_bounds_cache,0,sizeof(q.index_bounds_cache));
 check(&q,0,4,600,0);uint64_t hits=q.index_bounds_metrics.quad_hits;
 q.external_cpu_access=true;quads[50]=200;check(&q,0,4,600,0);
 assert(q.index_bounds_metrics.quad_hits==hits);
 q.external_cpu_access=false;q.gpu_written=true;check(&q,0,4,600,0);
 q.gpu_written=false;q.index_bounds_gpu_writable=true;check(&q,0,4,600,0);
 assert(q.index_bounds_metrics.quad_hits==hits && q.index_bounds_metrics.bypass==3);
 q.index_bounds_gpu_writable=false;quads[50]=(50/6)*4+pattern[50%6];
 memset(&q.index_bounds_cache,0,sizeof(q.index_bounds_cache));
 check(&q,0,4,600,0);assert(q.index_bounds_metrics.quad_hits==hits+1);
 puts("INDEX_BOUNDS_CACHE_PASS: 10000 changing chunk base vertices without rescan; mutations, export/GPU bypass, offsets, supported 16/32-bit types, negative/extreme bias, mixed/whole wrap and 112000 randomized comparisons");
 puts("QUAD_PREFIX_PASS: 10000 distinct draw sizes validate 60000 indices once versus 300030000 elements in exact-range-only mode; 28800 permutation/width comparisons, partial groups, corrupt tails, 16-bit wrap and write/export/GPU guards");
}
'''
with tempfile.TemporaryDirectory(prefix='prosperomc-index-cache-') as folder:
    folder=Path(folder);file=folder/'check.c';file.write_text(c);binary=folder/'check'
    subprocess.run(['clang-18','-std=c11','-O2','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-fno-sanitize-recover=all',str(file),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
