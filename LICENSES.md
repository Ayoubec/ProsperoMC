# Licensing boundaries

Repository-owned ProsperoMC application code is GPL-3.0-or-later. The original native-app foundation's LICENSE remains at the root. Vendored prospero-win and Wine retain LGPL-2.1-or-later, with component notices under vendor/prospero-win and the packaged Wine runtime.

PolyMC was consulted as a behavior and format reference. Its Qt application is not packaged. ProsperoEden supplies visual direction only; any reused font files carry their original OFL notice.

The local supplied Java 8 is Adoptium Temurin under GPL-2.0 with Classpath Exception and component notices. Those notices must remain beside the staged runtime. Minecraft files imported from the user's local installation are local build data and are not source-control or public release content. Account databases from that installation are excluded.

A runtime package must preserve its original SOURCES.txt, THIRD_PARTY.md and LICENSES directory. Source archives and compiled dependencies are pinned in versions.lock. Host fixture success and native cross-compilation are not a console compatibility claim.
