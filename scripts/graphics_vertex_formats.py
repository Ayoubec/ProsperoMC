"""Native integer vertex fetches shared by Gallium and the PSBC compiler.

Append compiler enum values to preserve the existing SDK ABI. RADV's existing
vertex-input lowering implements the actual signed/unsigned GPU loads; Mesa
must see the same supported formats instead of translating buffers per draw.
"""
from pathlib import Path
import difflib
import hashlib

FORMATS = (
    'R8_SINT', 'R8G8_SINT', 'R8G8B8A8_SINT',
    'R16_UINT', 'R16G16_UINT', 'R16G16B16_UINT', 'R16G16B16A16_UINT',
    'R16_SINT', 'R16G16_SINT', 'R16G16B16_SINT', 'R16G16B16A16_SINT',
)
ORIGINAL = {
    'psbc_compile.c': '8b382fba804fd6b23be31bd5e726af2fa136cc456396d3c7e942227168c03273',
    'psbc_compile.h': 'b1194d8fb20fd103fefc57ada6c69990676b949fecbab34742d87c60716e4644',
}

def replace_once(source, anchor, replacement):
    if source.count(anchor) != 1:
        raise ValueError('Integer vertex patch anchor changed: ' + anchor[:70])
    return source.replace(anchor, replacement, 1)

def patch_driver(source):
    cases = ''.join('   case PIPE_FORMAT_' + name + ':\n' for name in FORMATS)
    anchor = 'ps5_integer_vertex_format(enum pipe_format format)\n{\n   switch (format) {\n'
    source = replace_once(source, anchor, anchor + cases)
    anchor = 'ps5_vertex_format(enum pipe_format format, PsbcVertexFormat *out)\n{\n   switch (format) {\n'
    mappings = ''.join('   case PIPE_FORMAT_' + name + ':\n'
                      '      *out = PSBC_VERTEX_FORMAT_' + name + ';\n'
                      '      return PS5_ENABLE_INTEGER_VERTEX_CANDIDATE;\n'
                      for name in FORMATS)
    source = replace_once(source, anchor, anchor + mappings)
    anchor = 'ps5_vertex_format_alignment(enum pipe_format format)\n{\n   switch (format) {\n'
    alignments = ''.join('   case PIPE_FORMAT_' + name + ':\n' for name in FORMATS[:3])
    alignments += '      return 1;\n'
    alignments += ''.join('   case PIPE_FORMAT_' + name + ':\n' for name in FORMATS[3:])
    alignments += '      return 2;\n'
    return replace_once(source, anchor, anchor + alignments)

def compiler_text(original, name):
    if hashlib.sha256(original.encode()).hexdigest() != ORIGINAL[name]:
        raise ValueError('Compiler input is not the verified platform source: ' + name)
    if name.endswith('.h'):
        anchor = '    PSBC_VERTEX_FORMAT_R8G8_SNORM,\n} PsbcVertexFormat;'
        return replace_once(original, anchor, '    PSBC_VERTEX_FORMAT_R8G8_SNORM,\n'
                            '    /* ABI extension: native packed integer vertex inputs. */\n' +
                            ''.join('    PSBC_VERTEX_FORMAT_' + fmt + ',\n' for fmt in FORMATS) +
                            '} PsbcVertexFormat;')
    anchor = '    case PSBC_VERTEX_FORMAT_R8G8_SNORM: return PIPE_FORMAT_R8G8_SNORM;'
    return replace_once(original, anchor, anchor + '\n' + ''.join(
        '    case PSBC_VERTEX_FORMAT_' + fmt + ': return PIPE_FORMAT_' + fmt + ';\n'
        for fmt in FORMATS).rstrip('\n'))

def patch_compiler(directory, patch_path):
    directory, patch_path = Path(directory), Path(patch_path)
    diff = ''
    for name in ORIGINAL:
        path = directory / 'libpsbc' / name
        current = path.read_text()
        if name.endswith('.h'):
            addition = '    /* ABI extension: native packed integer vertex inputs. */\n' + ''.join(
                '    PSBC_VERTEX_FORMAT_' + fmt + ',\n' for fmt in FORMATS)
        else:
            addition = '\n' + ''.join('    case PSBC_VERTEX_FORMAT_' + fmt +
                ': return PIPE_FORMAT_' + fmt + ';\n' for fmt in FORMATS).rstrip('\n')
        original = current.replace(addition, '', 1) if addition in current else current
        updated = compiler_text(original, name)
        path.write_text(updated)
        diff += ''.join(difflib.unified_diff(original.splitlines(True), updated.splitlines(True),
            fromfile='a/third_party/opengnm-psbc/libpsbc/' + name,
            tofile='b/third_party/opengnm-psbc/libpsbc/' + name))
    patch_path.write_text(diff)
    return patch_path
