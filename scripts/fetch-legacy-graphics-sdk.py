"""Fetch the official CI SDK containing documented legacy draw fixes."""
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request
import zipfile

root = Path(__file__).resolve().parent.parent
metadata = json.loads((root / 'artifacts/graphics-source/ci-artifacts.json').read_text())
artifact = next(a for a in metadata['artifacts'] if a['name'] == 'ps5-opengl-4.6-sdk')
target = root / '.deps/archives/ps5-opengl-ci-738f94c.zip'
urls = [artifact['archive_download_url'],
        'https://nightly.link/blackbearreloaded/ps5-opengl/actions/runs/37710162111/ps5-opengl-4.6-sdk.zip']
if not target.exists():
    for url in urls:
        try:
            urllib.request.urlretrieve(url, target)
            break
        except urllib.error.HTTPError as error:
            print('DOWNLOAD_ENDPOINT', error.code, flush=True)
    else:
        raise RuntimeError('CI SDK download unavailable')
expected = artifact['digest'].removeprefix('sha256:')
assert hashlib.sha256(target.read_bytes()).hexdigest() == expected, 'CI artifact does not match official GitHub digest'
print('OFFICIAL_CI_DIGEST_VERIFIED', expected, flush=True)
destination = root / '.deps/graphics-sdk-ci-738f94c'
destination.mkdir(exist_ok=True)
with zipfile.ZipFile(target) as archive:
    for member in archive.infolist():
        if member.is_dir():
            continue
        path = destination / member.filename
        if not path.resolve().is_relative_to(destination.resolve()):
            raise ValueError('CI archive path outside destination')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(archive.read(member))
        print('CI_FILE', member.filename, member.file_size, flush=True)
