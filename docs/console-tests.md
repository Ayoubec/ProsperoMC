# Console verification

Use a homebrew-enabled PS5 and a loader that supports complete title folders.
Upload the built `PPSA99888` directory as a whole. Replacing a mounted title
requires closing it first and refreshing the loader's mount/discovery state.

Record the firmware, loader version, package hash and data path for each run.
The earlier JavaCraft probe's successful launch does not prove this new app.

1. Launch ProsperoMC and confirm its native interface, controller navigation,
   writable data root and imported Minecraft instance.
2. Run a catalog request. Confirm Windows Java reaches the backend, writes
   response/view files and returns to the launcher without a crash.
3. Verify HTTPS and certificate trust with a small checked metadata download.
4. Install vanilla 1.12.2. Verify the client, libraries, assets and extracted
   Windows DLLs against the launcher report.
5. Prepare and launch with Java 8. Capture Java/Wine exceptions and Minecraft
   logs. Reaching the title screen is distinct from loading a playable world.
6. Load a single-player world. Check movement, controller/USB input, OpenGL
   rendering, audio, saving and a return to the launcher.
7. Repeat with a compatible mod loader and a known compatible local mod.

Store Wine/native diagnostics and Minecraft logs with the package hash. Redact
account tokens before sharing. Failed Java startup, missing native DLLs or
unsupported Wine calls are actionable runtime failures, not installer success.

2026-10-08: User console screenshot confirms the native frontend renders and
loads both staged instances. Startup reported a missing launcher JAR even though
both deployed copies were present. The repair avoids replacing a byte-identical
staged JAR and adds the real homebrew directory to package/runtime/restart lookup.
Regression checks verify reuse preserves the existing inode, upgrades replace
changed content, and a missing source is still reported as failure. The visible
error now includes the initialization errno and data root. Gameplay is unverified.

Second feedback: user observed one-second black flashes, Mods refresh, memory/account saves ineffective and errno13. Approved temporary read of only ProsperoMC native logs completed; all original file/directory modes restored. Logs show per-action LoadExec followed by Wine exiting in server_init_process before Java executes. Existing /data visibility bypassed the helper; the repair requires effective UID0 before reusing the filesystem grant. A persistent Java worker now serves download/auth actions beside the native UI. Settings/account saves and local mod operations stay native. The refresh footer uses a drawn triangle. Final host integration suite30/30 PASS; native regression/build checks PASS. Reopen this exact build and verify local settings survive reopening, account mode changes, Mods opens without a black screen, and a backend catalog operation completes before testing Minecraft.

Drive-table defect confirmed from fresh console logs: .pw-symlinks had CRLF and the virtual-link parser retained CR in targets. Staging/repair now use exact19-byte LF table and native tests verify normalization. UID1 private folders were preserved as backups and replaced with current UID0 private folders; fresh logs show the filesystem grant succeeds and Wine's server connects. User selected /data/ProsperoMC for all app data. New executable SHA256e3bb22eb4ac266a326e5a09cd08978144cf5a8219fea0bea661473c5cbfdff9e uploaded; Java worker and gameplay retest pending.

2026-10-09: The saved-FPU-state repair, disabled compressed pointers, Java 8
local-address cache and kernel random provider let the worker and Minecraft
stay running on the actual PS5. User hears Minecraft music but sees only a
gradient. Native graphics diagnostics repeatedly reject BGRA sampler views
(Mesa format 105). Disabling FBOs, VBOs and mipmaps did not resolve it. The
graphics-only rebuild uses the upstream SDK correction; menu rendering and
world movement/saving must be tested before marking the gameplay gate passed.

2026-10-09 follow-up: official CI SDK 738f94c's legacy varying, lowered
client-array and HUD fixes restored the Mojang logo, menus and pointer on PS5.
World creation then failed in Netty's adapter enumeration. The supported
io.netty.machineId override, generated from kernel entropy, prevents that
unsupported IP Helper call; the packaged Java 8/Netty local-channel smoke
passed. Deployed launcher SHA-256 is
19e57df575456995d3d55304934b63c464629defee07cd281fe492f88abc9cb0.
The user confirms a world loads and movement works, but reports 0.237 FPS.
Logs in artifacts/console-world-performance show a successful local server
and login, and about one presented frame per four seconds. The test instance
still used disabled VBOs and the default 12-chunk distance. A conservative
VBO/2-chunk preset is prepared; performance and save/reopen remain pending.

The settings-only retest reached 0.8–1.3 FPS. The local draw-driver patch then
kept smooth converted legacy geometry in one indexed draw and allowed existing
batching; flat and unknown interpolation still use the original split path.
Only ps5_screen.o changed in the runtime archive. Texture-capability, shading
policy and archive checks pass. The resulting win32u module and app update
were uploaded with executable/readback verification using ProsperoMC.cmd send.
The user reports 30–60 FPS at 2 chunks and 9–40 FPS at 10 chunks on low settings.
Logs in artifacts/console-batching-success confirm the same saved New World
loads, the player joins, all three dimensions save and view distance changes.
This passes the vanilla 1.12.2 single-player gate at the tested 2-chunk preset;
higher-distance pacing and other versions/loaders still need work.

On October 9, the first flat-quad batching update (win32u ba5edcc...) passes
actual console testing for TNT: the user reports 30 FPS during explosions,
previously 0.5 FPS. Open to LAN now reports port 61238 and permits changing
world game mode. The adapter warning is caught; no game crash follows. A PC
status connection was refused, so joining from another device is not verified.
The same retest reports about 25 FPS at 6 chunks and 10 FPS at 10 chunks.
The indexed-quad/known-generated-bounds follow-up is under build/test.

## October 9 controls, modpacks and buffer reuse update
The previous renderer measured 60 FPS at 4 low-setting chunks, about 21 at 8
fancy/fullscreen chunks and 8 at 16. The new module caches immutable quad indices
and publication of unchanged owned draw buffers; its console FPS is pending.
Controller wheel edges, CPU-edit publication, cached-pattern winding/provoking
semantics, native frontend and all 32 Java launcher integration checks pass.
An app-only update has been uploaded with verified readback; user settings and
worlds were preserved. Test the same world at 8/16 fancy chunks, L1/R1 and USB
wheel hotbar changes, launcher navigation sounds/animations, and Square in
Library/Mods to open the imports picker. A 120 Hz request falls back to 60 when
unsupported; verify actual negotiated output rather than assuming 130 FPS.

## Read-only buffer optimization

The user confirms resolution changes work, with about 25 FPS at 1080p and
18 FPS at 1440p. Fresh profiling shows many read-only vertex/index buffer maps
that drain queued draws and invalidate static publication. The candidate
keeps owned, CPU-written draw-buffer reads concurrent with GPU reads; writes,
GPU-written, exported/persistent and non-draw resources retain synchronization.
The exact predicate and map/unmap branches pass host tests, including repeated
reads and write/GPU/export exclusions. Compare the same world, camera, render
distance and graphics options at 1080p/1440p after deployment. Check terrain,
inventory items and TNT for correctness. No FPS improvement is established yet.

## Lowered draw batching follow-up

The read-only update's retest at 1440p/8 chunks started near 32 FPS, then stayed
at 13–14 after moving. Logs in artifacts/console-readonly-map-retest show average
buffer-map work falling from about 23,000 to 287 cycles per call. At the slowdown,
individual draw submissions increase from tens to roughly 3,400–4,700 per interval;
batch input rejects increase while other rejection categories remain zero.
The existing single-draw path already ignores has_user_indices when index_size
is zero, but batching rejected the stale flag unconditionally. The follow-up
aligns these checks and logs at most 16 remaining input fallbacks. It preserves
checks for actual client indices, indirect draws, primitive restart and unsupported
index formats. A host test extracts the actual eligibility predicate and exercises
these cases, including the restricted blitter fan path and empty inputs.
Console performance of this follow-up remains pending; test the same world at
1440p/8 chunks, move and stop, and check terrain, items and TNT for correctness.

## Menu triangle-strip submissions

The lowered-draw retest reports 24–30 FPS settled at 1440p/8 chunks and about35
while flying. The remaining main-menu slowdown is 16–20 FPS. In the dedicated
menu run (artifacts/console-menu-batching-retest), bounded input diagnostics
report mode5/non-indexed/count4 strips. Native single-submit calls stay around
3,400–3,500 per profiling interval; batch shader/framebuffer/depth/vertex/texture
rejects remainzero. The verified native runtime accepts hardware TRISTRIP6,
links packages using each draw's topology, and queues the complete draw packet.
The candidate admits non-indexed strips to the existing deferred path, preserving
index, restart, indirect and attachment-feedback guards. Tests extract both the
actual batch input predicate and native draw-state validator from pinned source.
Read-map/publication regression checks also pass. Actual strip rendering still
needs console verification, including menu text/buttons/panorama, terrain, clouds,
inventory items and TNT. No world FPS gain is claimed before that test.

The local 1.12.2 client bytecode's bib.k() returns30 when no world is loaded and
a GUI is open, otherwise the configured limit. This is the game's menu cap;
removing it is not part of this driver correction. Its source artifact is kept
locally as artifacts/minecraft-1.12.2-main-bytecode.txt, not redistributed.

## Deferred multi-draw groups

The strip update's user retest at1440p/8 chunks reaches43–55 FPS still,32–57
while walking and13–22 withF3 open. At16 chunks it remains7–22, at10 about20,
and looking at sky/down reaches60. The screenshot confirms actual2560x1440.
Freshlogs artifacts/console-strip-batching-retest show virtually all normal draws
eligible (6.81million), inputrejects8474, and no shader/framebuffer/depth/vertex/
texture rejects or GPU failures. In the retained tail,4014 lines report completed
multi-draw groups. The old ps5_try_multi_draw_batch takes a submission lock and
calls native batch_end for each group; batch_end retires all pending work with
wait=1 before returning. Individual deferred draws already retain resources and
descriptor snapshots until completion, but group calls bypass that path.

The candidate dispatches eligible groups through Mesa's existing util_draw_multi
before entering the old synchronous path. Each subdraw therefore uses the same
deferred queue as ordinary draws; its capacity, retirement fences and CPU-write
dependencies remain unchanged. Legacy split conversion, indirect and ineligible
groups retain their existing paths. The routing test extracts the actual block
and pinned Mesa helper, verifying draw IDs, zero-count subdraws, and fallback
guards. Existing topology and publication checks pass. Check the same scene with
F3 on/off, inventory, terrain and TNT before claiming an FPS improvement.

The console retest reports worse performance: about32 FPS at8 chunks,24 at10,
15–16 at16, and a persistent drop near10 after looking skyward and back down.
Mouse movement can exacerbate the drop. The monitor was also changed to120 Hz;
sky views now reach120 FPS. FreeSync off resolved the bright-area flicker.
Logs were saved in artifacts/console-deferred-multidraw-retest before rollback.
The multi-draw routing experiment is reverted. The exact checked910c698b module
and e98b54f8 source patch were restored from the saved backup and uploaded with
executable/both-report readback verification. Earlier strip, lowered-triangle,
read-only-map and quad improvements remain. No game options were changed.
Compare the same scene at1440p/8 and16 chunks with FreeSync off and120 Hz fixed,
including F3 open/closed and looking up then returning to the same view.


Production update, October 9: the latest pre-update report remains 8-24 FPS at
8 chunks. Fresh logs show 1,952,046 descriptor-cache misses and ~20us native draw
preparation. Synchronous retired descriptors now use the existing bounded cache;
success logging and per-draw profiling are removed. Compiled capability,
retirement ownership, input and resource-publication checks pass. New graphics
and native launcher executables were uploaded and their executable contents
verified over FTP. Launcher mouse selection/scrolling and stick navigation pass
host checks. Console FPS gain and device behavior await the user's retest.


Production retest: launcher mouse confirmed working; 1440p/8 chunks gives
25-45 FPS wandering and 44-56 still, F3 16-32, 16 chunks 13-23. Sky reaches120
and returning to terrain gives33. The native cache logs 5,199,964 hot hits from
5,200,000 lookups. Follow-up skips redundant shader package parsing only after
full byte verification against the cache's owned snapshot. Actual matching,
parser, stage-validation and routing tests pass, including mutated and malformed
packages. The module rebuild, compiled capabilities and archive checks pass;
FTP executable contents and both reports verified. Gain awaits console retest.


Shader-cache retest:1440p8chunks 29-40 wandering,43-44still,fastmouse27-41,
F3~32;16chunks16-23. Nextmodule enables the pinned upstream two-worker native
preparation mode, retaining shader/resource fixes and GPU retirement ownership.
Exact upstream queue/preflight tests pass underASan/UBSan for1/2workers, including
reverse completion, startup/affinity failures, ring wrap andshutdown. Production
capabilities/archive/importchecks pass. Graphics-onlyupload andELF/bothreport
readback verified. Console worker startup/affinity andFPS gain await retest.


Live console log now verifies both preparation workers: core10/worker0 and
core12/worker1 report verified affinity. GL swap counters advance at68-79FPS
in sampled5second windows, while CPU frame-transfer sequence stops updating.
Those counters serve different paths; no freeze is established. Chunkdistance
andcamera for these samples are unknown, so terrain FPS gain awaits user results.
