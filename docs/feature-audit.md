# Compatibility notes

ProsperoMC is an early release. A version appearing in the catalog means it can be installed; it does not guarantee that every mod or pack will run on PS5.

## Console-tested configurations

| Configuration | Current status |
| --- | --- |
| Vanilla 1.12.2 | Single-player worlds, movement, audio and saving tested |
| Vanilla 26.2 | Gameplay tested |
| Minecraft XBOX 1.21.11 | Pack launches; performance depends on configuration |
| Full Fabulously Optimized 26.2 | Gameplay, DualSense identification and world save/reopen tested |
| Fresh & Smooth 26.2, Zink | Launches with restored animations; movement/chunk-loading stalls remain under investigation |

## Graphics and input

For the best experience on Minecraft versions with a built-in Vulkan renderer, select Vulkan in Minecraft and in the launcher before playing. Shader packs currently require OpenGL through Zink. Older versions also use Zink.

Use a compatible [Controlify](https://modrinth.com/mod/controlify) release with native controller input, or a USB mouse and keyboard. DualSense identity and ordinary controls are tested; the current input transport does not expose Sony gyro or adaptive-trigger features.

## Loaders, packs and online play

Fabric and Quilt installation are implemented. Legacy Forge 1.12.2 is supported; modern Forge/NeoForge processor-based installers are not. Modrinth browsing, compatible content downloads and pack imports are available. CurseForge requires your own API key.

Microsoft device sign-in and ownership checks are implemented. Server compatibility also depends on Minecraft version, account setup and the server's supported versions. Comprehensive multiplayer, firmware and loader coverage is still incomplete.

## Reporting a result

Include firmware, loader, Minecraft/modpack version, graphics backend and the steps you tried. Both successful runs and failures help. Remove private account information from any logs you share.
