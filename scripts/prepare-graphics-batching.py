"""Batch legacy quads against verified CI source, preserving flat colors."""
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
after = after.replace('#include "indices/u_primconvert.h"',
    '#include "indices/u_primconvert.h"\n#include "indices/u_indices.h"')
after = after.replace('   bool legacy_primitive_conversion;',
    '   bool legacy_primitive_conversion;\n   bool legacy_batch_quads;\n'
    '   struct pipe_resource *quad_index_cache[2];\n'
    '   unsigned quad_index_vertices[2], quad_index_size[2];')
after = after.replace('   bool external_cpu_access;',
    '   bool external_cpu_access;\n   bool buffer_published;')
destroy = '   ps5_context_profile_report(context);\n   for (index = 0; index < PS5_COMPUTE_BUFFER_SLOTS; ++index)'
assert after.count(destroy) == 1
after = after.replace(destroy,
    '   for (unsigned q = 0; q < 2; ++q)\n'
    '      pipe_resource_reference(&context->quad_index_cache[q], NULL);\n' + destroy)
# Owned buffers cannot change without a driver write callback. Never cache
# raw-pointer/persistent mappings, GPU-written buffers or foreign aliases.
publication = '''static void
ps5_publish_draw_buffer(struct ps5_batch_flush_cache *batch, unsigned slot,
                        struct ps5_resource *buffer, size_t offset, size_t bytes)
{
   if (buffer->base.target != PIPE_BUFFER || buffer->external_cpu_access ||
       buffer->gpu_written) {
      ps5_flush_batch_backing(NULL, slot, buffer->data + offset, bytes);
      return;
   }
   if (!buffer->buffer_published) {
      ps5_flush_gpu_data(buffer->data, buffer->allocation_size);
      buffer->buffer_published = true;
   }
   (void)batch;
}

'''
after = after.replace('static void\nps5_flush_texture_backing(', publication + 'static void\nps5_flush_texture_backing(', 1)
old = '''         ps5_flush_batch_backing(
            vertex_resource->external_cpu_access ? NULL : flush_cache,
            2 + PS5_MAX_TEXTURE_UNITS + binding,
            (const void *)(vertex_address + binding_begin[binding]),
            binding_bytes[binding] - binding_begin[binding]);'''
assert after.count(old) == 1
after = after.replace(old, '''         ps5_publish_draw_buffer(flush_cache,
            2 + PS5_MAX_TEXTURE_UNITS + binding, vertex_resource,
            vertex_buffer->buffer_offset + binding_begin[binding],
            binding_bytes[binding] - binding_begin[binding]);''')
old = '''      ps5_flush_batch_backing(
         index_resource->external_cpu_access ? NULL : flush_cache,'''
assert after.count(old) == 1
old += '''
         2 + PS5_MAX_TEXTURE_UNITS + PIPE_MAX_ATTRIBS,
         index_resource->data + index_offset,
         (size_t)draws[0].count * info->index_size);'''
assert after.count(old) == 1
after = after.replace(old, '''      ps5_publish_draw_buffer(flush_cache,
         2 + PS5_MAX_TEXTURE_UNITS + PIPE_MAX_ATTRIBS, index_resource,
         index_offset, (size_t)draws[0].count * info->index_size);''')
after = after.replace('      buffer->texture_publication_epoch = 0;',
    '      buffer->buffer_published = false;\n      buffer->texture_publication_epoch = 0;', 1)
# UNSYNCHRONIZED CPU writes bypass drain, but must invalidate publication too.
for anchor in ('   transfer = calloc(1, sizeof(*transfer));',
               '   memcpy(buffer->data + offset, data, size);'):
    assert after.count(anchor) == 1
    var = 'resource' if 'transfer =' in anchor else 'buffer'
    after = after.replace(anchor, f'   {var}->buffer_published = false;\n' + anchor)
# CPU reads of owned vertex/index data do not conflict with queued GPU reads.
# Keep all GPU-write, exported, persistent and non-draw resources conservative.
read_helper = '''static bool
ps5_read_owned_draw_buffer(const struct ps5_resource *resource, unsigned usage)
{
   const unsigned draw_bind = PIPE_BIND_VERTEX_BUFFER | PIPE_BIND_INDEX_BUFFER;
   return resource && resource->base.target == PIPE_BUFFER &&
          (resource->base.bind & draw_bind) &&
          !(resource->base.bind & ~(draw_bind | PIPE_BIND_VERTEX_STATE)) &&
          !resource->external_cpu_access && !resource->gpu_written &&
          (usage & (PIPE_MAP_READ | PIPE_MAP_WRITE | PIPE_MAP_PERSISTENT |
                    PIPE_MAP_COHERENT)) == PIPE_MAP_READ;
}

'''
after = after.replace('static void *\nps5_transfer_map(', read_helper + 'static void *\nps5_transfer_map(', 1)
map_wait = '''   if (base->target != PIPE_BUFFER || (usage & PIPE_MAP_READ) ||
       !(usage & PIPE_MAP_UNSYNCHRONIZED))
      ps5_draw_batch_drain_buffer(base);
   else
      ps5_invalidate_gpu_writes(resource);'''
assert after.count(map_wait) == 1
after = after.replace(map_wait, '''   const bool read_owned = ps5_read_owned_draw_buffer(resource, usage);
   if (!read_owned) {
      if (base->target != PIPE_BUFFER || (usage & PIPE_MAP_READ) ||
          !(usage & PIPE_MAP_UNSYNCHRONIZED))
         ps5_draw_batch_drain_buffer(base);
      else
         ps5_invalidate_gpu_writes(resource);
   }''')
after = after.replace('   resource->buffer_published = false;\n   transfer = calloc',
                      '   if (!read_owned) resource->buffer_published = false;\n   transfer = calloc', 1)
after = after.replace('   if ((usage & PIPE_MAP_READ) && resource->base.target == PIPE_BUFFER)\n',
                      '   if (!read_owned && (usage & PIPE_MAP_READ) && resource->base.target == PIPE_BUFFER)\n', 1)
unmap_wait = '''   if (resource->base.target != PIPE_BUFFER || (transfer->usage & PIPE_MAP_READ) ||
       !(transfer->usage & PIPE_MAP_UNSYNCHRONIZED))
      ps5_draw_batch_drain_buffer(transfer->resource);'''
assert after.count(unmap_wait) == 1
after = after.replace(unmap_wait, '''   if (!ps5_read_owned_draw_buffer(resource, transfer->usage) &&
       (resource->base.target != PIPE_BUFFER || (transfer->usage & PIPE_MAP_READ) ||
        !(transfer->usage & PIPE_MAP_UNSYNCHRONIZED)))
      ps5_draw_batch_drain_buffer(transfer->resource);''')
quad_helper = (root / 'scripts/graphics-quad-batch.c').read_text()
after = after.replace('static bool\nps5_legacy_requires_split(',
    quad_helper + '\nstatic bool\nps5_legacy_requires_split(', 1)
draw_anchor = '''   if (info && (info->mode == MESA_PRIM_QUADS ||'''
assert after.count(draw_anchor) == 1
after = after.replace(draw_anchor, '''   if (ps5_draw_quads_batch(base, info, drawid_offset, indirect, draws, num_draws))
      return;

''' + draw_anchor)
after = after.replace('if (context->legacy_primitive_conversion && info && draws &&',
    'if (context->legacy_primitive_conversion && !context->legacy_batch_quads && info && draws &&')
after = after.replace('if (!context->legacy_primitive_conversion &&',
    'if ((!context->legacy_primitive_conversion || context->legacy_batch_quads) &&')
scan = '''      if (!ps5_index_bounds(indices, info->index_size, draws[0].count,
                            draws[0].index_bias, &min_index, &max_index,
                            &min_effective, &max_effective)) {'''
assert after.count(scan) == 1
after = after.replace(scan, '''      /* Our non-indexed quad generator already gives exact bounds. External
       * indexed data retains the complete validation scan. */
      if (context->legacy_batch_quads && info->index_bounds_valid &&
          draws[0].index_bias == 0 && info->min_index <= info->max_index &&
          info->max_index < UINT_MAX) {
         min_index = min_effective = info->min_index;
         max_index = max_effective = info->max_index;
      } else if (!ps5_index_bounds(indices, info->index_size, draws[0].count,
                                  draws[0].index_bias, &min_index, &max_index,
                                  &min_effective, &max_effective)) {''')
# Mirror the already-correct single-draw check: stale client-index flags have
# no meaning after Mesa lowers a draw to non-indexed vertex data.
start = after.index('static bool\nps5_multidraw_eligible(')
end = after.index('\nstatic ', start + 1)
eligibility = after[start:end]
assert eligibility.count('info->primitive_restart || info->has_user_indices ||') == 1
eligibility = eligibility.replace('info->primitive_restart || info->has_user_indices ||',
    'info->primitive_restart || (info->index_size && info->has_user_indices) ||')
# Bounded diagnostics distinguish remaining input fallbacks without per-draw logs.
anchor = '      rejects |= BITFIELD_BIT(PS5_BATCH_REJECT_INPUT - 1);'
assert eligibility.count(anchor) == 1
eligibility = eligibility.replace(anchor, '''   {
      rejects |= BITFIELD_BIT(PS5_BATCH_REJECT_INPUT - 1);
#ifdef PS5_DRAW_PROFILE
      static unsigned input_reports;
      if (info && draws && num_draws && context->batch_reject[0] >= 10000 && input_reports < 16) {
         input_reports++;
         printf("[ps5-batch-input] mode=%u index=%u user=%u restart=%u instances=%u draws=%u count=%u indirect=%u\\n",
                info->mode, info->index_size, info->has_user_indices,
                info->primitive_restart, info->instance_count, num_draws,
                draws[0].count, indirect != NULL);
      }
#endif
   }''')
after = after[:start] + eligibility + after[end:]
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
