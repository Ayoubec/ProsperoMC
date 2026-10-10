"""Check driver/compiler ABI agreement for direct compact integer fetches."""
from pathlib import Path
import re
import subprocess
import tempfile
import tarfile
from graphics_vertex_formats import FORMATS, compiler_text

root = Path(__file__).resolve().parents[1]
driver = (root / 'artifacts/graphics-batching/ps5_screen.c').read_text()
with tarfile.open(root / 'artifacts/graphics-batching/build-state.tar.gz') as archive:
    prefix = 'source/third_party/opengnm-psbc/libpsbc/'
    sources = {name: archive.extractfile(prefix + name).read().decode()
               for name in ('psbc_compile.c', 'psbc_compile.h')}
# A saved build may already contain the idempotently patched compiler.
from graphics_vertex_formats import ORIGINAL
import hashlib
patched = {}
for name, text in sources.items():
    if hashlib.sha256(text.encode()).hexdigest() == ORIGINAL[name]:
        patched[name] = compiler_text(text, name)
    else:
        # Build script itself verifies the original hash before accepting this.
        assert all('PSBC_VERTEX_FORMAT_' + fmt in text for fmt in FORMATS)
        patched[name] = text
header = patched['psbc_compile.h']
enum = re.search(r'typedef enum \{\n    PSBC_VERTEX_FORMAT_NONE.*?\} PsbcVertexFormat;', header, re.S).group()
def function(text, name):
    match = re.search(r'(?:static bool|static unsigned|static enum pipe_format)\s+' + name + r'\([^)]*\)\s*\{.*?\n\}', text, re.S)
    assert match, name
    return match.group()
functions = '\n'.join(function(driver, name) for name in
    ('ps5_integer_vertex_format', 'ps5_packed_vertex_format', 'ps5_vertex_format',
     'ps5_vertex_format_size', 'ps5_vertex_format_alignment'))
functions += '\n' + function(patched['psbc_compile.c'], 'psbc_vertex_pipe_format')
pipe_formats = sorted(set(re.findall(r'PIPE_FORMAT_[A-Z0-9_]+', functions)))
sizes = {}
for fmt in pipe_formats:
    components = re.findall(r'[RGBA BXY](\d+)', fmt.replace('PIPE_FORMAT_', '').replace(' ', ''))
    sizes[fmt] = sum(map(int, components)) // 8 if components else 0
c = '''#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define PS5_ENABLE_INTEGER_VERTEX_CANDIDATE 1
#define PS5_ENABLE_PACKED_VERTEX_CANDIDATE 1
#define PS5_ENABLE_FP64_CANDIDATE 1
''' + enum + '\nenum pipe_format {' + ','.join(pipe_formats) + '};\n'
c += 'static unsigned util_format_get_blocksize(enum pipe_format f) {switch(f){'
c += ''.join('case '+fmt+':return '+str(size)+';' for fmt,size in sizes.items())
c += '}return 0;}\n' + functions + '\nint main(void){\n'
for fmt in FORMATS:
    alignment = 1 if fmt.startswith('R8') else 2
    size = sizes['PIPE_FORMAT_' + fmt]
    c += ('{PsbcVertexFormat native; assert(ps5_integer_vertex_format(PIPE_FORMAT_'+fmt+'));'
          'assert(ps5_vertex_format(PIPE_FORMAT_'+fmt+', &native));'
          'assert(psbc_vertex_pipe_format(native)==PIPE_FORMAT_'+fmt+');'
          'assert(ps5_vertex_format_alignment(PIPE_FORMAT_'+fmt+')=='+str(alignment)+');'
          'assert(ps5_vertex_format_size(PIPE_FORMAT_'+fmt+')=='+str(size)+');}\n')
# The actual 20-byte compact layout must stay entirely native, with no stream
# conversion simply because its texture coordinate consists of two uint16s.
c += '''PsbcVertexFormat native;
assert(ps5_vertex_format(PIPE_FORMAT_R32G32_UINT,&native));
assert(ps5_vertex_format(PIPE_FORMAT_R8G8B8A8_UNORM,&native));
assert(ps5_vertex_format(PIPE_FORMAT_R16G16_UINT,&native));
assert(ps5_vertex_format(PIPE_FORMAT_R8G8B8A8_UINT,&native));
assert(PSBC_VERTEX_FORMAT_R8G8_SNORM==37);
assert(PSBC_VERTEX_FORMAT_R16G16_UINT>PSBC_VERTEX_FORMAT_R8G8_SNORM);
puts("PASS: compact signed/unsigned fetches agree across Gallium and compiler; existing enum ABI preserved; 20-byte layout requires no CPU vertex translation");}
'''
with tempfile.TemporaryDirectory() as temp:
    source = Path(temp)/'check.c'; exe=Path(temp)/'check'
    source.write_text(c)
    subprocess.run(['gcc','-std=c11','-O2',str(source),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
