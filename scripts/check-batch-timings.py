"""Check the exact producer-only timing helper and its source call sites."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
helper = (root / 'scripts/graphics-batch-timings.c').read_text()
source = (root / 'artifacts/graphics-batching/ps5_agc_native_runtime.c').read_text()
assert helper in source
draw = source[source.index('int main('):]
assert 'runtime_batch_timing' not in draw
queue = source[source.index('#ifdef PS5_ASYNC_NATIVE_PREP\n/* The producer'):
               source.index('int ps5_agc_gate2_batch_begin(')]
assert 'runtime_batch_timing' not in queue
assert source.count('runtime_batch_timing_submit(queued_ns, drained_ns') == 1
assert source.count('runtime_batch_timing_present(present_ns,') == 1
c = r'''
#include <assert.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define PROSPEROMC_BATCH_TIMINGS 1
''' + helper + r'''
int main(void) {
 assert(runtime_batch_elapsed(0,3)==0);
 assert(runtime_batch_elapsed(10,9)==0);
 assert(runtime_batch_elapsed(10,12)==2);
 runtime_batch_timings.begin_ns=1000000000;
 runtime_batch_timing_submit(1002000000,1003000000,1003500000,256,2);
 assert(runtime_batch_timings.queue_ns==2000000);
 assert(runtime_batch_timings.worker_wait_ns==1000000);
 assert(runtime_batch_timings.submit_ns==500000);
 assert(runtime_batch_timings.batches==1 && !runtime_batch_timings.begin_ns);
 runtime_batch_timings.gpu_wait_ns=4000000;
 runtime_batch_timings.reclaim_ns=500000;
 runtime_batch_timing_present(1003500000,1004500000);
 assert(runtime_batch_timings.frames==1);
 runtime_batch_timings.begin_ns=2000000000;
 runtime_batch_timing_submit(2002000000,2003000000,2003500000,128,2);
 runtime_batch_timing_present(6004000000,6004500000);
 assert(!runtime_batch_timings.frames && !runtime_batch_timings.batches);
 assert(!runtime_batch_timings.queue_ns && !runtime_batch_timings.gpu_wait_ns);
 assert(runtime_batch_timings.window_ns==6004500000);
}
'''
with tempfile.TemporaryDirectory(prefix='prosperomc-batch-timings-') as tmp:
    path = Path(tmp)
    (path / 'util').mkdir()
    (path / 'util/os_time.h').write_text('/* No clock calls in aggregation helper. */\n')
    (path / 'check.c').write_text(c)
    subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-I'+str(path), str(path / 'check.c'), '-o', str(path / 'check')], check=True)
    result = subprocess.check_output([str(path / 'check')], text=True)
    assert result.count('[prosperomc-batch-time]') == 1, result
    for expected in ('frames=2', 'draws/frame=192.0', 'groups/frame=2.0',
                     'queue_ms/frame=2.000', 'worker_wait_ms/frame=1.000',
                     'submit_ms/frame=0.500', 'gpu_wait_ms/frame=2.000',
                     'reclaim_ms/frame=0.250', 'present_ms/frame=0.750'):
        assert expected in result, (expected, result)
print('PASS: actual batch timing aggregation, five-second reporting/reset and invalid intervals; no per-draw or worker instrumentation')
