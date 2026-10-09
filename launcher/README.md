# ProsperoMC launcher backend

A Java 8-compatible headless Minecraft Java launcher, with no external Java dependencies. It implements selection and installation from the Mojang catalog, automatic detection/download of the required Java major, ordered Windows x64 rules, SHA1 checks, asset indexes/virtual assets, native extraction, exact logging configuration, vanilla/Fabric/Quilt and legacy Forge 1.12.2 instances, local import, mods, Modrinth mod search/download, PolyMC instance pack import/export, clone, and Microsoft device sign-in.

Build with `scripts/build-launcher.ps1` on Windows or `scripts/build-launcher.sh` with a JDK 9+ on Linux/macOS. The JAR is written to `artifacts/launcher/prosperomc-launcher.jar`. Copy it to `<root>/launcher/prosperomc-launcher.jar`. Invoke `java -jar prosperomc-launcher.jar --root ROOT --request REQUEST.properties`. UTF-8 request, response, progress and view files contain plain `key=value` lines; paths need no properties-file escaping. All operations finish with an atomic `response.properties` and `launcher-view.properties`.

Commands:

| Command | Request fields |
| --- | --- |
| catalog | (refresh Mojang version list) |
| create | id, name, version, loader=vanilla/fabric/quilt/forge, loaderVersion (optional) |
| create-install | same fields as create; creates the instance and installs Minecraft plus its required Java |
| install | id |
| import | id, source (.minecraft or its parent), version, name |
| prepare-launch | id; optional memoryMb, accountMode, username |
| mods | id |
| mod-add | id, source (local JAR), mod (optional filename) |
| mod-toggle | id, mod, enabled=true/false |
| mod-remove | id, mod |
| mod-search | query, id (optional instance filter) |
| mod-download | id, projectId, modVersion (optional Modrinth version ID) |
| clone | sourceId, id, name |
| export | id, destination (ZIP) |
| import-pack | source (PolyMC/MultiMC ZIP), id, name |
| delete | id |
| settings | memoryMb, java8/java17/java21/java25/etc, graphics=opengl/zink, accountMode=microsoft/offline, username, microsoftClientId |
| install-java | major; repair=true to replace an invalid runtime while preserving its old files |
| detect-java | scans named runtime folders and returns version, architecture validity and errors |
| auth-device / auth-poll / auth-signout | no extra fields |
| view | no extra fields |

`create-install` is the app's select-and-download flow; `create` and `install` are also available separately. Both installation and launch preparation read Mojang's `javaVersion.majorVersion`, reuse a valid matching Windows runtime, and automatically download a SHA256-verified Adoptium runtime when it is missing. Java 8, 17, 21, 25 and other metadata-required majors use the same mechanism. If a JRE is unavailable, it tries a Windows x64 JDK of the same major; it never substitutes another Java major.

Runtimes live at `<root>/runtimes/javaN/bin/java.exe`, where N is the required major. Detection checks `release` version, Windows OS and x64 architecture plus the PE64 headers of both `java.exe` and `bin/server/jvm.dll`. Invalid existing content produces a clear repair error. Explicit repair downloads and validates its replacement before preserving the old folder in the cache and installing the new one. A host Java installation is used to run the backend, never selected as a console game runtime.

The supplied 1.12.2 folder is a test fixture, not the app's version limit. To import it, use `command=import`, `id=minecraft-1.12.2`, `version=1.12.2` and `source=C:\Users\Admin\Desktop\minecraft ps5\.minecraft`. Import checks the client, libraries, assets and logging configuration; missing content is downloaded and an incomplete import keeps `installed=false`. The supplied Windows Java 8 runtime can be placed at `<root>/runtimes/java8`. Other versions are selected from the catalog through `create-install`, which also provisions their required Java. No Java installer process or game subprocess is executed by the backend.

The catalog view includes up to 2,048 version rows for the frontend's release/snapshot filters. `version.N.java=0` means the version's Java requirement is not known until its detailed metadata is cached; installation always uses the detailed metadata.

`graphics=opengl` is the packaged default. `graphics=zink` requires an optional matching Mesa Zink provider installed for prospero-win; the native runtime refuses a launch when that provider is missing.

`prepare-launch` creates `profiles/launch.profile` for prospero-win and `profiles/launch-plan.json`. Runtime starts a fresh PS5 title and selected Java process with the complete Minecraft system classpath and JVM/native settings. The backend's small Java entry point invokes the game's main class in that same JVM. No Java subprocess is created on PS5. Tokens are read from the private account file only after process start and never written to launch profiles, launch plans, the view or export packs.

Microsoft login requires an application ID registered by the app publisher as a public Microsoft client with Xbox/Minecraft access; this repository does not embed another launcher's ID. Device login performs Microsoft OAuth, Xbox Live, XSTS, Minecraft token, entitlement and profile checks. Accounts and refresh tokens stay under `private/`; Windows/Wine directory access controls apply when POSIX mode permissions are unavailable. Imports never copy launcher account databases. Explicit `accountMode=offline` is for local single-player only and supplies no multiplayer authentication or ownership bypass.

Supported packs are ordinary PolyMC/MultiMC components for vanilla, Fabric, Quilt and supported Forge 1.12.2 builds. Legacy Forge supports 14.23.5.2847, 14.23.5.2859 and 14.23.5.2864 (default) using SHA1-verified official installers and embedded universal JARs without child processes. Modern Forge and NeoForge installation processors, CurseForge/Modrinth pack manifests, legacy pre-1.6 nonstandard launch formats, advanced PolyMC Java/custom patch editors, and platform-specific third-party Java installers are explicitly unsupported. Modrinth required dependencies preserve a specified version when supplied; dependencies specifying only a version without a project ID require manual installation. Modern Minecraft versions and each native/library/mod combination require real console validation before compatibility can be claimed.
