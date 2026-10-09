"""Download official graphics SDK and exact currently bundled driver source."""
import hashlib
import json
from pathlib import Path
import urllib.request
import tarfile

root = Path(__file__).resolve().parent.parent
archives = root / '.deps/archives'
release = json.loads((root / 'artifacts/graphics-source/release.json').read_text())
for asset in release['assets']:
    if not asset['name'].startswith('ps5-opengl-sdk-'):
        continue
    target = archives / asset['name']
    if not target.exists():
        urllib.request.urlretrieve(asset['browser_download_url'], target)
    print('DOWNLOADED', target.name, target.stat().st_size, flush=True)
sdk = archives / 'ps5-opengl-sdk-1.0.1.tar.gz'
checksum = (archives / 'ps5-opengl-sdk-1.0.1.tar.gz.sha256').read_text().split()[0]
assert hashlib.sha256(sdk.read_bytes()).hexdigest() == checksum
with tarfile.open(sdk) as archive:
    names = archive.getnames()
    (root / 'artifacts/graphics-source/sdk-files.txt').write_text('\n'.join(names))
print('SDK_HASH_VERIFIED', checksum, flush=True)
revision = 'b696cd39d63a4e346da3c680a31238b41ae359a8'
source = archives / ('ps5-opengl-' + revision + '.tar.gz')
if not source.exists():
    urllib.request.urlretrieve('https://api.github.com/repos/mpereiraesaa/ps5-opengl/tarball/' + revision, source)
destination = root / '.deps/source' / ('ps5-opengl-' + revision)
destination.mkdir(exist_ok=True)
with tarfile.open(source) as archive:
    prefix = archive.getnames()[0].split('/')[0] + '/'
    for member in archive:
        if member.isfile():
            relative = member.name.removeprefix(prefix)
            target = destination / relative
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError('Archive path outside graphics source')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
print('PINNED_GRAPHICS_SOURCE', revision, hashlib.sha256(source.read_bytes()).hexdigest(), flush=True)
