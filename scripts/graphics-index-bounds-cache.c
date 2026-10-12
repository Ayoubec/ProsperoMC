/* Reuse validated index bounds, including across base vertices, while bytes are unchanged.
 * Exported/persistent mappings and pending GPU writes always take the scan. */
struct ps5_index_bounds_entry {
   size_t offset;
   unsigned count, index_size;
   int bias;
   unsigned minimum, maximum, effective_minimum, effective_maximum;
   bool valid;
};

struct ps5_index_bounds_cache {
   struct ps5_index_bounds_entry entries[8];
   unsigned next;
   struct {
      size_t checked;
      uint8_t pattern[6];
      bool initialized, rejected;
   } quads[2];
};

struct ps5_index_bounds_metrics {
   uint64_t calls, range_hits, quad_hits, scans, scanned_indices;
   uint64_t quad_validated, bypass;
   uint64_t gpu_bounded;
};

/* Index bounds helpers; require ps5_resource. */
static bool
ps5_quad_prefix_bounds(struct ps5_resource *resource, size_t offset,
                       unsigned index_size, unsigned count,
                       unsigned *minimum, unsigned *maximum)
{
   /* Recognize actual bytes, never a buffer label or a game's assumed format.
    * Only an owned, unchanged buffer reaches this helper. Every newly used
    * element is checked before the periodic representation can describe it. */
   if (!count || (index_size != 2 && index_size != 4) || offset % index_size ||
       resource->size / index_size < 6 || offset > resource->size ||
       count > (resource->size - offset) / index_size)
      return false;
   const unsigned slot = index_size == 4;
   struct ps5_index_bounds_cache *cache = &resource->index_bounds_cache;
   if (cache->quads[slot].rejected)
      return false;
   if (!cache->quads[slot].initialized) {
      unsigned mask = 0;
      cache->quads[slot].initialized = true;
      for (unsigned i = 0; i < 6; ++i) {
         unsigned value = ps5_index_value(resource->data, index_size, i);
         ++resource->index_bounds_metrics.quad_validated;
         if (value > 3) {
            cache->quads[slot].rejected = true;
            return false;
         }
         cache->quads[slot].pattern[i] = value;
         mask |= 1u << value;
      }
      if (mask != 15) {
         cache->quads[slot].rejected = true;
         return false;
      }
      cache->quads[slot].checked = 6;
   }
   const size_t start = offset / index_size, end = start + count;
   const size_t previous = cache->quads[slot].checked;
   for (size_t i = previous; i < end; ++i) {
      uint64_t expected = (uint64_t)(i / 6) * 4 + cache->quads[slot].pattern[i % 6];
      const uint64_t limit = index_size == 2 ? UINT16_MAX : UINT32_MAX;
      if (expected > limit ||
          ps5_index_value(resource->data + i * index_size, index_size, 0) != expected) {
         resource->index_bounds_metrics.quad_validated += i - previous + 1;
         cache->quads[slot].rejected = true;
         return false;
      }
   }
   if (end > previous) {
      resource->index_bounds_metrics.quad_validated += end - previous;
      cache->quads[slot].checked = end;
   }
   /* All later groups exceed all earlier groups. The extrema therefore lie
    * in the first/last (possibly partial) six-element groups, for any pattern
    * containing all four vertices. This also handles non-quad draw lengths. */
   *minimum = UINT32_MAX;
   *maximum = 0;
   size_t first_end = MIN2(end, start + (6 - start % 6));
   size_t last_start = MAX2(start, end - 1 - (end - 1) % 6);
   for (size_t i = start; i < first_end; ++i)
      *minimum = MIN2(*minimum, (unsigned)((i / 6) * 4 + cache->quads[slot].pattern[i % 6]));
   for (size_t i = last_start; i < end; ++i)
      *maximum = MAX2(*maximum, (unsigned)((i / 6) * 4 + cache->quads[slot].pattern[i % 6]));
   return true;
}

static bool
ps5_cached_index_bounds(struct ps5_resource *resource, size_t offset,
                         unsigned index_size, unsigned count, int bias,
                         unsigned *minimum, unsigned *maximum,
                         unsigned *effective_minimum, unsigned *effective_maximum)
{
   struct ps5_index_bounds_cache *cache = &resource->index_bounds_cache;
   struct ps5_index_bounds_metrics *metrics = &resource->index_bounds_metrics;
   ++metrics->calls;
   const bool reusable = !resource->external_cpu_access && !resource->gpu_written &&
                         !resource->index_bounds_gpu_writable;
   if (reusable) {
      for (unsigned i = 0; i < 8; ++i) {
         const struct ps5_index_bounds_entry *entry = &cache->entries[i];
         if (entry->valid && entry->offset == offset && entry->count == count &&
             entry->index_size == index_size) {
            *minimum = entry->minimum;
            *maximum = entry->maximum;
            if (entry->bias == bias) {
               ++metrics->range_hits;
               *effective_minimum = entry->effective_minimum;
               *effective_maximum = entry->effective_maximum;
               return true;
            }
            if (bias < 0 && *minimum < (uint64_t)-(int64_t)bias)
               return false;
            /* A range crossing the uint32 wrap boundary is not monotonic.
             * Its true effective extrema still require the original scan. */
            if (bias > 0 && *minimum <= UINT32_MAX - (uint32_t)bias &&
                *maximum > UINT32_MAX - (uint32_t)bias)
               break;
            *effective_minimum = *minimum + (uint32_t)bias;
            *effective_maximum = *maximum + (uint32_t)bias;
            ++metrics->range_hits;
            return *effective_maximum != UINT32_MAX;
         }
      }
      if (ps5_quad_prefix_bounds(resource, offset, index_size, count, minimum, maximum)) {
         if (bias < 0 && *minimum < (uint64_t)-(int64_t)bias)
            return false;
         if (!(bias > 0 && *minimum <= UINT32_MAX - (uint32_t)bias &&
               *maximum > UINT32_MAX - (uint32_t)bias)) {
            *effective_minimum = *minimum + (uint32_t)bias;
            *effective_maximum = *maximum + (uint32_t)bias;
            ++metrics->quad_hits;
            return *effective_maximum != UINT32_MAX;
         }
      }
   } else {
      ++metrics->bypass;
   }
   ++metrics->scans;
   metrics->scanned_indices += count;
   if (!ps5_index_bounds(resource->data + offset, index_size, count, bias,
                         minimum, maximum, effective_minimum, effective_maximum))
      return false;
   if (reusable) {
      struct ps5_index_bounds_entry *entry = &cache->entries[cache->next++ % 8];
      *entry = (struct ps5_index_bounds_entry){
         .offset = offset, .count = count, .index_size = index_size, .bias = bias,
         .minimum = *minimum, .maximum = *maximum,
         .effective_minimum = *effective_minimum, .effective_maximum = *effective_maximum,
         .valid = true,
      };
   }
   return true;
}
