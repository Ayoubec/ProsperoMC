"""Bake OFL Montserrat into a small dependency-free native bitmap atlas."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

p = argparse.ArgumentParser()
p.add_argument("font", type=Path)
p.add_argument("output", type=Path)
a = p.parse_args()
font = ImageFont.truetype(str(a.font), 48)
data, glyphs = [], []
for ch in range(32, 127):
    left, top, right, bottom = font.getbbox(chr(ch), anchor="ls")
    width, height = max(1, right-left), max(1, bottom-top)
    img = Image.new("L", (width, height))
    ImageDraw.Draw(img).text((-left, -top), chr(ch), font=font, fill=255, anchor="ls")
    glyphs.append((len(data), width, height, left, top, round(font.getlength(chr(ch)))))
    data.extend(img.tobytes())
lines = ["/* Montserrat Medium raster atlas; font licensed SIL OFL 1.1. */",
         "typedef struct PmGlyph { unsigned offset; short width,height,left,top,advance; } PmGlyph;",
         "static const PmGlyph pm_glyphs[95] = {"]
lines.extend("{%s}," % ",".join(map(str, g)) for g in glyphs)
lines += ["};", "static const unsigned char pm_font_pixels[] = {"]
lines.extend(",".join(map(str, data[i:i+32]))+"," for i in range(0, len(data), 32))
lines += ["};", ""]
a.output.write_text("\n".join(lines), encoding="utf-8")
print("Generated", a.output, "with", len(data), "coverage bytes")
