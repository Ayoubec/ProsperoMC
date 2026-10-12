"""Verify only the intended draw-driver/native-backend objects change."""
from pathlib import Path
import hashlib
import json

root=Path(__file__).resolve().parents[1]
def members(path):
    result={};names=b''
    with path.open('rb') as source:
        assert source.read(8)==b'!<arch>\n'
        while header:=source.read(60):
            assert len(header)==60 and header[58:]==b'`\n'
            name=header[:16].decode().strip();size=int(header[48:58])
            data=source.read(size)
            assert len(data)==size
            if size&1:source.read(1)
            if name=='//':names=data
            elif name not in ('/','/SYM64/'):
                if name.startswith('/') and name[1:].isdigit():
                    name=names[int(name[1:]):].split(b'/\n',1)[0].decode()
                else:name=name.rstrip('/')
                assert name not in result
                result[name]=hashlib.sha256(data).hexdigest()
    return result
before=root/'.deps/graphics-sdk-ci-738f94c/extracted/sdk/lib'
after=root/'.deps/graphics-sdk-batching/sdk/lib'
a=members(before/'libps5_opengl_core33.a');b=members(after/'libps5_opengl_core33.a')
assert a.keys()==b.keys()
assert [name for name in a if a[name]!=b[name]]==['ps5_screen.o','ps5_agc_runtime_backend.o']
a_comp=members(before/'libpsbc.ps5.a');b_comp=members(after/'libpsbc.ps5.a')
assert a_comp.keys()==b_comp.keys()
assert [name for name in a_comp if a_comp[name]!=b_comp[name]]==['psbc_compile.ps5.o']
a_gallium=members(before/'libgallium.a');b_gallium=members(after/'libgallium.a')
assert a_gallium.keys()==b_gallium.keys()
assert [name for name in a_gallium if a_gallium[name]!=b_gallium[name]]==['util_u_vbuf.c.o']
provenance=json.loads((root/'.deps/graphics-sdk-batching/provenance.json').read_text())
if not provenance['draw_profile']:
    driver=(root/'artifacts/graphics-batching/ps5_screen.o').read_bytes()
    native=(root/'artifacts/graphics-batching/ps5_agc_runtime_backend.o').read_bytes()
    assert hashlib.sha256(driver).hexdigest()==b['ps5_screen.o']
    assert hashlib.sha256(native).hexdigest()==b['ps5_agc_runtime_backend.o']
    assert b'[ps5-driver-cycles]' not in driver
    assert b'[ps5-prepare-perf]' not in native
    assert b'profile=0' in driver
    assert b'ps5_agc_gate2_batch_end' in native
    assert (b'[prosperomc-batch-time]' in native) == provenance.get('batch_timings',False)
    if provenance.get('async_native_prepare'):
        assert b'[ps5-async-prep] cpu=' in native
        assert b'pthread_create' in native and b'pthread_join' in native
message='PASS: only draw driver, native runtime backend, integer-format compiler and owned Mesa vertex uploader changed; every other archive member remains from verified CI SDK'
(root/'artifacts/graphics-batching/archive-check.log').write_text(message+'\n')
print(message)
