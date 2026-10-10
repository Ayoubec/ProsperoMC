ProsperoMC uses stb_image 2.30 to decode locally cached PNG/JPEG instance icons.

Upstream: https://github.com/nothings/stb/tree/f0569113c93ad095470c54bf34a17b36646bbbb5

`stb_image.h` SHA-256: `594c2fe35d49488b4382dbfaec8f98366defca819d916ac95becf3e75f4200b3`.
The upstream header includes its MIT/public-domain license. Only PNG and JPEG
decoders are compiled; icon input size and dimensions are bounded in pm_icons.c.
