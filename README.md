# ProsperoMC

Minecraft Java launcher for homebrew-enabled PS5, rebuilt on [prospero-win](https://github.com/mpereiraesaa/prospero-win). Its native interface takes its appearance from [ProsperoEden](https://github.com/blackbearreloaded/ProsperoEden); the launcher behavior and instance formats follow [PolyMC](https://github.com/PolyMC/PolyMC).

This project is under development and uses Windows x64 Java through Wine.
Vanilla 1.12.2 now loads saved worlds on the tested PS5, with movement and audio.
Performance remains under development. With two preparation workers and
worker-local shader-cache hits, the latest 1440p test peaks at 78-88 FPS at
8 chunks, falling to 44-54 when turning. At 16 chunks it gives 19-30 FPS,
mostly 24; returning to 8 averages about 53. These are manual observations
rather than a fixed benchmark. Console logs verify both workers on cores
10/12. An opt-in batch timing build measures the remaining preparation and
retirement waits while retaining these optimizations.
Stable 60 FPS at 16 chunks is unverified.
FreeSync off resolved the reported bright-area flicker. With the monitor set to
120 Hz, the user reaches about 120 FPS looking at the sky. Vanilla 1.12.2 limits
its main menu to 30 FPS. Current game graphics choices are preserved.
Other versions, mod loaders and online features require separate
console checks. It is an independent launcher, not an embedded Qt build of PolyMC.

![Native launcher UI preview](assets/generated/launcher-preview.png)

**Home-screen music — “hollow. (mastered)” by [steveologic](https://github.com/steveologic).**
Huge thanks to steveologic for the soundtrack! Follow his work on
[Instagram](https://www.instagram.com/steveoology/). An 87-second loop plays
when ProsperoMC is highlighted in the PS5 home menu, through `sce_sys/snd0.at9`;
it does not play inside the launcher. Refresh the loader's cached presentation
assets after updating if the previous selection music remains.

The main flow is **Add Instance**: choose Minecraft, Modrinth, CurseForge or
an imported pack. Home shows your instances with their pack artwork, with
Minecraft-style loader icons when no artwork is available. Library offers
Play, Clone and Delete; deleting an instance requires confirmation.
For Minecraft, choose a release or snapshot and its loader, then download it.
Installation selects the Java major required by that version, reuses a valid
installed Windows x64 runtime, or downloads a verified runtime when missing.
Settings lists detected runtimes and offers Java downloads. Minecraft 1.12.2
is the initial test case, not the application's fixed or main version.
Settings selects 1280×720, 1920×1080, 2560×1440 (2K/1440p) or
3840×2160 (4K). Select a setting to open its choices, then use Save Settings
to apply changes to the next launch. Directional controls move between fields.
These are game-rendering
resolutions; the HDMI output mode depends on the console/display. Higher
resolution can reduce performance.
Game windows have edge resizing disabled on PS5.

To download a Modrinth modpack, choose **Add Instance → Modrinth**.
Search with the controller's on-screen keyboard or a
USB keyboard, choose a project, then choose its release. The installer downloads
the pack, Minecraft, its loader and required Java as a separate instance.
There is no preset search. Alpha/beta/release labels are shown; each pack's
PS5 execution still needs its own test.
Failed game installation can be resumed by selecting the release again or its
instance in Library. Downloads show byte progress and verify archive hashes.
If Adoptium's API is unreachable, Java uses official Temurin GitHub releases
with the same SHA256 and Windows x64 validation.
The PS5 Java 8 backend resolves public hostnames through certificate-verified
DNS over HTTPS, bootstrapped from Cloudflare's numeric resolver addresses.
The bundled Wine title resolver supports only numeric addresses and localhost;
without this compatibility service, downloads fail with UnknownHostException.

For a local pack, copy a PolyMC/MultiMC ZIP or Modrinth `.mrpack` into
`/data/ProsperoMC/imports` over FTP. Choose **Add Instance → Import Pack**,
choose the pack, and press X. Select the new instance to install its game and loader
dependencies. Each pack keeps its own mods, configuration and worlds. Fabric,
Quilt and Forge 1.12.2 manifests are supported. CurseForge manifest ZIPs use
the official API to resolve their files and need your own API key;
modern Forge/NeoForge installers are still unsupported. Modrinth files are verified against
both SHA1 and SHA512, and client overrides take precedence over shared overrides.

**Content** manages mods, resource packs and shader packs for the selected
instance. Switch instances and content type in that tab, browse compatible
Modrinth releases, or import a local JAR/ZIP from
`/data/ProsperoMC/imports/mods`, `imports/resourcepacks` or `imports/shaderpacks`.
Files can be enabled, disabled or deleted. Resource/shader pack activation is
chosen in Minecraft settings; shader packs also require a compatible shader mod.
Missing enabled Fabric dependencies are reported before starting Minecraft.

Settings also selects emulated controller mouse/keyboard input or native
XInput for controller mods. Native mode disables game key/mouse emulation;
the launcher's controller navigation remains available. The OpenGL renderer
selector offers the native PS5 driver and upstream's WGL/Zink provider, which
translates OpenGL to Vulkan. Stage the pinned provider with
`python scripts/stage-zink-provider.py`; normal CMD sends include it afterward.
Console validation of this new provider is pending.

### CurseForge setup

CurseForge's official API requires an API key issued to the application user.
Obtain API access through [CurseForge for Studios](https://console.curseforge.com/),
then put a UTF-8 file at `/data/ProsperoMC/private/curseforge.properties` containing
`apiKey=YOUR_KEY`. The key stays in private app configuration and is excluded
from public launcher state and instance exports. **Add Instance → CurseForge**
then browses packs and release files. The installer verifies file sizes and
SHA1/MD5 hashes and respects publishers who disable third-party downloads.
See [CurseForge setup and limitations](docs/curseforge.md).

L1/R1 cycle the hotbar, and USB mouse-wheel ticks are forwarded to the game.
The display profile requests 120 Hz with the upstream SDK's 60 Hz fallback;
actual refresh depends on the console/display accepting the mode. Minecraft's
own FPS and VSync settings are preserved. The launcher has focus transitions,
animated progress feedback, held-D-pad scrolling and quiet navigation sounds.
In the launcher, the D-pad or left stick navigates, X selects, and L1/R1 switch
tabs. The right stick moves the pointer and R2 clicks. USB mouse movement,
left-click, right-click (back), and wheel scrolling are supported. Lists select
on click; use the Play or Download button to start an operation.

Recent upstream Wine changes are reviewed selectively; see the
[October 9 upstream review](docs/upstream-review-2026-10-09.md). New Minecraft
releases include a Vulkan renderer, but modern Minecraft/Java/LWJGL and the
packaged Wine/RADV path still need console validation. The working 1.12.2
instance uses OpenGL on the PS5 GPU.

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

Microsoft sign-in shows a phone QR code, website address and short code in the
launcher. This build uses the requested PolyMC public-client sign-in option and
checks authorization automatically while kept open. It also supports a custom
client ID; see [Microsoft sign-in](docs/microsoft-sign-in.md).

Only Minecraft instances and internally generated Java profiles are offered. General PC-game importing and emulator functionality are absent. The previous JavaCraft probe is preserved locally in `artifacts/previous-javacraft-source.zip` and `artifacts/previous-project-tooling.zip`.

See [feature audit](docs/feature-audit.md), [console checks](docs/console-tests.md), [provenance](docs/provenance.md), and [acceptance gates](GATES.md) for implemented features, limitations and verification evidence.

## Licensing

Repository-owned application code is GPL-3.0-or-later; vendored prospero-win retains LGPL-2.1-or-later and component licenses. Java and fonts retain their own notices. Local game files, account state, downloaded runtime binaries and build outputs are ignored by Git. See LICENSES.md and the vendored runtime notices.
