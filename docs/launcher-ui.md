# Launcher controls

The native visual pass retains the compact catalog and tabs, with rounded
cards, bright Play and Save actions, and six complete background/surface/text
palettes. Home's grass trim and drawn icon backplates have been removed.
Transparent artwork blends into its card. Previews use the actual native
renderer and are inspected after navigation/framebuffer checks.
The reference is [Overdrive's controller-driven catalog](https://github.com/half144/overdrive-releases);
its release repository provides no screenshot, so this is a Minecraft visual
adaptation within the existing layout rather than an exact reproduction.

Home shows up to 12 instances per page. Installed pack icons are used when
available. Instances without an icon use a Minecraft-style grass block for
vanilla, feather for Fabric/Quilt, furnace for Forge, or fox for NeoForge.
Select a card with the mouse, then select it again to play. With a controller,
move to the card and press X. The next/previous buttons and directional controls
reach the rest of the library.

Library keeps the instance list beside Play, Manage Content, Rename, Duplicate
and Delete. Rename opens a controller keyboard; USB typing replaces the selected
name, Enter/Triangle saves, Square erases and Circle cancels. It updates only
the display name in launcher and PolyMC metadata. Folder identity, worlds and
content stay in place. Imported Modrinth/CurseForge packs default to pack name
plus Minecraft version, preserving explicit custom names. Old automatic
Modrinth release labels are migrated only after matching provider metadata.
Delete asks for confirmation and removes that instance's worlds and
content. Cancel is selected by default.

Add Instance groups the installation sources in one place:

- Minecraft: choose a release or snapshot and a loader, then download.
- Modrinth: search packs and choose a release to install as its own instance.
- CurseForge: browse packs through the configured CurseForge API.
- Your own pack: copy a supported pack to `/data/ProsperoMC/imports`, refresh,
  and select it. Modrinth `.mrpack`, PolyMC/MultiMC ZIP and supported CurseForge
  archives use this picker.

Modrinth and CurseForge have a search bar above the results. The initial list
browses packs without a preset search. Click the bar or press Up from the first
result and select it to enter a query; Search submits it. The controller's
on-screen keyboard and USB keyboard use the same field.

The current loader installer supports Vanilla, Fabric, Quilt and legacy Forge
for Minecraft 1.12.2. Unsupported Forge/NeoForge combinations produce a clear
message.

Content names the instance being edited at the top. Select that control or use
left/right while it is focused to choose another instance. The Mods, Resource
Packs and Shader Packs tabs each list their own files. Each category has a
visible Modrinth search bar directly above its installed files, alongside Search,
Import and Delete. Select the bar to type, then Search to find content compatible
with that instance. Search results keep the category tabs and field visible;
Back returns to the installed files. Select a file to toggle it; Delete Selected
asks for confirmation. Import Local File scans the corresponding subfolder:

- `/data/ProsperoMC/imports/mods`
- `/data/ProsperoMC/imports/resourcepacks`
- `/data/ProsperoMC/imports/shaderpacks`

Disabling a file prevents it from being loaded. Resource packs and shader
packs also need to be chosen in Minecraft's own settings; a shader pack needs
a compatible shader mod.

Settings has memory, resolution, graphics API and controller-input selectors,
Java runtime cards and a Save Settings button. Directional controls move between
settings. Selecting a setting opens its option list; only that list edits its
value. Changes are
applied to the next game launch when Save Settings is selected.
Graphics API selects OpenGL through Zink or Minecraft's native Vulkan backend.
The next launch updates only `preferredGraphicsBackend` in Minecraft's options,
with an original-options backup. Vulkan requires a Minecraft client with its
built-in API selector; older clients receive a clear unsupported-version error.
Old native OpenGL settings migrate to Zink. Stage the
verified upstream provider with `python scripts/stage-zink-provider.py` before
sending a source build; `ProsperoMC.cmd send` includes the staged provider
and its matching Vulkan driver. The driver releases an unused startup
context's display ownership so the actual game window can present.
The launcher restores the normal VideoOut preset on opening, so it does not
inherit the game's high-refresh output mode. This does not alter the monitor's
FreeSync setting. Full FO Zink now has console evidence at60FPS16chunks;
shader performance remains under investigation.
Appearance and Display Pacing/VRR occupy matching cards in a second settings
row. Down from Memory/Resolution reaches Appearance; Down from Graphics/Input
reaches VRR. Left/Right moves between these two cards and Down reaches Java.
Theme and VRR selections save immediately; other settings retain Save Settings.
Backend runtime registration merges only its own settings fields, preserving
newer native preferences while optional work is in flight.
Pages use eased slide/fade motion and an eased tab marker. Sounds play outside
the render loop at five times the previous generated amplitude; actual sample
peaks remain below clipping. Installed pack
artwork supports PNG/JPEG/WebP and is refreshed once at backend startup.
Content Down from search enters the local mod/resource/shader list.

`VRR: Auto` preserves the game display policy. `VRR: Stable refresh` requests
fixed refresh as a flicker fallback while keeping the existing high-refresh
game mode. Menu output always requests fixed refresh. Console refusals are
logged; this setting cannot guarantee fixed HDMI refresh when firmware refuses
the request. See [the current UI/display investigation](ui-viewport-heap-vrr.md).
Game launches request fullscreen and normalize saved fullscreen/window-size
overrides with a one-time original backup. Shader, resource-pack and distance
options are preserved. The previous CLI-only correction was overridden by saved
Minecraft options. Manual fullscreen fixed the user's viewport; automatic
fullscreen still requires console confirmation.
Controller input defaults to emulated mouse/keyboard bindings. Native gamepad
mode forwards the controller to gamepad mods such as Controllify and disables
the emulated bindings for the game. Launcher controls and USB mouse/keyboard
remain available.

Accounts shows the Minecraft account name and offers Microsoft or Offline
mode. Start Sign-in displays the phone QR code and code; the launcher checks
for completion automatically.

Close at the top right exits ProsperoMC after confirmation. On a controller,
press Up from the top of a screen to focus the header, move right to Close,
then press X. Closing during an operation stops it; the confirmation states
this. Deleting waits for the current operation to finish.

L1/R1 change screens; X selects; Circle goes back; Triangle refreshes. Square
adds an instance on Home/Library, searches while browsing packs/content, and
changes the version filter inside the Minecraft catalog. The right stick moves
the pointer and R2 clicks. USB mouse and keyboard use the same controls and
search field.

The real native framebuffer preview is built by `tests/frontend/run.sh`.
It exercises controller and pointer flows, confirms deletion/exit behavior,
renders the same screens as the console, and decodes PNG/JPEG/WebP through the
runtime's image cache. Preview files are under `artifacts/frontend`.
