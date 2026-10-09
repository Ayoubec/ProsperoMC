/* Inserted into the pinned ps5_screen.c by prepare-graphics-batching.py.
 * Mesa's index generator puts the original quad's provoking vertex last in
 * both triangles. One fragment variant can therefore draw the whole buffer.
 * The original converter remains available for restart/complex draws.
 */
static bool
ps5_draw_quads_batch(struct pipe_context *base,
                     const struct pipe_draw_info *info, unsigned drawid_offset,
                     const struct pipe_draw_indirect_info *indirect,
                     const struct pipe_draw_start_count_bias *draws,
                     unsigned num_draws)
{
   struct ps5_context *context = (struct ps5_context *)base;
   if (!info || info->mode != MESA_PRIM_QUADS ||
       (info->index_size && info->index_size != 1 && info->index_size != 2 && info->index_size != 4) ||
       info->primitive_restart || indirect || !draws || num_draws != 1 ||
       !context->vs || !context->fs || !context->rasterizer ||
       context->gs || context->tes || context->tcs ||
       context->stream_output_target_count || context->active_occlusion_query ||
       context->render_condition_query ||
       !context->fs->nir->info.known_interpolation_qualifiers ||
       (context->fs->nir->info.inputs_read & VARYING_BIT_PRIMITIVE_ID) ||
       BITSET_TEST(context->fs->nir->info.system_values_read, SYSTEM_VALUE_PRIMITIVE_ID))
      return false;
   unsigned vertices = draws[0].count & ~3u;
   if (!vertices || !info->instance_count) {
      context->last_draw_status = 0;
      return true;
   }
   if ((!info->index_size && (uint64_t)draws[0].start + vertices > UINT_MAX) ||
       (uint64_t)(vertices / 4u) * 6u * 4u > UINT_MAX)
      return false;
   enum mesa_prim mode;
   unsigned index_size, index_count, offset;
   u_generate_func generate = NULL;
   u_translate_func translate = NULL;
   const unsigned mask = base->screen->caps.supported_prim_modes &
                         ~BITFIELD_BIT(MESA_PRIM_QUADS);
   const unsigned provoking = context->rasterizer->flatshade_first ? PV_FIRST : PV_LAST;
   /* Terrain draws start at zero. Keep one immutable pattern per provoking
    * convention, growing only when a larger chunk needs it (at most 12 MiB).
    * Deferred draws retain their own references when a cache entry grows. */
   if (!info->index_size && !draws[0].start && vertices <= (1u << 20)) {
      unsigned slot = provoking == PV_FIRST ? 0 : 1;
      unsigned capacity = context->quad_index_vertices[slot];
      struct pipe_resource *cached = context->quad_index_cache[slot];
      if (capacity < vertices || !cached) {
         capacity = util_next_power_of_two(MAX2(vertices, 256u));
         u_index_generator(mask, MESA_PRIM_QUADS, 0, capacity, provoking, PV_LAST,
                           &mode, &index_size, &index_count, &generate);
         if (!generate || mode != MESA_PRIM_TRIANGLES) return false;
         struct pipe_resource templ = {0};
         templ.target = PIPE_BUFFER; templ.format = PIPE_FORMAT_R8_UNORM;
         templ.bind = PIPE_BIND_INDEX_BUFFER; templ.usage = PIPE_USAGE_IMMUTABLE;
         templ.width0 = index_count * index_size;
         templ.height0 = templ.depth0 = templ.array_size = 1;
         struct pipe_resource *replacement = base->screen->resource_create(base->screen, &templ);
         if (!replacement) return false;
         generate(0, index_count, ((struct ps5_resource *)replacement)->data);
         pipe_resource_reference(&context->quad_index_cache[slot], NULL);
         context->quad_index_cache[slot] = replacement;
         context->quad_index_vertices[slot] = capacity;
         context->quad_index_size[slot] = index_size;
         cached = replacement;
      }
      struct pipe_draw_info converted = *info;
      struct pipe_draw_start_count_bias draw = draws[0];
      converted.mode = MESA_PRIM_TRIANGLES;
      converted.index_size = context->quad_index_size[slot];
      converted.index.resource = cached; converted.has_user_indices = false;
      converted.index_bounds_valid = true; converted.min_index = 0;
      converted.max_index = vertices - 1;
      draw.start = 0; draw.count = vertices / 4u * 6u; draw.index_bias = 0;
      context->legacy_primitive_conversion = context->legacy_batch_quads = true;
      context->legacy_flat_input_vertex = 2;
      base->draw_vbo(base, &converted, drawid_offset, NULL, &draw, 1);
      context->legacy_batch_quads = context->legacy_primitive_conversion = false;
      context->legacy_flat_input_vertex = -1;
      return true;
   }
   if (info->index_size) {
      if (u_index_translator(mask, MESA_PRIM_QUADS, info->index_size, vertices,
                            provoking, PV_LAST, PR_DISABLE,
                            &mode, &index_size, &index_count, &translate) == U_TRANSLATE_ERROR)
         return false;
   } else {
      u_index_generator(mask, MESA_PRIM_QUADS, draws[0].start, vertices,
                        provoking, PV_LAST, &mode, &index_size, &index_count, &generate);
   }
   if ((!generate && !translate) || mode != MESA_PRIM_TRIANGLES ||
       (index_size != 2 && index_size != 4))
      return false;
   struct pipe_draw_info converted = *info;
   struct pipe_draw_start_count_bias draw = draws[0];
   struct pipe_resource *release = NULL;
   void *indices = NULL;
   converted.index.resource = NULL;
   struct pipe_transfer *transfer = NULL;
   const void *source = NULL;
   if (info->index_size) {
      const uint64_t first = (uint64_t)draws[0].start * info->index_size;
      const uint64_t bytes = (uint64_t)vertices * info->index_size;
      if (first > UINT_MAX || bytes > UINT_MAX || first + bytes > UINT_MAX)
         return false;
      if (info->has_user_indices) {
         if (!info->index.user)
            return false;
         source = (const uint8_t *)info->index.user + first;
      } else {
         if (!info->index.resource || first + bytes > info->index.resource->width0)
            return false;
         source = pipe_buffer_map_range(base, info->index.resource,
                                        first, bytes, PIPE_MAP_READ, &transfer);
      }
      if (!source)
         return false;
   }
   u_upload_alloc(base->stream_uploader, 0, index_count * index_size, 4,
                  &offset, &converted.index.resource, &release, &indices);
   if (!indices) {
      if (transfer)
         pipe_buffer_unmap(base, transfer);
      return false; /* No draw has been submitted; the old path can retry. */
   }
   if (translate)
      translate(source, 0, vertices, index_count, info->restart_index, indices);
   else
      generate(draws[0].start, index_count, indices);
   if (transfer)
      pipe_buffer_unmap(base, transfer);
   u_upload_unmap(base->stream_uploader);
   converted.mode = mode;
   converted.index_size = index_size;
   converted.has_user_indices = false;
   converted.index_bounds_valid = !info->index_size;
   converted.min_index = info->index_size ? 0 : draws[0].start;
   converted.max_index = info->index_size ? UINT_MAX : draws[0].start + vertices - 1;
   draw.start = offset / index_size;
   draw.count = index_count;
   draw.index_bias = info->index_size ? draws[0].index_bias : 0;
   context->legacy_primitive_conversion = true;
   context->legacy_batch_quads = true;
   context->legacy_flat_input_vertex = 2;
   base->draw_vbo(base, &converted, drawid_offset, NULL, &draw, 1);
   context->legacy_batch_quads = false;
   context->legacy_primitive_conversion = false;
   context->legacy_flat_input_vertex = -1;
   pipe_resource_release(base, release);
   return true;
}
