"""Extract the verified SDK prefix and its own source snapshot locally."""
from pathlib import Path
import tarfile
import json
import argparse

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--archive', type=Path, default=root / '.deps/archives/ps5-opengl-sdk-1.0.1.tar.gz')
parser.add_argument('--output', type=Path, default=root / '.deps/graphics-sdk-1.0.1')
args = parser.parse_args()
destination = args.output.resolve()
assert destination.is_relative_to(root / '.deps'), 'SDK output must remain in workspace dependencies'
destination.mkdir(exist_ok=True)
prefix = None
with tarfile.open(args.archive, mode='r|gz') as archive:
    for member in archive:
        if prefix is None:
            prefix = member.name.split('/')[0] + '/'
        relative = member.name.removeprefix(prefix)
        if not member.isfile() or not (relative.startswith('sdk/') or relative in ('provenance.json', 'consumer-validation.json', 'sources/ps5-opengl.tar')):
            continue
        target = destination / relative
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError('SDK archive path outside destination')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.extractfile(member).read())
print((destination / 'provenance.json').read_text())
source = destination / 'sources/ps5-opengl.tar'
with tarfile.open(source) as archive:
    for member in archive:
        if member.isfile() and member.name.endswith('src/gallium/ps5/ps5_screen.c'):
            data = archive.extractfile(member).read()
            (destination / 'ps5_screen.c').write_bytes(data)
            print('SDK_BGRA_CAPABILITY_FIX', b'!(format == PIPE_FORMAT_B8G8R8A8_UNORM && (bindings & PIPE_BIND_SAMPLER_VIEW))' in data)
