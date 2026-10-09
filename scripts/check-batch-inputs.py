"""Exercise the driver's actual input predicate for lowered and indexed draws."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts/graphics-batching'
source = (out / 'ps5_screen.c').read_text()
body = source[source.index('ps5_multidraw_eligible('):]
condition = body[body.index('   if ('):body.index('\n   {')].strip()
assert 'info->index_size && info->has_user_indices' in condition
assert 'info && draws && num_draws && context->batch_reject' in body

test = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#define MESA_PRIM_TRIANGLES 4
#define MESA_PRIM_TRIANGLE_FAN 6
struct blitter {bool running;};
struct ps5_context {bool deferred_blitter_draw;struct blitter *blitter;};
struct pipe_draw_info {
 unsigned mode,index_size,instance_count,start_instance;
 bool primitive_restart,has_user_indices;
 union {void *resource;void *user;} index;
};
struct pipe_draw_start_count_bias {unsigned start,count;};
static bool rejected(struct ps5_context *context,const struct pipe_draw_info *info,
 const void *indirect,const struct pipe_draw_start_count_bias *draws,unsigned num_draws) {
'''+condition+r'''
  return true;
 return false;
}
int main(void) {
 struct ps5_context context={0};
 struct pipe_draw_info info={.mode=MESA_PRIM_TRIANGLES,.instance_count=1};
 struct pipe_draw_start_count_bias draw={0,12};
 assert(!rejected(&context,&info,NULL,&draw,1));
 info.has_user_indices=true; /* Mesa can retain this after lowering to vertices. */
 assert(!rejected(&context,&info,NULL,&draw,1));
 info.index_size=2;info.index.user=&draw;
 assert(rejected(&context,&info,NULL,&draw,1)); /* Real client indices still fall back. */
 info.has_user_indices=false;
 assert(!rejected(&context,&info,NULL,&draw,1));
 info.index_size=4;assert(!rejected(&context,&info,NULL,&draw,1));
 info.index_size=1;assert(rejected(&context,&info,NULL,&draw,1));
 info.index_size=2;info.index.resource=NULL;
 assert(rejected(&context,&info,NULL,&draw,1));
 info.index_size=0;info.primitive_restart=true;
 assert(rejected(&context,&info,NULL,&draw,1));info.primitive_restart=false;
 assert(rejected(&context,&info,&draw,&draw,1));
 assert(rejected(&context,NULL,NULL,&draw,1));
 assert(rejected(&context,&info,NULL,NULL,1));
 assert(rejected(&context,&info,NULL,NULL,0));
 info.instance_count=0;assert(rejected(&context,&info,NULL,&draw,1));info.instance_count=1;
 info.mode=MESA_PRIM_TRIANGLE_FAN;draw.count=4;
 assert(rejected(&context,&info,NULL,&draw,1));
 struct blitter blitter={true};context.blitter=&blitter;context.deferred_blitter_draw=true;
 assert(!rejected(&context,&info,NULL,&draw,1));
 draw.count=5;assert(rejected(&context,&info,NULL,&draw,1));draw.count=4;
 draw.start=1;assert(rejected(&context,&info,NULL,&draw,1));draw.start=0;
 info.start_instance=1;assert(rejected(&context,&info,NULL,&draw,1));info.start_instance=0;
 assert(rejected(&context,&info,NULL,&draw,2));
 puts("PASS: lowered non-indexed draws batch; indexed client data, invalid input, indirect and unsupported fan draws retain guards");
}
'''
(out / 'check-batch-inputs.c').write_text(test)
print(out / 'check-batch-inputs.c')
