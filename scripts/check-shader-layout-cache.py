"""Test real native cache matching, ELF validation and cached draw routing."""
from pathlib import Path
import re
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
s=(root/'artifacts/graphics-batching/ps5_agc_native_runtime.c').read_text()
def function(name):
    return re.search(r'static int '+name+r'\(.*?\n\}',s,re.S).group()
structure=s[s.index('static struct runtime_shader_pair {'):s.index('/* Prepared draws write every')]
# Drop worker-lock macros from this host fixture; the lookup body is unchanged.
structure=structure[:structure.index('#ifdef PS5_ASYNC_NATIVE_PREP')]+s[s.index('static uint64_t runtime_pair_lookups,'):s.index('/* Prepared draws write every')]
start=s.index('    uintptr_t key =',s.index('static struct runtime_shader_pair *runtime_shader_pair_get_unlocked'))
end=s.index('    if (runtime_shader_pair_count ==',start)
lookup=s[start:end]
start=s.index('    int shader_packages_cached = 0;')
end=s.index('    if (runtime_hs_package &&',start)
routing=s[start:end]
start=s.index('    if (!shader_packages_cached &&\n',start)
end=s.index('    if (runtime_hs_package &&',start)
routing=(routing+s[start:end]).replace('goto cleanup;', 'return -1;')
# The section layout assignment is the actual insertion, tested against owned
# snapshots so reused caller addresses never become cached metadata pointers.
start=s.index('    p.vs_header = p.source +')
end=s.index('    memcpy(p.memory + vs_header_at',start)
assignment=s[start:end]
c=r'''
#include <assert.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define PS5_NATIVE_TITLE_RUNTIME 1
#define PS5_MULTIDRAW_BATCH 1
#define LOG_PREFIX "fixture"
static const uint8_t *runtime_vs_package,*runtime_ps_package,*runtime_hs_package;
static unsigned runtime_vs_package_len,runtime_ps_package_len;
static uint32_t runtime_primitive_type=4;
#define VS_PACKAGE runtime_vs_package
#define VS_PACKAGE_LEN runtime_vs_package_len
#define PS_PACKAGE runtime_ps_package
#define PS_PACKAGE_LEN runtime_ps_package_len
'''+structure+r'''
static unsigned parses,validations;
'''+function('shader_sections').replace('    uint64_t section_offset;', '    ++parses;\n    uint64_t section_offset;')+'\n'+function('validate_shader_header').replace('    uint32_t magic,', '    ++validations;\n    uint32_t magic,')+r'''
static struct runtime_shader_pair *runtime_shader_pair_get(const void *agc, int direct,
 const void *a,size_t b,const void *d,size_t e,const void *f,size_t g,const void *h,size_t i) {
 (void)direct;(void)a;(void)b;(void)d;(void)e;(void)f;(void)g;(void)h;(void)i;
'''+lookup+r'''
 return NULL;
}
static int route(void) {
 const uint8_t *vs_header=NULL,*vs_code=NULL,*ps_header=NULL,*ps_code=NULL;
 size_t vs_header_size=0,vs_code_size=0,ps_header_size=0,ps_code_size=0;
 struct runtime_shader_pair *prepared=NULL;
'''+routing+r'''
 return shader_packages_cached;
}
static void put16(uint8_t *p,unsigned v){uint16_t n=v;memcpy(p,&n,2);}
static void put32(uint8_t *p,unsigned v){uint32_t n=v;memcpy(p,&n,4);}
static void put64(uint8_t *p,unsigned v){uint64_t n=v;memcpy(p,&n,8);}
static void package(uint8_t *p,unsigned stage) {
 memset(p,0,640);memcpy(p,"\177ELF",4);put64(p+40,64);put16(p+58,64);put16(p+60,4);put16(p+62,1);
 static const char names[]="\0.shstrtab\0.shader_header\0.shader_text\0";
 memcpy(p+320,names,sizeof(names));
 put32(p+128,1);put64(p+128+24,320);put64(p+128+32,sizeof(names));
 put32(p+192,11);put64(p+192+24,384);put64(p+192+32,96);
 put32(p+256,26);put64(p+256+24,512);put64(p+256+32,16);
 put32(p+384,0x34333231);put32(p+388,24);put64(p+392,32);
 put32(p+448,96);put32(p+452,16);p[384+0x5a]=stage;
}
int main(void) {
 uint8_t vs[640],ps[640];package(vs,2);package(ps,1);
 runtime_vs_package=vs;runtime_ps_package=ps;runtime_vs_package_len=runtime_ps_package_len=640;
 assert(route()==0 && parses==2 && validations==2 && !runtime_shader_pair_count);
 struct runtime_shader_pair p={.vs_key=vs,.ps_key=ps,.vs_size=640,.ps_size=640,.primitive=4};
 p.source=malloc(1280);assert(p.source);memcpy(p.source,vs,640);memcpy(p.source+640,ps,640);
 const uint8_t *vs_header=vs+384,*vs_code=vs+512,*ps_header=ps+384,*ps_code=ps+512;
 size_t vs_header_size=96,vs_code_size=16,ps_header_size=96,ps_code_size=16;
'''+assignment+r'''
 runtime_shader_pairs[0]=p;runtime_shader_pair_count=1;
 for(unsigned n=0;n<10000;n++)assert(route()==1);
 assert(parses==2 && validations==2 && runtime_pair_hot_hits>9990);
 assert(p.vs_header==p.source+384 && p.ps_header==p.source+640+384);
 vs[512]^=1;assert(route()==0 && parses==4);vs[512]^=1;
 ps[512]^=1;assert(route()==0);ps[512]^=1;
 vs[0]=0;assert(route()==-1);vs[0]=127;
 ps[384+0x5a]=2;assert(route()==-1);ps[384+0x5a]=1;
 runtime_primitive_type=6;assert(route()==0);runtime_primitive_type=4;
 assert(route()==1);
 free(p.source);
 puts("PASS: 10000 byte-identical cached draws perform no ELF parse or header validation; changed content, malformed packages, stage changes and topology changes take original validation; metadata owns its bytes");
}
'''
with tempfile.TemporaryDirectory(prefix='prosperomc-shader-cache-') as tmp:
    path=Path(tmp);(path/'check.c').write_text(c)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(path/'check.c'),'-o',str(path/'check')],check=True)
    subprocess.run([str(path/'check')],check=True)
