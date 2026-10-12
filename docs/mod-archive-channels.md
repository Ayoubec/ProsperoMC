The fixed drive-root semantics now pass on the PS5: Java 8 and 21 report
`isWritable=true`, `zipReadOnly=false`, and valid C/Z/P directories. Minecraft
XBOX passed Fabric remapping and reached OpenGL. Its next crash is Legacy4J's
OSHI graphics-card lookup: Wine's PS5 adapter has DriverDesc and DriverVersion,
but lacks ProviderName. An offline registry edit did not survive Wine's display
initialization and has been removed. Patch0911 now sets ProviderName when
win32u creates the adapter, using the same provider as its existing
DEVPKEY_Device_DriverProvider. No remote registry edits are needed.

Fabulously Optimized's failure reporter captured EMFILE while opening a
processed Fabric JAR: 931 descriptors, 468 regular descriptors, 217 tracked
archive handles, 190 unique regular/directory inodes, and soft/hard limits12555.
The inode count is a lower bound, not the kernel file-object count or its limit.
Raising RLIMIT_NOFILE again cannot explain that failure. Exact traces are in
`artifacts/console-core-rootfix-live-all/logs/session-4.log`.

The first ZipFS pool let FO reach the native PS5 AGC OpenGL menu. Later Zink
world tests still failed to save level.dat and data/minecraft with EMFILE,
then failed to open the directory for a capacity query. These save failures
are real; chunk-save success does not prove world metadata was saved. A
low-disk warning is not proof that the data disk is actually full. Complete
20-file evidence: artifacts/console-world-save-pressure-all. Census:1241 live,
460 regular,186 tracked archives,22 regions,229 unique-inode lower bound,
RLIMIT12555. The actual kernel file-object limit is still unmeasured.

Fabric's ModContainer mounts resources through JDK ZipFS and retains each mount.
Each mount holds a READ backing channel, in addition to normal class-loader
archive access. The bounded channel helper retains at most16 such channels.
ZipFS's parsed central directory, original Paths and original mod/classpath JARs
remain intact. An evicted channel reopens the same verified file at its saved
position. Size, modification time and file key are checked before reopening;
an externally changed archive produces an explicit error rather than switching
silently. The pool serializes backing operations while they use a channel;
there is no background sampler or work in OpenGL draw calls.

A scoped Java startup instrumentation hook redirects only the READ varargs
Files.newByteChannel reference in jdk.nio.zipfs.ZipFileSystem. It validates the
constant-pool shape and adds the module read edge to the bootstrap helper. It
does not rewrite mods, disable JarURLConnection caching, unzip the classpath,
or change ZIP write channels. Non-archive files and non-READ options use the
ordinary JDK implementation. Writable ZipFS still rebuilds and replaces its
archive normally when closed.

Normal cached JarFile/URL readers retain another set of backing files. A
second pool now limits those to16 READ files while keeping ZipFile.Source's
central directory, signature cache and ordinary loader URL cache. Its
RandomAccessFile subclass closes the transient superclass descriptor before
Source uses it, then reopens through the bounded pool with the same identity
and position guards. The startup hook retransforms only Source's ordinary
READ construction; both OPEN_DELETE branches remain original. It validates
the constructor layout and every RandomAccessFile operation used by Source.
Unsupported JDK shapes fail startup explicitly. World write channels and
ordinary writable RandomAccessFile instances remain unchanged.

The launcher uses this helper only for modern Fabric/Quilt clients on Java17+
and installs its small bootstrap JAR beside the launcher. Java8 and vanilla
launches retain their original path. Java21 and the packaged Java25 passed
240 mounts and cached JAR readers,7680 concurrent reads,16+16 backing limits,
seek/close/file-change/interruption guards, OPEN_DELETE and ZIP/world
write/save/reopen. Separate signed-JAR tests verify64 archives through256 reads
across eviction, retain code signers and reject altered signed content.
All64 launcher tests and final5 focused artifact checks pass, as do native
runtime/crossbuild, Wine import gates and unchanged SDK archive checks.
The combined update is deployed with18 app/core/bootstrap files and graphics
ELF/both reports independently verified. Xbox startup and FO native OpenGL
world save/reopen remained pending at that stage. The next console test confirms
Xbox launches and FO runs a native PS5 AGC world, with no new EMFILE save failures.

Capacity diagnostics prove a separate volume bug: Z data paths report~0.79MiB
free on a~7MiB root volume; P reports~390GiB on the actual data volume. The
verified26.2 client uses FileStore usable space and warns below64MiB. A query
exception returns Long.MAX_VALUE, so failed capacity queries are not the direct
cause of that warning. The latest update now passes only the Minecraft gameDir
through the existing P mapping, verifies root/game file identities, and moves
no files. Native executable/classpath/workingdir guards remain unchanged.
The real directory-alias save/reopen fixture and all65 launcher tests pass.
Console warning removal and save/reopen are confirmed by the latest retest
described below.

Primary implementations reviewed:
- https://github.com/FabricMC/fabric-loader/blob/0.19.5/src/main/java/net/fabricmc/loader/impl/ModContainerImpl.java
- https://github.com/openjdk/jdk/blob/jdk-25%2B36/src/jdk.zipfs/share/classes/jdk/nio/zipfs/ZipFileSystem.java
- https://github.com/openjdk/jdk/blob/jdk-25%2B36/src/java.base/share/classes/java/util/zip/ZipFile.java
- https://github.com/oshi/oshi/blob/oshi-parent-6.9.0/oshi-core/src/main/java/oshi/hardware/platform/windows/WindowsGraphicsCard.java

Console confirmation after data-volume correction: user reports no low-space warnings or notifications. The latest FO log records clean save/quit, reopening New World at15:24:47 and another clean save at15:25:04, with no new EMFILE errors. Evidence: artifacts/console-data-volume-base-vertex-retest-all.
