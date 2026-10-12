# ProsperoMC architecture

ProsperoMC is a Minecraft Java-only PS5 homebrew application. Its native C
frontend draws directly into prospero-win's framebuffer. Wine supplies Windows
API compatibility for the Windows x64 Java runtime and LWJGL native libraries.
The launcher backend is Java bytecode compatible with Java 8; it also runs on
newer registered Windows JVMs when a Minecraft version requires them.

The native interface takes visual direction from ProsperoEden's charcoal-green
panels, lime focus treatment, broad spacing and controller navigation. No
Switch emulator, ROM scanner or emulator service is included.

PolyMC's source is a behavior and format reference. Its Qt launcher has not
been ported or embedded. The independent backend implements Minecraft metadata,
isolated instances, downloads, native extraction and launch planning. The
feature audit describes the differences rather than calling this full parity.

## Process model

The PS5 title keeps the native launcher visible while Wine runs Windows Java
with the launcher JAR in `--serve` mode. Frontend actions publish bounded atomic
request files to this persistent JVM. It processes one request at a time, writes
progress, response and view files, and waits for the next request without
restarting the title. Memory/account settings and local mod browsing/toggling
run directly in the native bridge; settings preserve the other configuration
keys and are read by Java before each operation.

Preparing Minecraft writes a launch plan and an internal launch profile. That
profile selects the Windows JVM required by the version, sets native-library
and logging arguments before JVM initialization, and enters Minecraft in that
JVM. This avoids depending on Windows child-process creation in the PS5 port.
The worker exits only after a successful launch preparation so the title can
restart with the selected Minecraft JVM. Closing Minecraft returns to a fresh
native launcher process. A failed Java worker creates a failure marker before
returning to the UI, preventing an automatic restart loop; local actions remain
available and the next Java operation offers a retry.

The persistent root is `/data/ProsperoMC`, containing all Java, instances, mods,
downloads and configuration. `/app0` is the immutable packaged application. Instances
have isolated game directories and share verified downloaded libraries/assets.
Only internally generated backend and Minecraft profiles can be launched.

## Compatibility evidence

The Windows Java 8 supplied by the user is not a PS5-native JVM. It is intended
to run through Wine. Wine/OpenGL inclusion proves packaging, not that HotSpot,
AWT, LWJGL, OpenAL or a particular mod works on a PS5. Native compilation, host
Java tests and an actual console run provide separate evidence. See the
[compatibility notes](feature-audit.md) for current console coverage.

The runtime release uses a title-specific elevation helper for `PPSA99995`.
ProsperoMC uses `PPSA99888`; a helper for the other title must not be relabeled
or executed as if it matched. The package includes a matching helper built for
`PPSA99888`. Seeing `/data` alone does not prove the required grant: the native
check also requires effective UID zero before reusing access. The helper
validates the target title and applies the cooperative filesystem grant
protocol. Its actual console behavior remains an integration check.
