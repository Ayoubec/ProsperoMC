"""Verify the renderer archive changes only the intended draw driver object."""
from pathlib import Path
import hashlib

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
assert [name for name in a if a[name]!=b[name]]==['ps5_screen.o']
assert hashlib.sha256((before/'libpsbc.ps5.a').read_bytes()).digest()==hashlib.sha256((after/'libpsbc.ps5.a').read_bytes()).digest()
message='PASS: only ps5_screen.o changed; every other runtime object and compiler library remains from verified CI SDK'
(root/'artifacts/graphics-batching/archive-check.log').write_text(message+'\n')
print(message)
