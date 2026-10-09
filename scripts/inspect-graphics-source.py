"""Fetch pinned Mesa format data and official graphics SDK release metadata."""
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request

root = Path(__file__).resolve().parent.parent
output = root / 'artifacts/graphics-source'
output.mkdir(parents=True, exist_ok=True)
request = urllib.request.Request('https://api.github.com/repos/blackbearreloaded/ps5-opengl/releases/latest', headers={'User-Agent': 'ProsperoMC-source-inspection'})
with urllib.request.urlopen(request, timeout=30) as response:
    release = json.load(response)
(output / 'release.json').write_text(json.dumps(release, indent=2))
print('SDK_RELEASE', release['tag_name'])
for asset in release['assets']:
    print('SDK_ASSET', asset['name'], asset['size'], asset['browser_download_url'])
dependency = json.loads((root / '.deps/source/ps5-opengl/dependencies.json').read_text())['mesa']
archive = root / '.deps/archives/mesa-26.2.0.tar.xz'
if not archive.exists():
    urllib.request.urlretrieve(dependency['url'], archive)
assert hashlib.sha256(archive.read_bytes()).hexdigest() == dependency['sha256'], 'Mesa archive hash mismatch'
with tarfile.open(archive) as source:
    for member in source.getmembers():
        if member.name.endswith(('/pipe/p_format.h', '/format/u_formats.h', '/format/u_format.csv', '/format/u_format_table.py')):
            data = source.extractfile(member).read()
            (output / Path(member.name).name).write_bytes(data)
            print('FORMAT_SOURCE', member.name, len(data))
