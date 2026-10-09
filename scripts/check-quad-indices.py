"""Check Mesa's actual generated quad indices preserve winding and flat color."""
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import hashlib

root=Path(__file__).resolve().parents[1]
out=root/'artifacts/graphics-batching'
source=out/'u_indices_gen.py'
archive=root/'.deps/archives/mesa-26.2.0.tar.xz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='efd4bb08cdb7c365a812cd4e6c9202ab55b2f22cdcd13c7d6c4f9647b799a4ef'
out.mkdir(parents=True,exist_ok=True)
with tarfile.open(archive) as mesa:
    entry=next(m for m in mesa.getmembers() if m.name.endswith('/indices/u_indices_gen.py'))
    source.write_bytes(mesa.extractfile(entry).read())
subprocess.run([sys.executable,source,out/'u_indices_gen.c'],check=True)
generated=(out/'u_indices_gen.c').read_text()
functions=re.findall(r'static void (generate_quads_\w+)\(',generated)
selected=[name for name in functions if 'uint32' in name and ('last2last' in name or 'first2last' in name) and name.endswith('_tris')]
assert len(selected)==2,functions[:12]
translators=[f'translate_quads_{types}_{pv}2last_prdisable_tris'
    for types in ('uint82uint16','uint162uint16','uint322uint32') for pv in ('first','last')]
body=['#include <assert.h>','#include <stdint.h>','#include <stdio.h>']
for name in selected+translators:
    match=re.search(r'static void '+name+r'\(.*?\n\}',generated,re.S)
    assert match
    body.append(match.group())
body.append('''int main(void) {
    uint32_t indices[12];
    const int x[4]={0,1,1,0},y[4]={0,0,1,1};
''')
for name in selected:
    provoking=0 if 'first2last' in name else 3
    body.append(f'''    {name}(8,12,indices);
    for(unsigned t=0;t<4;t++) {{
        unsigned q=t/2, a=indices[t*3]-8-q*4, b=indices[t*3+1]-8-q*4, c=indices[t*3+2]-8-q*4;
        assert(a<4 && b<4 && c<4 && c=={provoking});
        assert((x[b]-x[a])*(y[c]-y[a])-(y[b]-y[a])*(x[c]-x[a])>0);
    }}
''')
for name in translators:
    input_type,output_type=re.search(r'quads_(uint\d+)2(uint\d+)_',name).groups()
    provoking=0 if '_first2last_' in name else 3
    body.append(f'''    {{
        const {input_type}_t input[8]={{4,7,2,9,17,11,23,5}};
        {output_type}_t output[12];
        {name}(input,0,8,12,0,output);
        for(unsigned t=0;t<4;t++) {{
            unsigned q=t/2, positions[3];
            for(unsigned v=0;v<3;v++) {{
                positions[v]=4;
                for(unsigned p=0;p<4;p++) if(input[q*4+p]==output[t*3+v])positions[v]=p;
                assert(positions[v]<4);
            }}
            unsigned a=positions[0],b=positions[1],c=positions[2];
            assert(c=={provoking});
            assert((x[b]-x[a])*(y[c]-y[a])-(y[b]-y[a])*(x[c]-x[a])>0);
        }}
    }}
''')
body.append('puts("PASS: Mesa indexed/unindexed quads preserve first/last colors and winding for 8/16/32-bit input indices");return 0;}')
(out/'check-quad-indices.c').write_text('\n'.join(body))
print(out/'check-quad-indices.c')
