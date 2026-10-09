"""Exercise the exact driver's read-map decisions and buffer publication."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts/graphics-batching'
source = (out / 'ps5_screen.c').read_text()
def function(name, result):
    match = re.search(r'static '+result+r'\n'+name+r'\(.*?\n\}', source, re.S)
    assert match, name
    return match.group()

map_body = source[source.index('   const bool read_owned ='):]
map_body = map_body[:map_body.index('   transfer = calloc')]
unmap_body = source[source.index('   if (!ps5_read_owned_draw_buffer(resource, transfer->usage)'):]
unmap_body = unmap_body[:unmap_body.index('   if (ps5->staging')]
assert 'if (!read_owned && (usage & PIPE_MAP_READ)' in source
test = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#define PIPE_BUFFER 0
#define PIPE_BIND_VERTEX_BUFFER (1u << 4)
#define PIPE_BIND_INDEX_BUFFER (1u << 5)
#define PIPE_BIND_VERTEX_STATE (1u << 8)
#define PIPE_BIND_STREAM_OUTPUT (1u << 10)
#define PIPE_BIND_SHADER_BUFFER (1u << 14)
#define PIPE_MAP_READ 1
#define PIPE_MAP_WRITE 2
#define PIPE_MAP_UNSYNCHRONIZED (1u << 5)
#define PIPE_MAP_PERSISTENT (1u << 8)
#define PIPE_MAP_COHERENT (1u << 9)
struct pipe_resource {unsigned target,bind;};
struct ps5_resource {
 struct pipe_resource base;
 bool external_cpu_access,gpu_written,buffer_published;
 unsigned char *data;size_t allocation_size;
};
struct ps5_batch_flush_cache {int unused;};
struct pipe_transfer {unsigned usage;struct pipe_resource *resource;};
static unsigned drains,flushes;
static void ps5_draw_batch_drain_buffer(struct pipe_resource *r) {
 drains++;((struct ps5_resource*)r)->buffer_published=false;
 ((struct ps5_resource*)r)->gpu_written=false;
}
static void ps5_invalidate_gpu_writes(struct ps5_resource *r){r->gpu_written=false;}
static void ps5_flush_gpu_data(const void *p,size_t n){assert(p&&n);flushes++;}
static void ps5_flush_batch_backing(void *b,unsigned s,const void *p,size_t n){
 (void)b;(void)s;ps5_flush_gpu_data(p,n);
}
'''
test += function('ps5_read_owned_draw_buffer', 'bool')+'\n'
test += function('ps5_publish_draw_buffer', 'void')+'\n'
test += 'static void map_access(struct ps5_resource *resource,unsigned usage){\nstruct pipe_resource *base=&resource->base;\n'+map_body+'}\n'
test += 'static void unmap_access(struct ps5_resource *resource,unsigned usage){\nstruct pipe_transfer t={usage,&resource->base},*transfer=&t;\n'+unmap_body+'}\n'
test += r'''
int main(void) {
 unsigned char bytes[64]={0};
 struct ps5_resource r={.base={PIPE_BUFFER,PIPE_BIND_INDEX_BUFFER|PIPE_BIND_VERTEX_STATE},
 .data=bytes,.allocation_size=64};
 ps5_publish_draw_buffer(NULL,0,&r,0,64);assert(flushes==1);
 for(unsigned i=0;i<1000;i++) {
  map_access(&r,PIPE_MAP_READ);assert(r.buffer_published);
  unmap_access(&r,PIPE_MAP_READ);ps5_publish_draw_buffer(NULL,0,&r,0,64);
 }
 assert(!drains&&flushes==1); /* Repeated bounds reads preserve publication. */
 assert(!ps5_read_owned_draw_buffer(NULL,PIPE_MAP_READ));
 assert(!ps5_read_owned_draw_buffer(&r,PIPE_MAP_READ|PIPE_MAP_WRITE));
 assert(!ps5_read_owned_draw_buffer(&r,PIPE_MAP_READ|PIPE_MAP_PERSISTENT));
 assert(!ps5_read_owned_draw_buffer(&r,PIPE_MAP_READ|PIPE_MAP_COHERENT));
 map_access(&r,PIPE_MAP_WRITE);unmap_access(&r,PIPE_MAP_WRITE);
 assert(drains==2&&!r.buffer_published);
 ps5_publish_draw_buffer(NULL,0,&r,0,64);assert(flushes==2);
 r.gpu_written=true;assert(!ps5_read_owned_draw_buffer(&r,PIPE_MAP_READ));
 map_access(&r,PIPE_MAP_READ);assert(drains==3&&!r.buffer_published);
 r.external_cpu_access=true;map_access(&r,PIPE_MAP_READ);unmap_access(&r,PIPE_MAP_READ);
 assert(drains==5);r.external_cpu_access=false;
 r.base.bind|=PIPE_BIND_SHADER_BUFFER;assert(!ps5_read_owned_draw_buffer(&r,PIPE_MAP_READ));
 r.base.bind=PIPE_BIND_VERTEX_BUFFER|PIPE_BIND_STREAM_OUTPUT;
 assert(!ps5_read_owned_draw_buffer(&r,PIPE_MAP_READ));
 r.base.bind=0;assert(!ps5_read_owned_draw_buffer(&r,PIPE_MAP_READ));
 r.base.target=1;r.base.bind=PIPE_BIND_VERTEX_BUFFER;
 assert(!ps5_read_owned_draw_buffer(&r,PIPE_MAP_READ));
 puts("PASS: unchanged owned draw-buffer reads avoid drains/republishing; writes, exports, persistent maps, GPU writes and other binds retain synchronization");
}
'''
(out / 'check-readonly-maps.c').write_text(test)
print(out / 'check-readonly-maps.c')
