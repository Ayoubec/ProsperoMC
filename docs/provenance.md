# Source provenance

The downloaded source archives are pinned in `versions.lock`.

| Source | Use |
| --- | --- |
| mpereiraesaa/prospero-win | Vendored PS5 Wine runtime, display/input/audio adapters and native build tooling |
| PolyMC/PolyMC | Behavioral and instance-format reference; Qt frontend not shipped |
| blackbearreloaded/ProsperoEden | Visual reference and licensed font source; no emulator core |
| mpereiraesaa/ps5-native-app-boilerplate | Native build foundation pinned by prospero-win |

The checksum-verified `prospero-win-v0.1.1.zip` supplies compiled Wine, OpenGL,
RADV and dependent modules. Its `SOURCES.txt`, `THIRD_PARTY.md` and license texts
must accompany the staged runtime. Its source revision differs from the newer
vendored title sources; ABI compatibility requires checking the exports used
by the title and ultimately running the package on the console.

The Java startup repair rebuilds only `ntdll.prx` from the release's exact
Wine revision and 72 patches, plus upstream patch 0501 from the pinned newer
prospero-win source. The patch corrects the measured PS5 floating-point save
area offset. Source archives and module tooling are recorded in `versions.lock`;
the build report records imports, exports, patches and the resulting checksum.
The staged `WINE_SOURCES.txt` and `WINE_PATCHES/` identify this modification.
The graphics repair rebuilds only `win32u.prx` against the official PS5 OpenGL
CI SDK from source commit `738f94cbdf6ff1de0376dc1cd4ce1229fd640730`. This SDK
corrects BGRA sampler capability advertising so Mesa converts uploads to
supported RGBA textures. Its archive, manifest and source snapshots are pinned
in `versions.lock`; the staged source notice identifies the resulting module.
The actual compiled SDK capability function was checked on the host: BGRA
sampling is rejected, while BGRA rendering and RGBA sampling/rendering remain
supported. This build also includes the upstream legacy varying mapping,
lowered client-array draw acceptance and EGL HUD fixes committed after SDK
1.0.1. The artifact was checked against GitHub's published SHA-256 before use.
The console now renders the logo, menus, pointer and a single-player world;
the user confirms movement. Acceptable frame rate and saved-world reopening
remain under test.
Other Wine modules stay from the verified release.

The performance candidate modifies only the runtime's `ps5_screen.o` against
that pinned CI source. Smooth legacy geometry stays in a converted indexed
draw and may use existing batching; flat/unknown interpolation, geometry
shaders, transform feedback and active occlusion keep the original split path.
The source patch is staged in `WINE_PATCHES/smooth-legacy-batching.patch` and
recorded in `versions.lock` and the stage report. Every other runtime object
and the compiled shader compiler library remain byte-identical to the CI SDK.
Host policy and compiled texture-capability checks pass. The console retest
loads the saved vanilla 1.12.2 world; the user reports 30–60 FPS at 2 chunks
and 9–40 FPS at 10 chunks on low settings. This does not establish performance
for other Minecraft versions or graphics configurations.

The supplied Windows runtime is Eclipse Adoptium Temurin JRE 8.0.504+1, x64.
Its license/notices are retained when copied into the local data package.
User Minecraft content and credentials are not checked into source control.
