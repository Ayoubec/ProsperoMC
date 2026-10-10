# PolyMC functionality audit

This is an independent native PS5 launcher and Java backend. PolyMC's Qt
application is not embedded. The table distinguishes implementation from actual
PS5 execution; vanilla 1.12.2 worlds are verified, while other configurations
still need separate console runs.

| Function | Current implementation |
| --- | --- |
| Minecraft releases and snapshots | Real Mojang catalog; native version screen and filters |
| Version download/install | Client, libraries, Windows x64 native archives, assets and logging configuration; metadata SHA1/size checks |
| Isolated instances | Create, install, clone, delete; separate game directories with shared verified downloads |
| Java selection | Required major from version metadata; detects installed Windows x64 runtimes and downloads a verified runtime automatically when needed |
| JVM/memory settings | Memory controls and detected-runtime/download controls in native interface; advanced settings through request files |
| Vanilla | Supplied 1.12.2 loads saved worlds on PS5 with movement, audio and saving |
| Fabric and Quilt | Loader metadata/profile resolution implemented and fixture-tested |
| Legacy Forge 1.12.2 | Checked installer profiles, embedded Forge artifact and LaunchWrapper/FMLTweaker support |
| Modern Forge and NeoForge | Not implemented; processor-based installers rejected explicitly |
| Installed mod management | Local JAR add/remove and enable/disable; native mod toggles |
| Online mod discovery | Modrinth search/download through backend requests; console online search is not implemented |
| Mod dependencies | Compatible required Modrinth project dependencies resolved; unusual version-only dependencies need manual installation |
| Instance packs | PolyMC/MultiMC ZIP import/export; Library pack picker reads `/data/ProsperoMC/imports` |
| Modrinth packs | Native search, release selection and verified `.mrpack` installation; console downloads confirmed. Fabulously Optimized 26.2/26.3 runtime failures remain unresolved |
| CurseForge packs | Manifest/service integration not implemented |
| Microsoft accounts | Phone QR/code with automatic device OAuth polling, Xbox/XSTS and Minecraft ownership checks; requested PolyMC public ID or optional custom ID. Complete console account sign-in remains unverified |
| Offline play | Explicit local single-player mode; no multiplayer authentication |
| Controller support | Native navigation with held-D-pad repeat; L1/R1 wheel bindings cycle the hotbar; USB wheel forwarding |
| Launcher feedback | Focus transitions, animated progress and quiet navigation/confirmation sounds; native build verified, hardware retest pending |
| Logs | Wine/native diagnostics and Minecraft logs; no PolyMC-style console/log viewer UI |
| Custom component/patch editors | Not implemented |
| General PC games or Switch emulation | Excluded from the application |

Full PolyMC feature parity is not achieved. The working host installer and
native cross-build are substantial implementation evidence, but neither is a
claim that all versions or packs run on PS5. Vanilla 1.12.2 has reached playable
saved worlds; high-distance performance is still being improved.

Minecraft 1.12.2 is used for initial vanilla and Forge testing. The normal
application workflow selects a version from the Mojang catalog; those test
instances do not restrict other versions.
