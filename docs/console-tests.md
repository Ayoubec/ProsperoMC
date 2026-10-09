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
