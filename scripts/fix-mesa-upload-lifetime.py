"""Preserve every retired upload until driver binding, then release per draw."""
from pathlib import Path
import difflib
import hashlib
import sys

root = Path(__file__).resolve().parents[1]
path = Path(sys.argv[1])
source = path.read_text()
changes = [
    ("uint32_t misaligned, struct pipe_resource **releasebuf)",
     "uint32_t misaligned, unsigned *release_count, struct pipe_resource **releasebufs)"),
    ("         err = u_vbuf_translate_buffers(mgr, &key[type], info, draw,",
     "         struct pipe_resource *releasebuf = NULL;\n"
     "         err = u_vbuf_translate_buffers(mgr, &key[type], info, draw,"),
    ("unroll_indices && type == VB_VERTEX, releasebuf);\n         if (err != PIPE_OK)",
     "unroll_indices && type == VB_VERTEX, &releasebuf);\n"
     "         /* Keep earlier translated buffers alive until driver binding. */\n"
     "         if (releasebuf)\n"
     "            releasebufs[(*release_count)++] = releasebuf;\n"
     "         if (err != PIPE_OK)"),
    ("   struct pipe_resource *releasebuf = NULL;\n   struct pipe_resource *releasebufs[PIPE_MAX_ATTRIBS];",
     "   struct pipe_resource *releasebufs[PIPE_MAX_ATTRIBS + VB_NUM];"),
    ("min_index, unroll_indices, misaligned, &releasebuf))",
     "min_index, unroll_indices, misaligned, &release_count, releasebufs))"),
    ("      if (info->increment_draw_id)\n         drawid_offset++;\n   }\n\n   if (mgr->using_translate)",
     "      if (info->increment_draw_id)\n         drawid_offset++;\n"
     "      /* The driver now owns references to all bound vertex buffers.\n"
     "       * Do not overwrite retired uploader references on the next draw. */\n"
     "      for (unsigned i = 0; i < release_count; i++)\n"
     "         pipe_resource_release(pipe, releasebufs[i]);\n"
     "      release_count = 0;\n"
     "   }\n\n   if (mgr->using_translate)"),
    ("out:\n   pipe_resource_release(pipe, releasebuf);\n   for (unsigned i = 0; i < release_count; i++)",
     "out:\n   for (unsigned i = 0; i < release_count; i++)"),
    ("   unsigned rcount = 0;", "   unsigned rcount = *release_count;"),
]
for indent in ('         ', '      '):
    changes.append((
        indent + 'if (!real_vb->buffer.resource)\n' + indent + '   return PIPE_ERROR_OUT_OF_MEMORY;\n\n' +
        indent + 'if (releasebufs[rcount])\n' + indent + '   rcount++;',
        indent + 'if (releasebufs[rcount])\n' + indent + '   rcount++;\n' +
        indent + '*release_count = rcount;\n' +
        indent + 'if (!real_vb->buffer.resource)\n' + indent + '   return PIPE_ERROR_OUT_OF_MEMORY;'))
if "Do not overwrite retired uploader references" in source:
    for old, new in reversed(changes):
        if source.count(new) == 1:
            source = source.replace(new, old)
        else:
            assert source.count(old) == 1, new
before = source
assert hashlib.sha256(before.encode()).hexdigest() == '6a08427dd61ee10ecb3e5280ff8890f449043f06d4a4e228a643dcf21fdca5d6', 'Unexpected Mesa platform source; review before patching'
for old, new in changes:
    assert source.count(old) == 1, old
    source = source.replace(old, new)
path.write_text(source)
out = root / 'artifacts/graphics-batching'
(out / 'u_vbuf.c').write_text(source)
prefix = 'a/third_party/mesa-26.2.0/src/gallium/auxiliary/util/u_vbuf.c'
patch = ''.join(difflib.unified_diff(before.splitlines(True), source.splitlines(True),
                                  fromfile=prefix, tofile=prefix.replace('a/', 'b/', 1)))
combined = out / 'smooth-legacy-batching.patch'
base = combined.read_text().split('--- ' + prefix)[0]
combined.write_text(base + patch)
print('Patched Mesa upload ownership: per-type retention and per-draw release')
