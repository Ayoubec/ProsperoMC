"""Exercise the real driver's publication and CPU buffer-update functions."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts/graphics-batching'
source = (out / 'ps5_screen.c').read_text()
functions = []
for name in ('ps5_publish_draw_buffer', 'ps5_buffer_subdata'):
    match = re.search(r'static void\n' + name + r'\(.*?\n\}', source, re.S)
    assert match, name
    functions.append(match.group())
test = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define PIPE_BUFFER 0
#define PIPE_MAP_UNSYNCHRONIZED 1
struct pipe_resource { unsigned target; };
struct pipe_context { int unused; };
struct ps5_batch_flush_cache { int unused; };
struct ps5_resource {
    struct pipe_resource base;
    bool external_cpu_access, gpu_written, buffer_published;
    unsigned char *data; size_t size, allocation_size;
};
static unsigned flushes, drains; static size_t last_bytes;
static void ps5_flush_gpu_data(const void *p,size_t n) { assert(p);flushes++;last_bytes=n; }
static void ps5_flush_batch_backing(void *batch,unsigned slot,const void *p,size_t n) {
    (void)batch;(void)slot;ps5_flush_gpu_data(p,n);
}
static void ps5_draw_batch_drain_buffer(struct pipe_resource *p) {
    drains++;((struct ps5_resource *)p)->buffer_published=false;
}
static void ps5_invalidate_gpu_writes(struct ps5_resource *p) { p->gpu_written=false; }
'''
test += '\n'.join(functions)
test += r'''
int main(void) {
    unsigned char data[64]={0};
    struct ps5_resource r={.data=data,.size=64,.allocation_size=64};
    ps5_publish_draw_buffer(NULL,0,&r,4,8);
    assert(flushes==1 && last_bytes==64 && r.buffer_published);
    ps5_publish_draw_buffer(NULL,0,&r,32,16);
    assert(flushes==1); /* Full initial publication covers later draw ranges. */
    ps5_buffer_subdata(NULL,&r.base,0,4,4,"EDIT");
    assert(drains==1 && !memcmp(data+4,"EDIT",4) && !r.buffer_published);
    ps5_publish_draw_buffer(NULL,0,&r,4,4);assert(flushes==3);
    ps5_buffer_subdata(NULL,&r.base,PIPE_MAP_UNSYNCHRONIZED,12,4,"NEXT");
    assert(drains==1 && !r.buffer_published && !memcmp(data+12,"NEXT",4));
    ps5_publish_draw_buffer(NULL,0,&r,12,4);assert(flushes==5);
    r.external_cpu_access=true;
    ps5_publish_draw_buffer(NULL,0,&r,4,8);assert(flushes==6 && last_bytes==8);
    ps5_publish_draw_buffer(NULL,0,&r,4,8);assert(flushes==7);
    r.external_cpu_access=false;r.gpu_written=true;
    ps5_publish_draw_buffer(NULL,0,&r,4,8);assert(flushes==8);
    ps5_publish_draw_buffer(NULL,0,&r,4,8);assert(flushes==9);
    ps5_buffer_subdata(NULL,&r.base,0,63,4,"BAD!");assert(flushes==9);
    puts("PASS: static buffers publish once; CPU edits republish; persistent/GPU-written buffers keep per-use flushing");
    return 0;
}
'''
(out / 'check-buffer-publication.c').write_text(test)
print(out / 'check-buffer-publication.c')
