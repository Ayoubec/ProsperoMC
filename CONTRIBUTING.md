# Contributing to ProsperoMC

Keep the native frontend, Java backend and Wine bridge contracts in docs/architecture.md synchronized. Run backend fixture integration tests, frontend navigation/framebuffer tests and runtime staging tests for changes affecting those parts. Native changes must cross-compile with scripts/build-ps5.sh before packaging.

A title's STAGE-REPORT.json reports structural packaging and console validation separately. Never replace a missing runtime, JVM or mod loader with a successful placeholder. Check actual downloads against metadata hashes and reject malformed archives and unsafe paths. Do not commit account state, private game content or generated artifacts.

The vendor directory retains prospero-win's upstream licenses and sources. New functionality belongs in the Minecraft-specific bridge/frontend/backend, with generic Windows-game importers excluded from the compiled title.

Host launcher checks use Java 8, 17, 21 and 25. Set `JAVA8_HOME`, `JAVA17_HOME`, `JAVA21_HOME` and `JAVA25_HOME` as needed; GitHub Actions supplies all four. Build with Java 21. Run `python3 -m unittest discover -s tests/launcher -p 'test_*.py' -v` after building the launcher. Tests that compare against an actual downloaded Minecraft/Controlify/Fabric corpus require those optional local artifacts and report a skip when absent. They do not substitute mock data for an actual-client compatibility result.

Local logs, performance captures, account data and scratch investigation tools belong under ignored directories. Only useful source, build tools, licenses, documentation and reproducible regression fixtures should be committed.
