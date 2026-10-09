# Native frontend preview

The PNG files in `artifacts/frontend/` come from `pm_frontend_render()` writing
an upstream `PwPresentTarget`, followed by PPM-to-PNG conversion. The console
frontend uses that exact renderer. These are native CPU framebuffer renders,
not a browser mockup.

Run `bash tests/frontend/run.sh` from a host with a C compiler, then run
`python app/preview/convert.py` with Pillow installed. On Windows the same
build can run in WSL. The tests compile as C99 with `-Wall -Wextra -Werror`.

`render output.ppm SCREEN [launcher-view.properties|--empty]` can render real
backend state. Screens 0-5 are Home, Library, Versions, Mods, Settings and
Accounts. With no state file supplied, the preview uses a clearly illustrative
fixture: one Minecraft 1.12.2 instance, six version rows and detected Java 8/21
entries. The fixture does not establish that any game ran on a PS5. Account
and mod lists are empty.

The original Eden-inspired drawing code uses Eden's green/lime color direction,
broad spacing, split detail panels and controller focus treatment. Montserrat
Medium is rasterized into `pm_font.h`; its SIL OFL license is stored beside it.
Rebuild the font with `generate_font.py FONT.ttf app/native/pm_font.h`.

L1/R1 (or the runtime's mapped previous/next-tab keyboard keys) changes tabs.
The d-pad/arrows selects rows. Right moves from a list to its detail actions;
left returns to the list. Cross/Enter selects, Circle/Back returns home, and
Triangle/Refresh reloads the catalog, current mods or detected Java runtimes.
A running backend command
locks duplicate actions while preserving screen navigation.
Square on the Versions screen switches between releases, snapshots and all
versions. The release filter is selected by default.

Download Version dispatches one `create-install` command, which creates the
selected Minecraft instance, downloads it and detects or downloads the Java
runtime required by its Mojang metadata. Installed instances dispatch
`prepare-launch`. The settings screen offers Java 8/17/21/25 download/verify
cards and a Refresh Runtimes action. Square cycles through every detected Java
entry, including other major versions, with its version, validity and detail.
Empty inventory and invalid runtimes have explicit states. Mod toggles, memory settings,
clone/export, offline/Microsoft mode and device sign-in dispatch actual backend
commands. Legacy Forge is offered specifically for Minecraft 1.12.2; newer
Forge profiles requiring installer processors are unavailable. Console file
browsing and custom Java path configuration use the host CLI.
