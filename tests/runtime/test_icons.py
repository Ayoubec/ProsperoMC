"""Exercise the actual native decoder/cache against bounded image fixtures."""
import os
import base64
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[2]


def png(width, height):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = (b"\0" + bytes((255, 20, 30, 77)) * width) * height
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def main():
    subprocess.run(['python3',str(ROOT/'scripts/build-webp-host.py'),'--sanitize'],check=True)
    with tempfile.TemporaryDirectory(prefix="prosperomc-icons-") as tmp:
        base = Path(tmp)
        data = base / "data"
        data.mkdir()
        (data / "color.png").write_bytes(png(4, 2))
        (data / "large.png").write_bytes(png(512, 256))
        (data / "oversized.png").write_bytes(png(2049, 1))
        (data / "bad.png").write_bytes(b"invalid icon")
        for name,fixture in (('1KVo5zza','icon.webp'),('bHUKuhiA','icon-lossy.webp')):
            shutil.copyfile(ROOT/'tests/fixtures'/fixture,data/f'{name}.webp')
        (data/'bad.webp').write_bytes(b'RIFF'+struct.pack('<I',24)+b'WEBPVP8L'+b'\0'*16)
        # Independent 2x1 RGB JPEG fixture (blue), covering the other decoder.
        (data / "color.jpg").write_bytes(base64.b64decode(
            "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAIDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDziiiiv0M8g//Z"))
        (base / "outside.png").write_bytes(png(4, 2))
        os.symlink(base / "outside.png", data / "link.png")
        os.symlink(base, data / "linkdir")
        for n in range(96):
            shutil.copyfile(data / "color.png", data / f"entry-{n}.png")
        binary = base / "test-icons"
        compiler = os.environ.get("HOST_CC", "clang-18")
        subprocess.run([compiler, "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                        "-I", str(ROOT / "app/native"),'-I',str(ROOT/'.deps/native/libwebp/libwebp-1.6.0'), str(ROOT / "app/native/pm_icons.c"),
                        str(ROOT / "tests/runtime/test_icons.c"),str(ROOT/'build/tests/webp-sanitized/libwebpdecoder.a'), "-o", str(binary)], check=True)
        subprocess.run([str(binary), str(data)], check=True)


if __name__ == "__main__":
    main()
