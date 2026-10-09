# Legacy Forge validation

Run `python -m unittest discover -s tests/forge -p "test_*.py" -v` using the
bundled Python runtime. This builds the real Java sources with `--release 8`
into an isolated test directory. The fixture suite uses localhost HTTP;
restricted environments need network permission for that test server.

Seven tests cover the no-processor version.json profile, old versionInfo
profile and checksums, preserving vanilla assets/client, replacing conflicting
library versions while retaining native classifiers, installer and embedded
artifact corruption, unsupported processors/Minecraft/Forge/main classes and
archive/metadata path traversal. Fixture class files are not Minecraft mods.

Official source inspection, 2026-10-08:

- [Forge 1.12.2 releases](https://files.minecraftforge.net/net/minecraftforge/forge/index_1.12.2.html)
  identifies 14.23.5.2864 as latest and 14.23.5.2859 as recommended.
- The 2864 installer is pinned with SHA1
  `b5ec0016c292830f2325e39417d1ec4d9e166cab`, matching its
  [official checksum](https://maven.minecraftforge.net/net/minecraftforge/forge/1.12.2-14.23.5.2864/forge-1.12.2-14.23.5.2864-installer.jar.sha1).
  It has an empty processor list, a version.json LaunchWrapper/FMLTweaker
  profile, 22 libraries and an embedded Maven Forge artifact. The 2859 format
  is the same. The 2847 installer uses versionInfo and an embedded universal.

Actual isolated smoke data is in `artifacts/forge/full-smoke/`. The official
2864 installer was downloaded automatically, all required libraries were
downloaded and verified, and installation produced `installed=true`. Its
merged metadata has 53 library rows. It reused the user's copied vanilla
1.12.2 client and assets in the isolated test root, with 1290 unique asset
objects. `prepare-launch` produced a LaunchWrapper/FMLTweaker plan using the
staged Java 8 runtime; the actual Java 8 executable also ran the launcher JAR
and prepared that plan successfully. The real 2847 installer also merged
successfully, including retrieval of missing official checksum sidecars.

This establishes launcher installation and launch preparation. It does not
establish Minecraft or Forge rendering or gameplay on PS5. Modern Forge
installer processors and other Minecraft versions remain explicitly unsupported.
