"""Check the actual routing block with Mesa's pinned multi-draw dispatcher."""
from pathlib import Path
import hashlib
import tarfile

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts/graphics-batching'
source = (out / 'ps5_screen.c').read_text()
route = source.split('   /* Keep eligible multi-draw groups in the existing deferred queue. */\n', 1)[1]
route = route.split('\n   if ((!context->legacy_primitive_conversion', 1)[0]
archive = root / '.deps/archives/mesa-26.2.0.tar.xz'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'efd4bb08cdb7c365a812cd4e6c9202ab55b2f22cdcd13c7d6c4f9647b799a4ef'
with tarfile.open(archive) as tar:
    member = next(m for m in tar.getmembers() if m.name.endswith('/src/gallium/auxiliary/util/u_draw.c'))
    mesa = tar.extractfile(member).read().decode()
dispatcher = 'void\n'+mesa[mesa.index('util_draw_multi('):].split('\n}', 1)[0]+'\n}'

test = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
struct pipe_draw_info {unsigned instance_count;bool increment_draw_id;};
struct pipe_draw_indirect_info {int unused;};
struct pipe_draw_start_count_bias {unsigned start,count;};
struct pipe_context {
 void (*draw_vbo)(struct pipe_context *,const struct pipe_draw_info *,unsigned,
                 const struct pipe_draw_indirect_info *,const struct pipe_draw_start_count_bias *,unsigned);
};
struct ps5_context {bool legacy_primitive_conversion,legacy_batch_quads,eligible;};
static unsigned ids[8],starts[8],calls,fallbacks;
static bool ps5_multidraw_eligible(struct ps5_context *context,const struct pipe_draw_info *info,
 const struct pipe_draw_indirect_info *indirect,const struct pipe_draw_start_count_bias *draws,unsigned n){
 assert(info&&draws&&n>1&&!indirect);return context->eligible;
}
static void enqueue(struct pipe_context *base,const struct pipe_draw_info *info,unsigned id,
 const struct pipe_draw_indirect_info *indirect,const struct pipe_draw_start_count_bias *draw,unsigned n){
 (void)base;assert(info&&draw&&n==1&&!indirect&&calls<8);
 ids[calls]=id;starts[calls++]=draw->start;
}
'''+dispatcher+r'''
static void route_group(struct pipe_context *base,struct ps5_context *context,const struct pipe_draw_info *info,
 unsigned drawid_offset,const struct pipe_draw_indirect_info *indirect,
 const struct pipe_draw_start_count_bias *draws,unsigned num_draws){
'''+route+r'''
 fallbacks++;
}
int main(void){
 struct pipe_context base={enqueue};struct ps5_context context={.eligible=true};
 struct pipe_draw_info info={1,true};
 struct pipe_draw_start_count_bias draws[3]={{3,4},{8,0},{12,6}};
 route_group(&base,&context,&info,7,NULL,draws,3);
 assert(calls==2&&!fallbacks&&ids[0]==7&&ids[1]==9&&starts[0]==3&&starts[1]==12);
 calls=0;info.increment_draw_id=false;route_group(&base,&context,&info,7,NULL,draws,3);
 assert(calls==2&&ids[0]==7&&ids[1]==7&&!fallbacks);
 calls=0;context.eligible=false;route_group(&base,&context,&info,0,NULL,draws,3);
 assert(!calls&&fallbacks==1);context.eligible=true;
 context.legacy_primitive_conversion=true;route_group(&base,&context,&info,0,NULL,draws,3);
 assert(!calls&&fallbacks==2);context.legacy_batch_quads=true;
 route_group(&base,&context,&info,0,NULL,draws,3);assert(calls==2&&fallbacks==2);
 calls=0;context.legacy_primitive_conversion=false;
 struct pipe_draw_indirect_info indirect={0};
 route_group(&base,&context,&info,0,&indirect,draws,3);
 route_group(&base,&context,NULL,0,NULL,draws,3);
 route_group(&base,&context,&info,0,NULL,NULL,3);
 route_group(&base,&context,&info,0,NULL,draws,1);
 assert(!calls&&fallbacks==6);
 info.instance_count=0;route_group(&base,&context,&info,0,NULL,draws,3);
 assert(!calls&&fallbacks==6);
 puts("PASS: eligible groups dispatch to single deferred draws with correct draw IDs, zero-count handling and legacy/indirect/input fallback guards");
}
'''
(out / 'check-deferred-multidraw.c').write_text(test)
print(out / 'check-deferred-multidraw.c')
