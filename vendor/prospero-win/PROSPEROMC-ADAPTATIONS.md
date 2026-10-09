# ProsperoMC runtime vendor adaptations

Upstream: https://github.com/mpereiraesaa/prospero-win
Pinned source: b510eb3db8709bb251d3da3c56850e96e057f489.
Original LGPL license and notices remain beside this file. The Minecraft-specific
frontend and Java file bridge are GPL-3.0-or-later, as the containing project is.

The native Wine, graphics, audio, HID, DualSense and title restart runtime remain.
The generic game library scanner, tiled launcher, profile catalog and game recipe/
transfer tools were removed. Only internal launcher and Minecraft Java profiles
can execute. Raw path= arguments and profile executable overrides are refused.
Data root is /data/prosperomc, fallback /download0/prosperomc; title is PPSA99888.

The app/native frontend replaces the upstream launcher. pm_bridge.c connects its
requests and atomic UTF-8 state files to the Java backend. A backend command runs
in a fresh title process under Wine. prepare-launch completion starts the selected
Minecraft Java executable in another fresh process. A launch marker is consumed
once and failed preparations return to the frontend. Screens/selections survive
process restarts. The launcher JAR is refreshed from app0 into the data root.

Profile arguments are bounded at 32 KiB and 256 tokens for Minecraft classpaths.
Left analog stick adds WASD movement; right analog stick retains upstream mouse
motion; explicit Minecraft pad bindings and USB keyboard/mouse are supported.

Build: scripts/build-ps5.sh. Package: scripts/stage-ps5.py. Both are at project root.
Wine runtime binaries come from checksum-verified upstream v0.1.1 (source8086243);
that source is slightly earlier than this pinned title integration. Its embedded
OpenGL is checked before staging. Native libc is reproduced from exact foundation
9c0b994 with digest e6ff45d16adf687855cc3b33b0c8a4132b6504360b221e0a34c7e99fb3ba0036.
Fresh prefixes must be initialized offline because upstream prevents child
processes, including wineboot, on PS5. A host10.0 prefix is only a fallback template;
its actual compatibility with the runtime11.17 needs console validation. Reports
never equate structural package completeness with playable Minecraft on PS5.

Version and Java flow: an empty catalog is fetched automatically once per data root, avoiding error reexec loops. Native Versions sends create-install; Java Settings renders up to 16 detected Windows runtimes and sends detect-java/install-java major requests. Required JVM downloads remain the Java backend's responsibility. The staged snapshot includes the verified bundled Java8 runtime; downloaded-runtime state comes from the console filesystem. Java runtime selection survives title restarts.
