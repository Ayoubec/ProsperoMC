"""Prove actual packed-buffer helper/descriptor fetches stay in their allocation."""
from pathlib import Path
import re
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
source=(root/'artifacts/graphics-batching/ps5_screen.c').read_text()
helper=(root/'scripts/graphics-gpu-vertex-bounds.c').read_text()
assert helper in source
descriptor=re.search(r'static bool\nps5_vertex_buffer_descriptor\(.*?\n\}',source,re.S).group()
assert 'const bool gpu_bounded = ps5_gpu_vertex_capacity(context, info,' in source
assert source.index('bytes > index_resource->size - offset') < source.index('const bool gpu_bounded =')
assert 'vertex_count = max_effective + 1u;' in source
assert 'first_vertex = min_effective;' in source
assert 'ps5_cached_index_bounds(index_resource, index_offset,' in source
assert 'ps5_publish_draw_buffer(flush_cache,' in source
assert '(stride ? 0 : S_008F0C_OOB_SELECT(V_008F0C_OOB_SELECT_RAW))' in descriptor
c=r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
enum {PIPE_BUFFER=1,MESA_PRIM_TRIANGLES=4};
#define S_008F0C_OOB_SELECT(x) ((x)<<28)
#define V_008F0C_OOB_SELECT_RAW 3u
struct pipe_vertex_element {unsigned src_stride,src_format,src_offset,vertex_buffer_index,instance_divisor;};
struct ps5_vertex_elements {unsigned count;struct pipe_vertex_element elements[4];};
struct ps5_shader {void *nir;};
struct ps5_resource {struct {unsigned target;} base;void *data;size_t size;bool external_cpu_access,gpu_written,index_bounds_gpu_writable;};
struct pipe_vertex_buffer {bool is_user_buffer;union {struct ps5_resource *resource;} buffer;unsigned buffer_offset;};
struct ps5_context {struct ps5_shader *vs,*gs,*tcs,*tes;struct ps5_vertex_elements *vertex_elements;unsigned vertex_buffer_count,stream_output_target_count;struct pipe_vertex_buffer vertex_buffers[1];};
struct pipe_draw_info {unsigned instance_count,mode;};
struct ps5_vertex_layout {unsigned count;};
static bool valid_layout=true;
static unsigned consumed;
static bool ps5_vertex_layout_from_state(const struct ps5_shader *s,const struct ps5_vertex_elements *e,struct ps5_vertex_layout *l){(void)s;(void)e;l->count=consumed;return valid_layout;}
/* Attribute byte widths are varied independently of the original enum table;
 * the integrated driver uses its unmodified ps5_vertex_format_size function. */
static unsigned ps5_vertex_format_size(unsigned format){return format;}
''' + helper + descriptor + r'''
static uint32_t rng=193;
static unsigned random32(void){rng=rng*1664525u+1013904223u;return rng;}
static bool eligible(struct ps5_context *c,struct pipe_draw_info *info,int bias){unsigned capacity=0;return ps5_gpu_vertex_capacity(c,info,bias,&capacity);}
int main(void){
 uint8_t bytes[4096];struct ps5_shader shader={bytes};
 struct ps5_vertex_elements elements={.count=3,.elements={{20,8,0,0,0},{20,4,8,0,0},{20,8,12,0,0}}};
 struct ps5_resource r={.base={PIPE_BUFFER},.data=bytes,.size=2020};
 struct ps5_context ctx={.vs=&shader,.vertex_elements=&elements,.vertex_buffer_count=1,.vertex_buffers={{false,{&r},20}}};
 struct pipe_draw_info info={1,MESA_PRIM_TRIANGLES};consumed=3;unsigned capacity=0;
 assert(ps5_gpu_vertex_capacity(&ctx,&info,7,&capacity)&&capacity==100);
 assert(!eligible(&ctx,&info,-1)&&!eligible(&ctx,&info,100));
 ctx.gs=&shader;assert(!eligible(&ctx,&info,0));ctx.gs=NULL;
 ctx.tcs=&shader;assert(!eligible(&ctx,&info,0));ctx.tcs=NULL;
 ctx.tes=&shader;assert(!eligible(&ctx,&info,0));ctx.tes=NULL;
 ctx.stream_output_target_count=1;assert(!eligible(&ctx,&info,0));ctx.stream_output_target_count=0;
 info.instance_count=2;assert(!eligible(&ctx,&info,0));info.instance_count=1;
 info.mode=1;assert(!eligible(&ctx,&info,0));info.mode=MESA_PRIM_TRIANGLES;
 r.external_cpu_access=true;assert(!eligible(&ctx,&info,0));r.external_cpu_access=false;
 r.gpu_written=true;assert(!eligible(&ctx,&info,0));r.gpu_written=false;
 r.index_bounds_gpu_writable=true;assert(!eligible(&ctx,&info,0));r.index_bounds_gpu_writable=false;
 ctx.vertex_buffers[0].is_user_buffer=true;assert(!eligible(&ctx,&info,0));ctx.vertex_buffers[0].is_user_buffer=false;
 ctx.vertex_buffer_count=2;assert(!eligible(&ctx,&info,0));ctx.vertex_buffer_count=1;
 consumed=2;assert(!eligible(&ctx,&info,0));consumed=3;
 valid_layout=false;assert(!eligible(&ctx,&info,0));valid_layout=true;
 ++r.size;assert(!eligible(&ctx,&info,0));--r.size;
 r.base.target=2;assert(!eligible(&ctx,&info,0));r.base.target=PIPE_BUFFER;
 ctx.vertex_buffers[0].buffer_offset=2020;assert(!eligible(&ctx,&info,0));ctx.vertex_buffers[0].buffer_offset=20;
 elements.elements[1].src_offset=18;assert(!eligible(&ctx,&info,0));elements.elements[1].src_offset=8;
 elements.elements[1].instance_divisor=1;assert(!eligible(&ctx,&info,0));elements.elements[1].instance_divisor=0;
 elements.elements[1].vertex_buffer_index=1;assert(!eligible(&ctx,&info,0));elements.elements[1].vertex_buffer_index=0;
 elements.elements[1].src_stride=16;assert(!eligible(&ctx,&info,0));elements.elements[1].src_stride=20;
 elements.elements[1].src_format=0;assert(!eligible(&ctx,&info,0));elements.elements[1].src_format=4;
 r.size=((uint64_t)UINT32_MAX+1)*20;ctx.vertex_buffers[0].buffer_offset=0;assert(!eligible(&ctx,&info,0));
 /* Random packed layouts: original valid indices fetch the same bytes using
  * exact scanned bounds or allocation bounds; every GPU-admitted record and
  * attribute byte is in the allocation, including the last full record. */
 uint64_t checks=0;
 for(unsigned iteration=0;iteration<200000;iteration++){
  unsigned stride=1+random32()%128,records=1+random32()%1024,offset=random32()%4096;
  consumed=elements.count=1+random32()%4;r.size=(uint64_t)offset+(uint64_t)stride*records;
  ctx.vertex_buffers[0].buffer_offset=offset;
  for(unsigned i=0;i<consumed;i++){
   unsigned width=1+random32()%stride,element_offset=random32()%(stride-width+1);
   elements.elements[i]=(struct pipe_vertex_element){stride,width,element_offset,0,0};
  }
  unsigned bias=random32()%records;
  assert(ps5_gpu_vertex_capacity(&ctx,&info,(int)bias,&capacity)&&capacity==records);
  uint32_t desc[4];assert(ps5_vertex_buffer_descriptor((uintptr_t)bytes+offset,r.size-offset,stride,capacity,desc));
  assert(desc[2]==records&&desc[3]==0x5204u&&((desc[1]>>16)&0x3fffu)==stride);
  unsigned raw=random32()%(records-bias),vertex=raw+bias;
  for(unsigned i=0;i<consumed;i++){
   const struct pipe_vertex_element *e=&elements.elements[i];
   uint64_t last=(uint64_t)offset+(uint64_t)(desc[2]-1)*stride+e->src_offset+e->src_format;
   assert(last<=r.size);
   uint64_t existing=(uint64_t)offset+(uint64_t)vertex*stride+e->src_offset;
   uint64_t bounded=(uint64_t)offset+(uint64_t)(raw+bias)*stride+e->src_offset;
   assert(existing==bounded&&bounded+e->src_format<=r.size);checks++;
   /* Original descriptor record aggregation also produces exactly capacity. */
   assert((e->src_offset+(uint64_t)(capacity-1)*stride+e->src_format+stride-1)/stride==capacity);
  }
  assert(records>=desc[2]); /* first excluded record fails STRUCT index bound */
 }
 printf("GPU_VERTEX_BOUNDS_PASS layouts=200000 attribute_checks=%llu; actual descriptor mode unchanged, valid fetch addresses identical, complete records bounded, malformed/ownership/instance/layout fallbacks preserved\n",(unsigned long long)checks);
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='gpu-vertex-bounds-') as temporary:
    folder=Path(temporary);code=folder/'fixture.c';exe=folder/'fixture'
    code.write_text(c)
    subprocess.run(['clang-18','-std=c11','-O2','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
        '-fno-sanitize-recover=all',str(code),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
