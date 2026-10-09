"""Run the pinned upstream concurrency tests against our generated runtime."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile

root=Path(__file__).resolve().parents[1]
ci=root/'.deps/graphics-sdk-ci-738f94c/extracted'
provenance=json.loads((ci/'provenance.json').read_text())
archive=ci/'sources/ps5-opengl.tar'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==provenance['source_archives']['ps5-opengl.tar']
out=root/'artifacts/graphics-batching/upstream-async-check'
source=out/'src/platform/ps5_agc_native_runtime.c'
source.parent.mkdir(parents=True,exist_ok=True)
source.write_bytes((root/'artifacts/graphics-batching/ps5_agc_native_runtime.c').read_bytes())
tests=[]
with tarfile.open(archive) as tar:
    for name in ('test_async_preflight.py','test_async_native_draw.py'):
        entry=next(m for m in tar.getmembers() if m.name.endswith('/tests/ps5/'+name))
        target=out/'tests/ps5'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(tar.extractfile(entry).read())
        tests.append(target)
with (out/'checks.log').open('w') as log:
    for path in tests:
        subprocess.run([sys.executable,str(path)],cwd=out,stdout=log,stderr=log,check=True)
print('PASS: pinned upstream tests on patched runtime: one/two workers, state ownership, reversed completion, ring wrap, startup/affinity failure, ordered submission, tessellation drain and shutdown (ASan/UBSan)')
