/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "../src/pw_guest_call.h"
#include "../src/pw_vm_posix.h"
#include <assert.h>
#include <string.h>
int main(void)
{
    PwVmBackend vm;PwVmRegion stack;
    assert(pw_vm_posix_backend(&vm)==PW_OK);
    assert(vm.reserve_at(NULL,0x03000000,4096,4096,&stack)==PW_OK);
    assert(vm.commit(NULL,&stack,0,4096,PW_PROT_READ|PW_PROT_WRITE)==PW_OK);
    for(unsigned abi=1;abi<=2;abi++)for(unsigned bits=0;bits<=64;bits+=32) {
        PwX86State s={0};PwGuestCall call={0};
        s.stack_low=0x03000000;s.stack_high=0x03001000;s.gpr[4]=0x03000fe0;s.eip=0xf0000000;
        s.gpr[0]=7;s.gpr[2]=8;s.eflags=0x602;
        s.gpr[3]=3;s.gpr[5]=5;s.gpr[6]=6;s.gpr[7]=7;
        uint32_t words[]={0x01001000,0x12345678,0xabcdef01,0x23456789};
        memcpy((void *)(uintptr_t)s.gpr[4],words,sizeof(words));
        assert(pw_guest_call_begin(&call,&s,(PwGuestConvention)abi,12,0)==PW_OK);
        uint32_t low=0;uint64_t wide=0;
        assert(pw_guest_call_u32(&call,0,&low)==PW_OK && low==words[1]);
        assert(pw_guest_call_u64(&call,4,&wide)==PW_OK && wide==0x23456789abcdef01ull);
        assert(pw_guest_call_u32(&call,12,&low)==PW_ERR_LIMIT && low==words[1]);
        assert(pw_guest_call_begin(&call,&s,(PwGuestConvention)abi,12,0)==PW_ERR_STATE);
        PwX86State before=s;
        assert(pw_guest_call_finish(&call,80,0)==PW_ERR_UNSUPPORTED);
        assert(memcmp(&before,&s,sizeof(s))==0 && call.active);
        s.gpr[6]++;
        assert(pw_guest_call_finish(&call,bits,0)==PW_ERR_STATE && call.active);
        s=before;
        assert(pw_guest_call_finish(&call,bits,0xfedcba9876543210ull)==PW_OK);
        assert(s.eip==words[0] && s.gpr[4]==before.gpr[4]+(abi==PW_GUEST_CDECL?4:16));
        assert(s.gpr[0]==(bits?0x76543210:7));
        assert(s.gpr[2]==(bits==64?0xfedcba98:8));
        assert(s.eflags==before.eflags && !call.active);
        assert(pw_guest_call_finish(&call,32,0)==PW_ERR_STATE);
    }
    PwX86State s={0};PwGuestCall call={0};
    s.stack_low=0x03000000;s.stack_high=0x03001000;s.gpr[4]=0x03000ff4;
    uint32_t values[]={0x100,11,22};memcpy((void *)(uintptr_t)s.gpr[4],values,12);
    assert(pw_guest_call_begin(&call,&s,PW_GUEST_STDCALL,4,1)==PW_ERR_PRECONDITION);
    assert(pw_guest_call_begin(&call,&s,PW_GUEST_CDECL,4,1)==PW_OK);
    uint32_t value=99;
    assert(pw_guest_call_u32(&call,4,&value)==PW_OK && value==22);
    assert(pw_guest_call_u32(&call,8,&value)==PW_ERR_VM && value==22);
    assert(pw_guest_call_u32(&call,UINT32_MAX,&value)==PW_ERR_VM);
    s.eip++;
    assert(pw_guest_call_u32(&call,0,&value)==PW_ERR_STATE);
    s.eip--;
    assert(pw_guest_call_finish(&call,32,1)==PW_OK);
    s.gpr[4]=s.stack_high-2;
    assert(pw_guest_call_begin(&call,&s,PW_GUEST_CDECL,0,0)==PW_ERR_VM);
    s.gpr[4]=s.stack_low;
    assert(pw_guest_call_begin(&call,&s,PW_GUEST_STDCALL,0xfffffffcu,0)==PW_ERR_VM);
    for(unsigned abi=1;abi<=2;abi++) {
        s.gpr[4]=s.stack_high-16;s.eip=0xf0000100;s.eflags=0x202;
        PwX86State saved=s;PwGuestCallback cb={0};
        uint32_t args[]={12,34};uint64_t answer=0;
        assert(pw_guest_callback_enter(&cb,&s,0x01000100,0xf1000000,args,2,(PwGuestConvention)abi)==PW_OK);
        uint32_t words[3];memcpy(words,(void *)(uintptr_t)s.gpr[4],12);
        assert(words[0]==0xf1000000 && words[1]==12 && words[2]==34);
        assert(s.eip==0x01000100);
        assert(pw_guest_callback_leave(&cb,64,&answer)==PW_ERR_STATE && cb.active);
        /* Model the guest's RET or RET 8; engine integration is separate. */
        s.gpr[4]+=abi==PW_GUEST_CDECL?4:12;s.eip=0xf1000000;
        s.gpr[0]=0x12345678;s.gpr[2]=0xabcdef01;s.eflags=0x246;
        assert(pw_guest_callback_leave(&cb,64,&answer)==PW_OK && answer==0xabcdef0112345678ull);
        assert(memcmp(&s,&saved,sizeof(s))==0 && !cb.active);
        assert(pw_guest_callback_leave(&cb,64,&answer)==PW_ERR_STATE);
        s.gpr[4]=s.stack_low;
        assert(pw_guest_callback_enter(&cb,&s,1,2,args,2,(PwGuestConvention)abi)==PW_ERR_VM);
    }
    assert(vm.release(NULL,&stack)==PW_OK);
    return 0;
}
