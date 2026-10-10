# Licensing boundaries

Repository-owned ProsperoMC application code is GPL-3.0-or-later. The original native-app foundation's LICENSE remains at the root. Vendored prospero-win and Wine retain LGPL-2.1-or-later, with component notices under vendor/prospero-win and the packaged Wine runtime.

PolyMC was consulted as a behavior and format reference. Its Qt application is not packaged. ProsperoEden supplies visual direction only; any reused font files carry their original OFL notice.

The native sign-in QR encoder is Project Nayuki's QR Code generator under MIT.
Its source files retain the full copyright/license notice; vendor/qrcodegen/PROVENANCE.json
records the pinned upstream revision and file hashes.

Home-screen selection music, “hollow. (mastered)” by [steveologic](https://github.com/steveologic), is included at the project owner's request. Thanks to the artist; see [Instagram](https://www.instagram.com/steveoology/). The recording retains its artist's copyright and is not covered by the application's GPL license. `sce_sys/snd0.at9` is an 87-second excerpt encoded with [PS5 AT9 Converter](https://github.com/blackbearreloaded/ps5-at9-converter), pinned at `f8ab08b33c1407bbd715a0af3c80c4da585832f4`; its GPL source is available there. The original MP3 is not included.

The PS5-only Netty 4.1.9 compatibility overlay contains one modified class under Apache-2.0 and included component notices. Its license is bundled from launcher/resources/META-INF/NETTY-LICENSE.txt. The original Netty JAR remains local Minecraft dependency data.

The local supplied Java 8 is Adoptium Temurin under GPL-2.0 with Classpath Exception and component notices. Those notices must remain beside the staged runtime. Minecraft files imported from the user's local installation are local build data and are not source-control or public release content. Account databases from that installation are excluded.

A runtime package must preserve its original SOURCES.txt, THIRD_PARTY.md and LICENSES directory. Source archives and compiled dependencies are pinned in versions.lock. Host fixture success and native cross-compilation are not a console compatibility claim.
