# ProsperoMC — Early Release

Minecraft: Java Edition on a homebrew-enabled PS5, with a native launcher built around your controller.

This is an early release, available as an experimental alpha. Thanks to [steveologic](https://github.com/steveologic) for the original soundtrack, “hollow. (mastered).”

## Included

- Vanilla Minecraft and compatible Fabric, Quilt and legacy Forge instances.
- Modrinth browsing, pack imports and content management.
- OpenGL through Zink and Minecraft's Vulkan renderer, with Zink shader-pack support.
- DualSense launcher controls, controller-mod input and USB mouse/keyboard support.
- Theme colors, instance artwork and naming, resolution and display-pacing settings.
- Automatic Java selection/downloads and Microsoft device sign-in.

## Install

Copy the app folder to `/data/homebrew/PPSA99888` and the bundled `prosperomc` data folder to `/data/ProsperoMC`. Refresh your loader and open ProsperoMC. Follow the [README](../../README.md#getting-started) for setup.

For an existing installation, close Minecraft and ProsperoMC before updating and preserve your data folder. The public update package must contain app/runtime updates only; do not replace existing worlds, instances or accounts with fresh defaults.

## Recommended setup

For the best experience on supported versions, select Vulkan as Minecraft's renderer, return to the launcher and set **Settings → Graphics API → Vulkan**, save and play again. Use OpenGL (Zink) for shader packs or versions without built-in Vulkan.

Use [Controlify](https://modrinth.com/mod/controlify) with native controller input for DualSense gameplay, or play with a USB mouse and keyboard.

## Still in progress

Modpack compatibility and chunk-loading performance need more work. Modern Forge/NeoForge installers are unsupported, and shader packs currently require Zink. Firmware, loader and multiplayer coverage remain limited.

Back up your worlds before updating. Report problems with your setup, pack/version and graphics backend; redact private account information from logs.

Minecraft game files, personal worlds and account credentials are not included. Third-party source and license notices must accompany the distributed runtime.
