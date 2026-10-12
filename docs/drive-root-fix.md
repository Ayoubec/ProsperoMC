Wine's virtual C/Z drive links exist only in `.pw-symlinks`. The CWD shim's
`lstat()` handling treated a final slash as if the final link should remain
unresolved. Therefore `lstat("dosdevices/c:/")` reached a nonexistent physical
path instead of the existing directory represented by `dosdevices/c:`.
Wine's `GetVolumePathNameW` queries these roots with a trailing slash.

Console Java 8, 21 and 25 all showed `Files.isWritable=false` and a read-only
ZIP filesystem for a temporary JAR which could be opened for writing. The
write-check stack failed inside `WindowsFileStore.create`, after access and
DOS readonly checks. Native volume information failure was translated to
`NoSuchFileException`. Fabric tiny-remapper then refused the read-only ZIP
output with “JAR can't be written”. A separate P drive did not fix the shared
drive-root semantics.

The fix follows a final virtual directory link when the input ends in `/`,
while retaining that slash on the resolved path. Retaining it matters:
`lstat("file-link/")` must fail with `ENOTDIR`. Ordinary `lstat("link")` and
no-follow `fstatat` without a trailing slash still report the link itself.
No Java readonly bypass, mod rewriting or recursive permission changes apply.

`python3 scripts/check-drive-root-links.py` compiles the real upstream CWD shim
and syscall fixture. The original version reproduces the drive-root failure;
the fixed version passes the full existing CWD suite plus trailing slash,
repeated slash, directory/file-link and no-follow cases under ASan/UBSan.
`prepare-wine-core-rootfix.py` and `build-wine-core-rootfix.sh` reproduce the
selected v0.2.0 core rebuild, retaining the matching official PE companions.
The failure-only FD reporter is included to diagnose the remaining mod and
world-save file exhaustion.

The core rebuild passed its link checks and ABI review: all deployed exports
remain available, no platform imports were added, and the FD reporter is present
in both modules. The fixed core is deployed and independently verified on the
PS5. Console Java8/21 now report valid C/Z/P directories, writable files and
writable ZIP mounts. Minecraft XBOX passes remapping and reaches OpenGL; its
subsequent Legacy4J graphics-registry crash is addressed separately in
`mod-archive-channels.md`. This fixes the write checks, not every mod startup.
