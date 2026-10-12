The Controlify-enabled Fabulously Optimized startup failed before loading SDL:
Fabric could not open a processed nested JAR for its resource pack roots.
Wine reported `Too many open files` with 941 live descriptors, including
468 regular-file descriptors, against a descriptor limit of 12,555.
Successful runs with Controlify disabled retained 451 regular descriptors.
This points to archive-open pressure rather than a proven SDL dependency
failure. The separate PS5 kernel file-object budget has not yet been measured.

The previous experimental PS5 launch path presented ordinary dependency libraries
as directories under `/data/ProsperoMC/cache/classpath-v1/<SHA256>/content`.
Each original JAR gets its own directory in the same classpath position;
classes, ordinary resources, and `META-INF/services` remain separate and
unchanged. Game, launcher, loader, and mod JARs remain archives. Original
libraries and worlds are never rewritten or deleted.

The cache conservatively preserves signed, sealed, Multi-Release, indexed,
nested-JAR, mod, loader, and manifest `Class-Path` archives. It also preserves
libraries with package Implementation/Specification manifest attributes,
whose package metadata would differ when loaded from directories. Unsafe
paths, Windows case/device-name collisions, oversized archives, corruption,
and unavailable cache storage fall back to the original JAR. Extraction is
bounded, CRC checked, and published only after an atomic ready marker. Reuse
checks every cached resource's size and CRC against the verified original
archive and rejects extra files or links. Initial extraction and integrity
checks add startup work; the purpose is to reduce retained file objects.

A real host Java fixture keeps a classloader alive while loading classes,
forty resources, and a ServiceLoader provider. The original archives retained
35 additional process handles; the directory classpath retained none. The
fixture also verifies cache repair and conservative archive guards:

```sh
python -m unittest tests.launcher.test_classpath_cache -v
```

This experimental dependency-classpath change is independent of Minecraft
version or mod loader. It does not patch Controlify, remove mods, or claim
its controller backend is console-validated. Launch logs report the number
of converted dependencies so console descriptor measurements can show the
actual savings and reveal any subsequent controller-library error. It is no
longer enabled for game launches: the console still exhausted files, and its
directory extraction/revalidation added substantial startup work. Original
dependencies keep their normal archive paths and package metadata; existing
cache directories are left in place but are absent from the launch classpath.

The launcher backend disables its `JarURLConnection` resource cache to release
its own short-lived resource streams. The game retains the loader's normal URL
cache. Disabling that game cache caused repeated archive verification during
Knot class loading: console samples at 45, 120 and 240 seconds remained inside
JAR reads and verification. The measured forty-handle saving in the isolated
host fixture therefore does not establish a usable game fix. No JAR is rewritten,
merged or forcibly closed. Console save and full-pack compatibility remain
pending; neither cache experiment establishes that file exhaustion is solved.
