/* Use native strided buffer bounds for packed, owned vertex allocations.
 * The GPU consumes the original indices/base vertex; no index bytes are
 * cached or assumed immutable, including persistent index mappings. */
static bool
ps5_gpu_vertex_capacity(const struct ps5_context *context,
                         const struct pipe_draw_info *info, int bias,
                         unsigned *capacity)
{
   struct ps5_vertex_layout layout;
   if (!context->vs || !context->vs->nir || !context->vertex_elements ||
       !context->vertex_elements->count || context->vertex_buffer_count != 1 ||
       context->gs || context->tcs || context->tes ||
       context->stream_output_target_count || info->instance_count != 1 ||
       info->mode != MESA_PRIM_TRIANGLES || bias < 0 ||
       !ps5_vertex_layout_from_state(context->vs, context->vertex_elements, &layout) ||
       layout.count != context->vertex_elements->count)
      return false;
   const struct pipe_vertex_buffer *binding = &context->vertex_buffers[0];
   const struct ps5_resource *resource =
      (const struct ps5_resource *)binding->buffer.resource;
   if (binding->is_user_buffer || !resource || !resource->data ||
       resource->base.target != PIPE_BUFFER || resource->external_cpu_access ||
       resource->gpu_written || resource->index_bounds_gpu_writable ||
       binding->buffer_offset >= resource->size)
      return false;
   const unsigned stride = context->vertex_elements->elements[0].src_stride;
   if (!stride || stride > 0x3fffu)
      return false;
   const uint64_t available = resource->size - binding->buffer_offset;
   const uint64_t records = available / stride;
   /* Full packed records ensure every component of every admitted attribute
    * fits the allocation even for the last GPU-admitted vertex index. */
   if (available % stride || !records || records > UINT32_MAX ||
       (uint64_t)bias >= records)
      return false;
   for (unsigned i = 0; i < layout.count; ++i) {
      const struct pipe_vertex_element *element = &context->vertex_elements->elements[i];
      const unsigned bytes = ps5_vertex_format_size(element->src_format);
      if (element->vertex_buffer_index || element->instance_divisor ||
          element->src_stride != stride || !bytes || bytes > stride ||
          element->src_offset > stride - bytes)
         return false;
   }
   *capacity = (unsigned)records;
   return true;
}
