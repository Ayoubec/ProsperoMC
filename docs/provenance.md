# Source provenance

The downloaded source archives are pinned in `versions.lock`.

| Source | Use |
| --- | --- |
| mpereiraesaa/prospero-win | Vendored PS5 Wine runtime, display/input/audio adapters and native build tooling |
| PolyMC/PolyMC | Behavioral and instance-format reference; Qt frontend not shipped |
| blackbearreloaded/ProsperoEden | Visual reference and licensed font source; no emulator core |
| mpereiraesaa/ps5-native-app-boilerplate | Native build foundation pinned by prospero-win |

The checksum-verified `prospero-win-v0.1.1.zip` supplies compiled Wine, OpenGL,
RADV and dependent modules. Its `SOURCES.txt`, `THIRD_PARTY.md` and license texts
must accompany the staged runtime. Its source revision differs from the newer
vendored title sources; ABI compatibility requires checking the exports used
by the title and ultimately running the package on the console.

The Java startup repair rebuilds only `ntdll.prx` from the release's exact
Wine revision and 72 patches, plus upstream patch 0501 from the pinned newer
prospero-win source. The patch corrects the measured PS5 floating-point save
area offset. Source archives and module tooling are recorded in `versions.lock`;
the build report records imports, exports, patches and the resulting checksum.
The staged `WINE_SOURCES.txt` and `WINE_PATCHES/` identify this modification.
The graphics repair rebuilds only `win32u.prx` against the official PS5 OpenGL
CI SDK from source commit `738f94cbdf6ff1de0376dc1cd4ce1229fd640730`. This SDK
corrects BGRA sampler capability advertising so Mesa converts uploads to
supported RGBA textures. Its archive, manifest and source snapshots are pinned
in `versions.lock`; the staged source notice identifies the resulting module.
The actual compiled SDK capability function was checked on the host: BGRA
sampling is rejected, while BGRA rendering and RGBA sampling/rendering remain
supported. This build also includes the upstream legacy varying mapping,
lowered client-array draw acceptance and EGL HUD fixes committed after SDK
1.0.1. The artifact was checked against GitHub's published SHA-256 before use.
The console now renders the logo, menus, pointer and a single-player world;
the user confirms movement and saved-world reopening. Higher-distance frame
pacing remains under test.
Other Wine modules stay from the verified release.

The performance candidate modifies the runtime's `ps5_screen.o` against
that pinned CI source. Indexed and non-indexed quads use Mesa's index translator/generator to preserve
the first or last provoking vertex across both triangles, then use one indexed
draw and existing batching even for flat shading. Restart/complex
geometry retains the conservative conversion path; smooth converted geometry
also uses batching. Geometry shaders, transform feedback and active occlusion
are excluded from the new quad path.
The source patch is staged in `WINE_PATCHES/smooth-legacy-batching.patch` and
recorded in `versions.lock` and the stage report. The production update also
recompiles `ps5_agc_runtime_backend.o` from the verified source with
`PS5_DRAW_PROFILE` disabled, matching the draw driver. All other runtime objects
and the compiled shader compiler library remain byte-identical to the CI SDK.
Host policy and compiled texture-capability checks pass. The console retest
loads the saved vanilla 1.12.2 world; the user reports 30–60 FPS at 2 chunks
and 9–40 FPS at 10 chunks on low settings. This does not establish performance
for other Minecraft versions or graphics configurations.

The October 9 quad update addresses remaining per-triangle GUI/particle work;
the first console retest reports TNT at 30 FPS instead of 0.5 FPS. Higher
chunk-distance performance remains limited (about 25 FPS at 6, 10 FPS at 10).
A follow-up batches indexed quads and removes redundant scans only for
internally generated indices with exact known bounds. The user reports 60 FPS
at 4 low-setting chunks, about 21 at 8 fancy/fullscreen chunks and 8 at 16.
The next update reuses immutable quad patterns and caches publication of owned
draw buffers. CPU map/subdata callbacks invalidate that publication; persistent,
exported and GPU-written buffers retain per-use flushing. Hardware retest is
required for any performance claim about this new module.
The actual generated Mesa quad indices
pass first/last provoking-color and winding checks. Only the draw-driver object
changes in that earlier update; the existing shader compiler and resource synchronization remain.

The next production update fixes synchronous descriptor allocation churn. The
latest session's destruction receipt records 2,522,286 cache hits and 1,952,046
misses. Synchronous groups already wait for confirmed retirement, but their
cleanup discarded private descriptors instead of returning them to the existing
bounded cache. The corrected cleanup reuses only private, retired, correctly
sized buffers; shared buffers and a full cache retain normal reference release.
Unconfirmed GPU retirement still pins resources or terminates safely. Successful
groups no longer write a log line each time. Per-draw and cache profiling is
disabled in both compiled objects; errors and lifecycle receipts remain enabled.
Set `PROSPEROMC_DRAW_PROFILE=1` when building a diagnostic renderer. These are
verified code-path fixes; their FPS gain still requires a console retest.

The production retest reports 25-45 FPS while wandering and 44-56 while still
at 1440p/8 chunks; F3 lowers this to 16-32 and 16 chunks gives 13-23. Native
logs confirm profiling is off and 5,199,964 of 5,200,000 shader-pair lookups hit
the hot cache. The next patch checks that existing byte-verified cache before
parsing and validating the packages, and stores the validated section layout
inside its owned package snapshot. Changed/reused package bytes still undergo
original parsing and validation; no GPU ownership or batching logic changes.
The real generated matching and routing code passes 10,000 warm-cache draws
without parsing, plus mutation, malformed-ELF, stage and topology tests. The
performance gain from this follow-up still requires a console retest.

The shader-layout retest reports 29-40 FPS wandering, about 43-44 still and
32 with F3 at 1440p/8 chunks; 16 chunks remains 16-23. The next build enables
the pinned upstream `PS5_ASYNC_NATIVE_PREP` implementation with two workers,
using its required `ps5_agc_gate2_run_sync` entry point. The producer snapshots
draw inputs and retains their resources; workers prepare commands, and the
producer collects results in draw order before submission. Existing GPU
retirement still controls resource reuse. The exact upstream tests were taken
from the verified source archive and run against the patched runtime, with
ASan/UBSan, for one and two workers: reverse completion, ring wrap, duplicate
results, startup/pinning failure, tessellation drain and shutdown all pass.
Console startup receipts now verify CPU affinity on cores 10/12. The user
reports 47-82 FPS wandering, about 90 stationary and 37-65 with F3 at
1440p/8 chunks; 16 chunks remains around 20-23 FPS. Returning from 16 to
8 chunks initially gives 45-51. Camera and terrain differ between observations.
Upstream workers busy-spin while idle, so CPU usage can increase. Set
`PROSPEROMC_ASYNC_NATIVE_PREP=0` for a synchronous diagnostic comparison;
`PROSPEROMC_DRAW_PROFILE=1` also selects synchronous preparation because the
upstream detailed profiling counters cannot run concurrently.

The follow-up retains a single last shader-pair pointer per preparation worker.
Shared entries are immutable after insertion and are freed only after workers
join and GPU work retires. A matching pointer still compares the entire owned
VS/PS package bytes, lengths, keys and topology before returning without the
shared insertion mutex. Every miss follows the existing protected cache and
validation path. Shutdown discards the producer's borrowed pointer too.
The actual generated wrapper passes an ASan/UBSan two-thread check: 200,000
byte-verified hot hits avoid locking; all 26 warmup/mutation lookups lock.
Changed bytes, reused keys, sizes, topology and distinct thread state are
covered. Shared-cache log counters now count searches that reach that cache;
worker-local hits bypass those counters. The console retest reports peaks of
78-88 FPS at 1440p/8 chunks with 44-54 during turns; 16 chunks gives 19-30,
mostly 24. Returning to 8 averages about 53. These manual observations do not
isolate the cache's contribution from terrain and camera differences.

The next diagnostic build enables `PROSPEROMC_BATCH_TIMINGS=1` while retaining
both workers and all rendering paths. Producer-only clocks around batch
begin/submit/drain/retirement/presentation generate one five-second aggregate.
No individual draw or worker instrumentation is added. Queue time overlaps
worker execution; GPU wait is CPU polling for retirement, not total GPU busy
time. The exact aggregation helper passes interval, averaging and reset checks;
source checks verify no worker/draw call sites. Default builds omit it.

In the completed diagnostic run, the five stable high-draw windows cover 594
frames and average 1,483 draws/frame. Frame-weighted timings are 33.637 ms
queue, 0.280 ms remaining worker wait, 0.448 ms submission and 0.104 ms CPU
retirement polling. They support targeting the producer path, without claiming
to measure total GPU busy time. The run's descriptor cache records 6,902,928
hits and 2,656,392 misses. Before an empty-cache allocation, deferred draws now
poll the existing FIFO retirement path without waiting. Already-completed
batches return their private descriptors; unfinished work remains owned.
The bounded cache, queue order, submission and GPU completion checks are
unchanged. A host check exercises the actual gate and retirement loop for ready,
unready, nonempty-cache, partially empty and no-inflight cases. Console effect
on allocation misses, queue time and FPS is pending.

Mouse-wheel support extends the existing motion event's code field, retaining
the deployed ntdll queue layout and validator. Patch 0671 sends a normal Windows
wheel event in win32u. USB notches and controller wheel bindings share this path.
The application requests 120 Hz through upstream patch 0722 and declares the
upstream HFR `attribute3=0x80040`; the SDK retains its 60 Hz fallback.
See the [upstream display metadata documentation](https://github.com/blackbearreloaded/ps5-opengl/blob/main/integration/SDL2/README.md).

Modrinth pack import follows the [official format definition](https://support.modrinth.com/en/articles/8802351-modrinth-modpack-format-mrpack),
with client filtering, SHA1/SHA512 verification and layered overrides. Optional
client files are included and can subsequently be disabled in Mods. Unsupported
loader dependencies fail explicitly, and incomplete instance imports are removed.

For PS5 Java 8 and 1.12.2 only, a single-class Netty overlay lets its existing
adapter fallback handle Java's GetIfTable Error. The original library remains
unchanged, the original class hash is pinned, and the overlay carries Netty's
license. A real Java 8/Netty test reproduces the adapter Error and verifies a
TCP listener/request/reply. Console world sharing now opens without crashing
and reports a port.
Cross-device joining remains unverified (one PC status connection was refused).

The supplied Windows runtime is Eclipse Adoptium Temurin JRE 8.0.504+1, x64.
Its license/notices are retained when copied into the local data package.
User Minecraft content and credentials are not checked into source control.

Direct Modrinth pack discovery uses the official v2 search, project-version and
version endpoints, matching PolyMC's project/release flow. The downloaded
`.mrpack` goes through the existing verified importer and Minecraft installer.
See [Modrinth API](https://docs.modrinth.com/api/operations/searchprojects/).
Java's fallback downloads official Eclipse Temurin release assets from GitHub,
using the release asset SHA256 or its publisher-provided checksum file.

The packaged prospero-win `wine/ps5/pw_ws2_32_libc.c` explicitly rejects public
names with EAI_NONAME. A Java 8 name-service proxy supplies IPv4 records through
[Cloudflare's JSON DoH endpoint](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-json/),
using numeric resolver addresses to bootstrap. Standard resolver and destination
TLS certificate checks remain enabled. The packaged Java 8 passed a real DoH
lookup plus Modrinth HTTPS 200 on the host; PS5 verification remains pending.
