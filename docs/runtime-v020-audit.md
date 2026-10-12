# Prospero Win v0.2.0 integration

Release: https://github.com/mpereiraesaa/prospero-win/releases/tag/v0.2.0
Source: `644e32e400c555e340d507383398c5d21b39b0b0`
Source archive SHA256: `f484565adb49aba496bd5dd02e133f3bda12d66580b0e9423cb4f939aac57edb`
Release archive SHA256: `7585efc624c2f8077c0d579a045ef808129a7b0bc525a9dd9c5c6db0c51626ca`

The release replaces upstream's native OpenGL SDK with Zink over Vulkan.
ProsperoMC retains win32u for Wine/launcher dependencies. Following the user's
Zink performance test, supported game choices are Zink OpenGL and Minecraft
Vulkan. Selecting Vulkan sets the game's API and uses the runtime's automatic
Vulkan path. Legacy native OpenGL selections migrate to Zink.

The integrated core update includes ntdll.prx, wineserver.prx and both matching
PE ntdll.dll companions. It retains every prior core export. New platform imports
resolve against the pinned SDK: cpuset_getaffinity, getppid, pthread_kill, qsort
and pthread_setschedparam. Exact ABI evidence is recorded in
`artifacts/runtime-v020-review/abi-review.json`; original modules are backed up
under that folder's `before-update` directory. This checks exports/imports,
not actual PS5 execution or every internal Wine protocol interaction.

Minecraft profiles enable the release's round-robin thread scheduling and
validated fast clock. The core also carries usable CPU-affinity reporting,
fixed-address memory backing, recommit zeroing, corrected exception/thread state,
process counters and directory notification updates. Networking/TLS upgrades
are audited but not included in this selected core update. The existing Java
DNS/TLS behavior remains in place.

Reproduce the core audit in WSL with `python3 scripts/review-runtime-v020.py`,
then stage with `python3 scripts/stage-runtime-v020-core.py`. Normal app updates
validate and publish the selected modules, matching PE companions and notices.
Stage the rebuilt Java/native app and regenerate signed FTP comparison views
before deployment. Other runtime modules, registry files, accounts, worlds,
mods, user settings and Java installations remain in place.

The official core executed Java on the console, but needed the local virtual
drive fix in `drive-root-fix.md` and bounded archive channels. Console tests
now confirm MinecraftXBOX launches, full FO26.2 starts and worlds save/reopen
without low-space warnings. The matching official PE companions are retained.
Native OpenGL performance is unresolved;
the showcase's GPU-driven workload does not establish Minecraft performance.
