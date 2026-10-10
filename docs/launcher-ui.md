# Launcher controls

Home shows up to 12 instances per page. Installed pack icons are used when
available. Instances without an icon use a Minecraft-style grass block for
vanilla, feather for Fabric/Quilt, furnace for Forge, or fox for NeoForge.
Select a card with the mouse, then select it again to play. With a controller,
move to the card and press X. The next/previous buttons and directional controls
reach the rest of the library.

Library keeps the instance list beside Play, Manage Content, Duplicate and
Delete. Delete asks for confirmation and removes that instance's worlds and
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
Packs and Shader Packs tabs each list their own files. Select a file to toggle
it; Delete Selected asks for confirmation. Find on Modrinth filters content for
the chosen instance. Import Local File scans the corresponding subfolder:

- `/data/ProsperoMC/imports/mods`
- `/data/ProsperoMC/imports/resourcepacks`
- `/data/ProsperoMC/imports/shaderpacks`

Disabling a file prevents it from being loaded. Resource packs and shader
packs also need to be chosen in Minecraft's own settings; a shader pack needs
a compatible shader mod.

Settings has memory, resolution, OpenGL renderer and controller-input selectors,
Java runtime cards and a Save Settings button. Directional controls move between
settings. Selecting a setting opens its option list; only that list edits its
value. Changes are
applied to the next game launch when Save Settings is selected.
The OpenGL renderer chooses native PS5 rendering or Vulkan acceleration through
Zink. This leaves Minecraft's own graphics API selection unchanged. Stage the
verified upstream provider with `python scripts/stage-zink-provider.py` before
sending a source build; `ProsperoMC.cmd send` includes the staged provider.
The launcher restores the normal VideoOut preset on opening, so it does not
inherit the game's high-refresh output mode. This does not alter the monitor's
FreeSync setting. Console flicker and Zink performance still require testing.
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
renders the same screens as the console, and decodes a local PNG through the
runtime's image cache. Preview files are under `artifacts/frontend`.
