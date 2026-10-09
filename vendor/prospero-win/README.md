# ProsperoMC Wine runtime foundation

This directory is a modified vendoring of prospero-win source
b510eb3db8709bb251d3da3c56850e96e057f489 for the Minecraft-only ProsperoMC app.

The real PS5 Wine loader, OpenGL display path, audio, USB input, DualSense,
process restarts and PS5 platform shims are retained. The upstream generic game
library scanner, catalog frontend and game recipe/transfer tools are removed.

Build and stage through the project-root scripts, not upstream release scripts:

```sh
bash scripts/build-ps5.sh
python scripts/stage-ps5.py --help
bash tests/runtime/run.sh
```

See PROSPEROMC-ADAPTATIONS.md for modifications and exact runtime provenance.
Original technical docs remain as reference for the Wine platform runtime.
Original LICENSE, LICENSING.md, NOTICE.md and THIRD_PARTY.md are preserved.
