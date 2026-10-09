"""Prepare a conservative smooth-quad batching patch against verified CI source."""
from pathlib import Path
import difflib
import hashlib
import json
import tarfile

root = Path(__file__).resolve().parent.parent
sdk = root / '.deps/graphics-sdk-ci-738f94c/extracted'
out = root / 'artifacts/graphics-batching'
out.mkdir(parents=True, exist_ok=True)
provenance = json.loads((sdk / 'provenance.json').read_text())
snapshot = sdk / 'sources/ps5-opengl.tar'
assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == provenance['source_archives']['ps5-opengl.tar']
with tarfile.open(snapshot) as archive:
    entry = next(m for m in archive.getmembers() if m.name.endswith('/src/gallium/ps5/ps5_screen.c'))
    before = archive.extractfile(entry).read().decode()

# Mesa's gathered interpolation masks distinguish smooth inputs from explicit
# flat inputs. Unknown information always keeps the original correctness path.
helper = '''static bool
ps5_legacy_requires_split(bool flatshade, bool known_interpolation,
                          uint64_t inputs, uint64_t perspective,
                          uint64_t linear)
{
   return flatshade || !known_interpolation ||
          (inputs & ~(perspective | linear)) != 0;
}

'''
anchor = '''static void
ps5_draw_vbo(struct pipe_context *base, const struct pipe_draw_info *info,
             unsigned drawid_offset,
             const struct pipe_draw_indirect_info *indirect,
             const struct pipe_draw_start_count_bias *draws,
             unsigned num_draws)
{'''
assert before.count(anchor) == 1
after = before.replace(anchor, helper + anchor)
anchor = '''      struct primconvert_config cfg = {
         .primtypes_mask = base->screen->caps.supported_prim_modes &'''
assert after.count(anchor) == 1
after = after.replace(anchor, '''      const shader_info *fs = context->fs ? &context->fs->nir->info : NULL;
      const bool split = !fs || !context->rasterizer || context->gs ||
         context->stream_output_target_count || context->active_occlusion_query ||
         ps5_legacy_requires_split(context->rasterizer->flatshade,
            fs->known_interpolation_qualifiers, fs->inputs_read,
            fs->perspective_varyings, fs->linear_varyings);
      struct primconvert_config cfg = {
         .primtypes_mask = base->screen->caps.supported_prim_modes &''')
assert after.count('.split_legacy_triangles = true,') == 1
after = after.replace('.split_legacy_triangles = true,', '.split_legacy_triangles = split,')
assert after.count('context->legacy_primitive_conversion = true;') == 1
after = after.replace('context->legacy_primitive_conversion = true;', '''/* Smooth inputs need no per-triangle provoking-vertex override.
       * Keep their converted index buffer in one draw and allow batching. */
      context->legacy_primitive_conversion = split;''')
(out / 'ps5_screen.c').write_bytes(after.encode())
patch = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
    fromfile='a/src/gallium/ps5/ps5_screen.c', tofile='b/src/gallium/ps5/ps5_screen.c'))
(out / 'smooth-legacy-batching.patch').write_bytes(patch.encode())
(out / 'check-policy.c').write_text('''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
''' + helper + '''int main(void) {
    assert(!ps5_legacy_requires_split(false,true,9,9,0));
    assert(!ps5_legacy_requires_split(false,true,9,1,8));
    assert(!ps5_legacy_requires_split(false,true,0,0,0));
    assert(ps5_legacy_requires_split(true,true,9,9,0));
    assert(ps5_legacy_requires_split(false,false,9,9,0));
    assert(ps5_legacy_requires_split(false,true,9,1,0));
    puts("PASS: smooth perspective/linear/constant shaders batch; flat shading, explicit flat inputs and unknown interpolation preserve splitting");
}
''')
print('PREPARED_SMOOTH_BATCHING_PATCH', hashlib.sha256(patch.encode()).hexdigest())
