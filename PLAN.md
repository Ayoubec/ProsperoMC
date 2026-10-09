# ProsperoMC rebuild

## Contract
Minecraft Java only. Use prospero-win PS5 Wine/graphics/input/audio runtime; replace its generic game launcher. ProsperoEden supplies visual direction only. PolyMC is the behavioral and instance-format reference; its Qt desktop launcher is not a PS5-native library. Do not claim a complete PolyMC port or console playability without execution evidence. Preserve the previous source in artifacts/previous-javacraft-source.zip. Never import launcher account databases.

Pinned source archives (downloaded 2026-10-08):
- prospero-win b510eb3db8709bb251d3da3c56850e96e057f489
- PolyMC 5ad72dda606a7e8a3a3c7adae6de7053597fcc23
- ProsperoEden 026851f5accfca80e0f6cb2c83b4dc686e0ca25f

## Architecture and shared interfaces
Native PS5 frontend and Wine runtime; Java 8 compatible headless launcher JAR runs as a Windows Java application through Wine. Host CLI uses the identical JAR. Launch operations use fresh title processes, as required by upstream. Data root: /data/prosperomc (fallback /download0/prosperomc).

IPC is UTF-8 line-oriented key=value with no embedded newlines in values.
Java CLI: java -jar prosperomc-launcher.jar --root PATH --request PATH.
request.properties keys: command, id, version, name, loader, loaderVersion, source, username, memoryMb, plus command-specific keys.
Commands: catalog, create, install, import, prepare-launch, mods, mod-toggle, mod-add, settings, auth-device, auth-poll, clone, export, import-pack. Unknown commands return explicit errors.
launcher-view.properties: status, detail, instance.count; instance.N.id/name/version/loader/installed; version.count; version.N.id/type/java; mod.count; mod.N.name/enabled.
response.properties: ok, command, message. progress.properties: status, detail, done, total. Atomically replaced.
Backend writes profiles/launch.profile in upstream PwGameProfile syntax after prepare-launch. Runtime stages backend.profile. Internal profiles only.

Native frontend C ABI in app/native/pm_frontend.h: PmFrontend state, pm_frontend_init/update/render; actions carry command and id/version. Upstream PwPresentTarget framebuffer. Runtime owns invocation/file IO, frontend owns draw/navigation only. Coordinate header promptly.

## Ownership and leaves
- backend agent: launcher/, tests/launcher/, scripts/build-launcher.ps1, scripts/build-launcher.sh, gates/backend.md. Downloads, rules/assets/natives, imports, Java selection, launch preparation, loaders/mods/packs, device auth, tests.
- frontend agent: app/native/pm_frontend.*, app/preview/, tests/frontend/, gates/frontend.md. Eden-inspired console UI and framebuffer preview.
- runtime agent: vendor/prospero-win/, scripts/build-ps5.*, scripts/stage-ps5.py, tests/runtime/, gates/runtime.md. Vendor runtime, replace launcher, Java command bridge, compile/package.
- root: contracts, docs, source reset/archive, local Java/1.12.2 staging, integration, provenance, root gates.

## Status log
- Previous source archived; requested upstream archives downloaded.
- Additional leaf: legacy Forge 1.12.2 installer helper and tests, owned by frontend agent after its frontend gates; backend agent owns integration into Installer/Main. Gates: gates/forge.md.
- Host actual 1.12.2 install and Java8 launch plan verified; minimal payload selects 1346 files. Native title cross-build passes. Console FTP connected read-only; deployment pending final prefix and UI validation.
- User requested low-usage checkpoint. Complete local title/data staged, no FTP writes. See CHECKPOINT.md and GATES.md for continuation and exact hashes.
- User resumed: implement automatic required-Java provisioning plus native detected-runtime/download controls; 1.12.2 remains only testtarget. Java leaf integration gates in gates/java.md.
- Resumed Java/version flow complete;29backendtests+parentnativechecks pass. Finalpackagehashvalidation passes. AuthorizedFTP upload session96123 running; consoleworld evidence pending.
- ScopedFTPdeployment complete:3215datafiles+1767titlefiles, signedELFviews verified and criticalJAR/metadata readback verified. Userconsolelaunch test pending.
