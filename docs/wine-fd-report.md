The Fabulously Optimized world log repeatedly reports `Too many open files`
while resolving region-directory paths. The later `WindowsFileStore` error
for the debug folder follows failed folder creation; it is not proof of a
volume-query leak. Wine maps both Unix `EMFILE` and `ENFILE` to the Windows
error used in that message.

The captured console descriptor limit is already 13,952. Upstream's CWD
shim describes a separate, much smaller PS5 budget for independently opened
file objects, but its approximate 268 figure has **not** been measured on
this console's firmware. The image-view descriptor cleanup is already on
in the captured Wine logs. Neither another descriptor-limit increase nor
closing Java's ZIP/JAR handles without ownership evidence is an established fix.

`wine/ps5/pw_wine_fd_report.h` adds source-only failure telemetry to the
vendored ProsperoWin CWD shim. It reports once per shim module on `EMFILE`
or `ENFILE`: failing operation, path, flags, caller address, descriptor limit,
live descriptor types, verified tracked archive/image/region paths, and
a bounded set of sample paths. Its inode count is explicitly a lower bound:
descriptors and inode counts cannot reveal the number of independently opened
kernel file objects. It performs no opens, closes, allocations, or retries,
uses an atomic one-shot guard, and restores the failing call's `errno`.

The fixture lowers its own real `RLIMIT_NOFILE` to 64, exhausts it, then
exercises `open`, `openat`, `fopen`, `opendir`, directory scans, and eight
concurrent callers. Each produces exactly one report, preserves `EMFILE`,
rejects stale path records, and keeps file contents and handles intact:

```sh
python3 tests/runtime/test_wine_fd_report.py
```

Prepare the patch and SHA-256 provenance without building anything:

```sh
python3 scripts/prepare-wine-fd-report.py
```

For a later Wine build, `--recipe-root PATH` mirrors only the changed CWD
source and helper header into an existing pinned ProsperoWin recipe root.
It refuses an unexpected CWD baseline rather than overwriting other patches.
The existing `tools/build_wine_ps5.sh` compile recipe already compiles this
source separately into `ntdll.prx` and `wineserver.prx`; the header requires
no new object, runtime export, or PE-module change. The generated
`artifacts/wine-fd-review/cwd-fd-diagnostic.patch` and
`fd-probe-provenance.json` record the exact source and recipe inputs.

This helper has **not been built into or deployed with the current console
Wine PRXs**. The current native app's separate timed descriptor snapshots
can provide initial evidence without a Wine rebuild. A confirmed failing
syscall and census are still needed before choosing a remedy.
