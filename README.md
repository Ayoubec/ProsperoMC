# ProsperoMC

Minecraft Java launcher for homebrew-enabled PS5, rebuilt on [prospero-win](https://github.com/mpereiraesaa/prospero-win). Its native interface takes its appearance from [ProsperoEden](https://github.com/blackbearreloaded/ProsperoEden); the launcher behavior and instance formats follow [PolyMC](https://github.com/PolyMC/PolyMC).

This project is under development and uses Windows x64 Java through Wine.
Vanilla 1.12.2 now loads saved worlds on the tested PS5, with movement and audio.
The user reports 30–60 FPS at 2 chunks and 9–40 FPS at 10 chunks on low graphics
settings. Other versions, mod loaders and online features require separate
console checks. It is an independent launcher, not an embedded Qt build of PolyMC.

![Native launcher UI preview](assets/generated/launcher-preview.png)

The main flow is to choose a release or snapshot in Versions and download it.
Installation selects the Java major required by that version, reuses a valid
installed Windows x64 runtime, or downloads a verified runtime when missing.
Settings lists detected runtimes and offers Java downloads. Minecraft 1.12.2
is the initial test case, not the application's fixed or main version.

## Build and use

From Windows CMD, run `ProsperoMC.cmd build-send` to build and update the
existing PS5 installation at `192.168.1.111:2121`. Close the app and start its
FTP server first. Use `build` or `send` separately, or double-click for a menu.
Updates preserve console worlds, settings, mods and Java. See
[build and deployment details](docs/build-and-deploy.md).

Build the Java launcher with `./scripts/build-launcher.ps1` on Windows or `bash scripts/build-launcher.sh` on Linux with a JDK. Build the native title with `./scripts/build-ps5.ps1` or `bash scripts/build-ps5.sh`. The PS5 build uses the pinned public SDK and native foundation.

The identical backend JAR runs on the PC and through Wine on PS5:

```powershell
java -jar artifacts/launcher/prosperomc-launcher.jar --root game-data/prosperomc --request request.properties
```

Requests use UTF-8 `key=value` lines. See the launcher documentation and [architecture](docs/architecture.md). All writable Java, Minecraft instances, mods and downloads live together under `/data/ProsperoMC`; the loader package is `/data/homebrew/PPSA99888`.

Only Minecraft instances and internally generated Java profiles are offered. General PC-game importing and emulator functionality are absent. The previous JavaCraft probe is preserved locally in `artifacts/previous-javacraft-source.zip` and `artifacts/previous-project-tooling.zip`.

See [feature audit](docs/feature-audit.md), [console checks](docs/console-tests.md), [provenance](docs/provenance.md), and [acceptance gates](GATES.md) for implemented features, limitations and verification evidence.

## Licensing

Repository-owned application code is GPL-3.0-or-later; vendored prospero-win retains LGPL-2.1-or-later and component licenses. Java and fonts retain their own notices. Local game files, account state, downloaded runtime binaries and build outputs are ignored by Git. See LICENSES.md and the vendored runtime notices.
