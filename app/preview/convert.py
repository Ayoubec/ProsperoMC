"""Convert the real CPU framebuffer previews from PPM into PNG."""
from pathlib import Path
import argparse
from PIL import Image
p = argparse.ArgumentParser()
p.add_argument("directory", type=Path, nargs="?", default=Path("artifacts/frontend"))
a = p.parse_args()
for path in a.directory.glob("*.ppm"):
    out = path.with_suffix(".png")
    Image.open(path).save(out)
    print(out)
