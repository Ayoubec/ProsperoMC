"""Exercise the actual public VideoOut refresh-policy control flow."""
from pathlib import Path
import re,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
class VrrPolicyTests(unittest.TestCase):
    def test_fixed_request_success_and_refusals(self):
        source=(ROOT/'vendor/prospero-win/native/pw_videoout_ps5.c').read_text()
        functions='\n'.join(re.search(r'int '+name+r'\(.*?\n\}',source,re.S).group() for name in ('pw_videoout_ps5_stable_refresh','pw_videoout_ps5_fixed_output'))
        code=r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
enum {PW_ERR_PRECONDITION=-1};
typedef struct {int opened,handle,refresh_unpeg_rc,refresh_peg_rc;} PwVideoOutPs5;
static int mode_result,unpeg_result,peg_result,stage,waits;
static int sceVideoOutConfigureOutput(int h,unsigned mode,const void *a,const void *b,const void *c){assert(h==2&&mode==1&&!a&&!b&&!c);stage=1;return mode_result;}
static int sceVideoOutVrrUnpegFromFixedRate(int h){assert(h==2);stage=2;return unpeg_result;}
static int sceVideoOutVrrPegToFixedRate(int h,uint64_t a,uint64_t b){assert(h==2&&stage==2&&!a&&!b);stage=3;return peg_result;}
static int sceVideoOutWaitVblank(int h){assert(h==2&&stage==3);waits++;return 0;}
''' + functions + r'''
int main(void){
 PwVideoOutPs5 v={1,2,0,0};
 assert(pw_videoout_ps5_stable_refresh(NULL)==PW_ERR_PRECONDITION);
 assert(!pw_videoout_ps5_fixed_output(&v)&&stage==3&&waits==2);
 waits=0;unpeg_result=(int)0x8029001cu;
 assert(!pw_videoout_ps5_fixed_output(&v)&&v.refresh_unpeg_rc==unpeg_result&&waits==2);
 waits=0;peg_result=(int)0x8029001cu;
 assert(pw_videoout_ps5_fixed_output(&v)==peg_result&&!waits&&v.refresh_peg_rc==peg_result);
 stage=0;mode_result=-50;
 assert(pw_videoout_ps5_fixed_output(&v)==-50&&stage==1&&!waits);
 v.opened=0;assert(pw_videoout_ps5_fixed_output(&v)==PW_ERR_PRECONDITION);
 return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='vrr-policy-') as tmp:
            path=Path(tmp);(path/'test.c').write_text(code)
            subprocess.run(['clang-18','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(path/'test.c'),'-o',str(path/'test')],check=True)
            subprocess.run([str(path/'test')],check=True)
        print('VRR_POLICY_PASS: fixed request, already-released state, peg/mode refusal propagated; no per-frame retry')

if __name__=='__main__':
    unittest.main()
