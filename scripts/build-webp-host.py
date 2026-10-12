"""Build the same decode-only source for native UI tests and previews."""
import importlib.util
from pathlib import Path
import subprocess
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('webp', ROOT / 'scripts/fetch-webp-decoder.py')
webp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(webp)
source = webp.prepare()
sanitized = '--sanitize' in sys.argv
folder = ROOT / ('build/tests/webp-sanitized' if sanitized else 'build/tests/webp')
folder.mkdir(parents=True, exist_ok=True)
compiler = shutil.which('clang-18') or shutil.which('cc')
flags = ['-std=c11', '-O2', '-DNDEBUG', '-I', str(source)]
if sanitized:
    flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
objects = []
for path in webp.sources(source):
    obj = folder / (path.name + '.o')
    if not obj.is_file() or obj.stat().st_mtime < path.stat().st_mtime:
        subprocess.run([compiler, *flags, '-c', str(path), '-o', str(obj)], check=True)
    objects.append(str(obj))
archive = folder / 'libwebpdecoder.a'
subprocess.run(['ar', 'rcs', str(archive), *objects], check=True)
print('WEBP_HOST_DECODER_BUILT', archive)
