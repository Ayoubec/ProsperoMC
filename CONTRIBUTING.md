# Contributing to ProsperoMC

Keep the native frontend, Java backend and Wine bridge contracts in PLAN.md synchronized. Run backend fixture integration tests, frontend navigation/framebuffer tests and runtime staging tests for changes affecting those parts. Native changes must cross-compile with scripts/build-ps5.sh before packaging.

A title's STAGE-REPORT.json reports structural packaging and console validation separately. Never replace a missing runtime, JVM or mod loader with a successful placeholder. Check actual downloads against metadata hashes and reject malformed archives and unsafe paths. Do not commit account state, private game content or generated artifacts.

The vendor directory retains prospero-win's upstream licenses and sources. New functionality belongs in the Minecraft-specific bridge/frontend/backend, with generic Windows-game importers excluded from the compiled title.
