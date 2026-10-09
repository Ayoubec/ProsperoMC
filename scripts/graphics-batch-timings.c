/* Producer-only batch timings: no clocks, atomics or logging in draw workers.
 * Queue time overlaps worker execution. GPU wait is observed CPU retirement
 * waiting, not a GPU timestamp or a measurement of total GPU busy time. */
#ifdef PROSPEROMC_BATCH_TIMINGS
#include "util/os_time.h"
static struct {
    int64_t window_ns, begin_ns;
    uint64_t queue_ns, worker_wait_ns, submit_ns;
    uint64_t gpu_wait_ns, reclaim_ns, present_ns;
    uint64_t draws, groups, batches, frames;
} runtime_batch_timings;

static uint64_t runtime_batch_elapsed(int64_t begin, int64_t end)
{
    return begin > 0 && end >= begin ? (uint64_t)(end - begin) : 0;
}

static void runtime_batch_timing_submit(int64_t queued, int64_t drained,
                                      int64_t submitted, unsigned draws,
                                      unsigned groups)
{
    runtime_batch_timings.queue_ns += runtime_batch_elapsed(
        runtime_batch_timings.begin_ns, queued);
    runtime_batch_timings.worker_wait_ns += runtime_batch_elapsed(queued, drained);
    runtime_batch_timings.submit_ns += runtime_batch_elapsed(drained, submitted);
    runtime_batch_timings.draws += draws;
    runtime_batch_timings.groups += groups;
    ++runtime_batch_timings.batches;
    runtime_batch_timings.begin_ns = 0;
}

static void runtime_batch_timing_present(int64_t start, int64_t end)
{
    runtime_batch_timings.present_ns += runtime_batch_elapsed(start, end);
    ++runtime_batch_timings.frames;
    if (!runtime_batch_timings.window_ns) {
        runtime_batch_timings.window_ns = end;
        return;
    }
    uint64_t elapsed = runtime_batch_elapsed(runtime_batch_timings.window_ns, end);
    if (elapsed < UINT64_C(5000000000))
        return;
    double count = (double)runtime_batch_timings.frames;
    double ms = 1e-6 / count;
    printf("[prosperomc-batch-time] frames=%" PRIu64 " window_ms=%.3f "
           "draws/frame=%.1f groups/frame=%.1f batches/frame=%.1f "
           "queue_ms/frame=%.3f worker_wait_ms/frame=%.3f "
           "submit_ms/frame=%.3f gpu_wait_ms/frame=%.3f "
           "reclaim_ms/frame=%.3f present_ms/frame=%.3f\n",
           runtime_batch_timings.frames, elapsed * 1e-6,
           runtime_batch_timings.draws / count, runtime_batch_timings.groups / count,
           runtime_batch_timings.batches / count,
           runtime_batch_timings.queue_ns * ms,
           runtime_batch_timings.worker_wait_ns * ms,
           runtime_batch_timings.submit_ns * ms,
           runtime_batch_timings.gpu_wait_ns * ms,
           runtime_batch_timings.reclaim_ns * ms,
           runtime_batch_timings.present_ns * ms);
    memset(&runtime_batch_timings, 0, sizeof(runtime_batch_timings));
    runtime_batch_timings.window_ns = end;
}
#endif
