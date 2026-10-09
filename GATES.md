# ProsperoMC acceptance gates

- [x] G1: Previous probe preserved and active project describes Minecraft-only architecture.
  EVIDENCE: artifacts/previous-javacraft-source.zip, previous-project-tooling.zip and previous-console-probe.zip; active README/PLAN, app/launcher/vendor tree replaces probe.
- [x] G2: Real installer, instances, mods and launch preparation verified.
  EVIDENCE: 29 backend fixture tests passed; parent performed real supplied1.12.2 installation, catalog and Java8prepare; real Forge14.23.5.2864 installed independently by parent plus7Forgefixture tests.
- [x] G3: Native frontend supports controller navigation and rendered screens.
  EVIDENCE: parent reran tests/frontend/run.sh successfully; six native framebuffer previews and navigation/guard tests; Forge/account-mode additions passed leaf checks.
- [x] G4: prospero-win runtime integrates Minecraft-only frontend and Java bridge.
  EVIDENCE: parent reran tests/runtime/run.sh: native bridge passed,4staging tests OK. Genericlibrary/catalog and arbitrarypath launches excluded from compiledapp.
- [x] G5: Supplied1.12.2/Java8 imported without credentials and launch prepared.
  EVIDENCE: actual Java8 fullinstall and prepare-launch OK; minimal verified two-instance payload build/minecraft-payload-final/PAYLOAD-REPORT.json.
- [x] G6: Complete PS5 title cross-compiled and staged.
  EVIDENCE: dist/PPSA99888/STAGE-REPORT.json structurallyComplete=true; current ebootSHA256bc674bc4326aa0383cf90f96593d5b8d6d5c440d069d15411b1fb9730c1d4484; Wine/OpenGL/Java/JAR/helper staged. readyToPlay=false records required console tests.
- [x] G7: Java and Minecraft reach a playable PS5world.
  EVIDENCE: Actual PS5 renders the logo, menus, pointer and vanilla 1.12.2 world; user confirms movement. The smooth-quad renderer fix raises reported FPS from 0.8-1.3 to 30-60 at 2 chunks, and 9-40 at 10 chunks with low graphics settings. The same New World reopens; logs confirm joining, saving overworld/nether/end and view-distance changes. Evidence: artifacts/console-batching-success, graphics-batching policy/archive/capability checks and console-graphics-repair.json. This is a scoped single-player pass; higher-distance frame pacing and other versions/loaders remain unverified. All app data remains /data/ProsperoMC.
- [x] G8: PolyMC feature parity audited and unsupported functionality recorded.
  EVIDENCE: docs/feature-audit.md. FullPolyMCparity is not achieved; modernForge/NeoForge, servicepackmanifests and advancededitors remain unsupported.


- [x] G9: App downloads chosen Minecraft versions and detects/downloads the required Java.
  EVIDENCE: gates/java.md4/4checked; actualJava17download/detection and parentnativeintegration checks passed.

2026-10-08 console feedback repair: all30 launcher tests PASS, including persistent
worker failure recovery, consecutive settings updates and exit after successful
prepare-launch. Native bridge tests verify local memory/account persistence,
preserved configuration, mod enumeration/toggles and traversal rejection;4stage
tests PASS. Frontend guards/navigation PASS and triangle icon visually checked.
PS5 feedback confirms the UI opens, but Java still fails during startup. See
CHECKPOINT.md and artifacts/console-drive-retest for the current diagnosis.


