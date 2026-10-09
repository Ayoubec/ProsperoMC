# Upstream review — October 9, 2026

Reviewed prospero-win through [`807eed638c268b94f313e6371e2c760fe1cb2b5b`](https://github.com/mpereiraesaa/prospero-win/commit/807eed638c268b94f313e6371e2c760fe1cb2b5b).
The working Minecraft runtime remains based on the pinned Wine revision;
this update rebuilds only win32u, preserving the Java signal-state repair
and the existing PS5 OpenGL optimizations.

- Backported upstream [`0910`, worker desktop cache](https://github.com/mpereiraesaa/prospero-win/commit/da57aaab64bfd54e068da35522139ef6d6886a31).
  Fresh worker threads can recognize existing desktop handles without creating
  windows or loading drivers. Failed window-rectangle queries now return empty
  rectangles rather than reading uninitialized data. It is a correctness fix,
  not a measured Minecraft FPS improvement.
- Reviewed [`0908`, native suspension context](https://github.com/mpereiraesaa/prospero-win/commit/45edff166f47aa1d40874cdb84cad1eb36558845).
  It protects native service context when the main guest machine differs from
  the native machine, especially PE32 guests. Our Minecraft instance uses PE64
  Java, so this update does not replace the working ntdll for that change.
- Recent D3D9 transform/queue fixes and the PE32/native IME class-domain fix
  do not address this instance's OpenGL path and are not bundled wholesale.

Local patch `0672` strips resizable-frame and maximize-button styles from
top-level windows only when `WINE_PS5_FIXED_WINDOW=1` on the PS5 build.
Window creation and later style changes both enforce this; child windows and
non-PS5 builds retain their styles. The native ProsperoMC launcher sets this
flag. Changing resolution remains possible through the launcher settings.

## Vulkan

[Minecraft 26.2](https://www.minecraft.net/en-us/article/minecraft-java-edition-26-2)
offers an experimental Vulkan renderer. Its release notes require Vulkan 1.2,
dynamic rendering and push descriptors. Those requirements are version-specific.
The packaged runtime contains Wine Vulkan and Mesa RADV, making a separate
modern Minecraft test plausible. Matching Vulkan features, Java and LWJGL
still require console testing; compatibility and faster performance are not
established. Vanilla 1.12.2 uses LWJGL 2/OpenGL and has no native Vulkan switch.

## Performance and display evidence

An earlier snapshot had `useVbo:false`, despite FPS 150 and VSync disabled.
The fresh file already has VBO enabled, and the user reports no improvement
from that setting. All option values are preserved; no performance gain is
claimed from the scoped write. The remaining bottleneck needs profiling.
Logs show successful PS5 AGC GPU submissions and the game identifies the AGC
renderer. The etaHEN overlay's 0% GPU reading alone cannot establish GPU idleness.
Aggregate CPU usage also does not identify which thread limits frame rate.

720p/1080p settings change both Wine's virtual desktop and Minecraft launch
dimensions. The existing 120 Hz request is retained; actual negotiated refresh
and the reported 60 FPS ceiling remain to be checked on the user's display.

The review also checked [`d5a0ec0`](https://github.com/mpereiraesaa/prospero-win/commit/d5a0ec0195531f0b607aea548be8f014d2f9146a), published during this build. Its validation-only D3D9 command scans do not affect Minecraft’s OpenGL path and were not imported.
