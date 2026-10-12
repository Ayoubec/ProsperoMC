"""Prepare the pinned, decode-only native WebP source for pack artwork."""
from pathlib import Path
import hashlib
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SHA = 'e4ab7009bf0629fd11982d4c2aa83964cf244cffba7347ecd39019a9e38c4564'
SOURCE = ROOT / '.deps/native/libwebp/libwebp-1.6.0'

def prepare():
    archive = ROOT / '.deps/archives/libwebp-1.6.0.tar.gz'
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        url = 'https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-1.6.0.tar.gz'
        data = urllib.request.urlopen(url, timeout=30).read(8 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != SHA:
            raise ValueError('Unexpected official WebP archive')
        archive.write_bytes(data)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA:
        raise ValueError('WebP source checksum mismatch')
    if not (SOURCE / 'src/webp/decode.h').is_file():
        SOURCE.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as stream:
            stream.extractall(SOURCE.parent, filter='data')
    return SOURCE

def sources(source=SOURCE):
    # Follow the upstream decode-only Makefiles. Encoder/demux utilities and
    # threading are not needed by the bounded launcher icon cache.
    result = sorted((source / 'src/dec').glob('*.c'))
    for folder in ('dsp', 'utils'):
        for line in (source / ('src/' + folder + '/Makefile.am')).read_text().splitlines():
            if line.startswith('COMMON_SOURCES += ') and line.endswith('.c'):
                result.append(source / ('src/' + folder) / line.split()[-1])
    # The normal compiler target exposes SSE2; use upstream guarded dispatch.
    for line in (source / 'src/dsp/Makefile.am').read_text().splitlines():
        if line.startswith(('libwebpdspdecode_sse2_la_SOURCES += ',
                            'libwebpdspdecode_sse41_la_SOURCES += ',
                            'libwebpdspdecode_avx2_la_SOURCES += ')) and line.endswith('.c'):
            result.append(source / 'src/dsp' / line.split()[-1])
    return sorted(set(result))

if __name__ == '__main__':
    import sys
    source = prepare()
    if '--sources' in sys.argv:
        print('\n'.join(str(p) for p in sources(source)))
    else:
        print('WEBP_DECODER_SOURCE_VERIFIED', SHA)
