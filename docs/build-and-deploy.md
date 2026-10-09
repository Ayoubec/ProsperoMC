# Build and deploy

From Windows CMD in the project folder, run:

```bat
ProsperoMC.cmd build-send
```

This builds the Java launcher and native PS5 app, stages their checksums, and
sends an app update to `192.168.1.111:2121`. Close Minecraft and ProsperoMC and
start the PS5 FTP server before sending. The update preserves console worlds,
mods, settings, Java installations and the Wine prefix. Repaired Wine/OpenGL
modules already in the distribution are retained. Changed app modules are
verified before publication; unchanged modules are skipped.

Use `ProsperoMC.cmd build` to build only, `ProsperoMC.cmd send` to send the
current staged app, or double-click the file for a menu. To change the address:

```bat
ProsperoMC.cmd build-send 192.168.1.111 2121
```

Build prerequisites are the cached JDK, Python 3, WSL Ubuntu and the existing
pinned PS5 SDK. `ProsperoMC.cmd help` lists the commands. For a custom Python or
WSL distribution, invoke `scripts/build-send-ps5.ps1` with `-Python PATH` or
`-Distribution NAME`. The entry point updates an existing complete console
installation; use the full deployment steps below for first installation.

Build the Java 8-compatible JAR with `scripts/build-launcher.ps1` on Windows
using the cached JDK, or pass `-Jdk PATH`. On Linux use
`bash scripts/build-launcher.sh` with a JDK on PATH. The JAR is written to
`artifacts/launcher/prosperomc-launcher.jar`.

Build the native title with `scripts/build-ps5.ps1` (WSL Ubuntu) or
`bash scripts/build-ps5.sh`. Its pinned public SDK/native foundation must be
prepared by the dependency setup script. Output is `dist/PPSA99888`.

`scripts/import-supplied.ps1` copies the user's Windows Java 8 and imports the
chosen Minecraft version into the ignored `game-data/prosperomc` directory. It
excludes launcher account databases and verifies the installation. The default
source is the supplied `C:\Users\Admin\Desktop\minecraft ps5` directory.

Use `scripts/select-game-data.py` to produce a minimal verified payload from
installed instances. This avoids copying unrelated versions' libraries/assets.
Initialize a fresh offline Wine prefix with `scripts/prepare-wine-prefix.sh`.
The prefix initializer must wait for Wine's registry files before exporting.
The stage report records whether its host Wine source matches the PS5 runtime.

Stage using `scripts/stage-ps5.py` with the Wine runtime release, Java 8, launcher
JAR, offline prefix, minimal game root and optional exact-title filesystem
helper. The helper's manifest must match the title ID, ELF and protocol digest.
The stage script refuses missing modules, a GDI-only runtime or credential files.
It writes `STAGE-REPORT.json` to the title and data directories.

The v0.1.1 Wine release lacks upstream patch 0501, which corrects the PS5 saved
floating-point state used during Java startup. `scripts/prepare-wine-fpfix.py`
verifies the pinned source archives and prepares the original release recipe
with that one patch added. Run `bash scripts/build-wine-fpfix.sh` in WSL, then
`scripts/stage-wine-fpfix.py`. This replaces only `ntdll.prx`, checks its imports
and patch set, preserves the original module for rollback, and records sources.
Regenerate the FTP ELF views before using `scripts/deploy-ps5-patch.py
--host IP --wine-fpfix` to publish the module and reports.

The loader package goes to `/data/homebrew/PPSA99888`. All writable app data
goes together to `/data/ProsperoMC`: Java, instances, mods, downloads and settings.
The title's filesystem helper must grant access to that folder.

`scripts/deploy-ps5.py --host IP --port 2121 --inspect` reads only this title's
locations. Upload with `--title dist/PPSA99888 --data dist/PPSA99888/prosperomc`.
Uploads are limited to this title/data root, verified for length and renamed
after transfer; executable and metadata files are published last. Repeating a
deployment uses its previous manifest to skip unchanged files. No other titles
are modified or deleted.

The deployment tool transfers files; the user launches the app through the
console's loader. `structurallyComplete=true` does not mean `readyToPlay=true`.
Follow `docs/console-tests.md` to establish Java, graphics and world execution.

Some PS5 FTP servers expose signed homebrew files as reconstructed ELF files.
Before deployment, `scripts/build-ftp-views.py --tool PATH_TO_NATIVE_TOOL`
derives comparison views from this build. The uploader verifies the complete
ELF representation, normalizing only bounded SCE version records that do not
overlap loadable segments. Executable byte changes are rejected. This avoids
treating the server's different reported size as a failed transfer.
