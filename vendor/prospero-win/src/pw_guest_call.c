/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "pw_guest_call.h"
#include <string.h>

static int live_frame(const PwGuestCall *call)
{
    if(!call || !call->active || !call->state)return PW_ERR_STATE;
    const PwX86State *s=call->state;
    if(s->gpr[4]!=call->esp || s->eip!=call->entry ||
       s->stack_low!=call->stack_low || s->stack_high!=call->stack_high)
        return PW_ERR_STATE;
    return PW_OK;
}
int pw_guest_call_begin(PwGuestCall *call,PwX86State *state,
                       PwGuestConvention convention,uint32_t fixed_bytes,int variadic)
{
    if(!call || !state || (fixed_bytes&3) ||
       (convention!=PW_GUEST_CDECL && convention!=PW_GUEST_STDCALL) ||
       (variadic!=0 && variadic!=1) || (variadic && convention!=PW_GUEST_CDECL))
        return PW_ERR_PRECONDITION;
    if(call->active)return PW_ERR_STATE;
    uint32_t esp=state->gpr[4];
    if(!esp || esp<state->stack_low || (uint64_t)esp+4+fixed_bytes>state->stack_high)
        return PW_ERR_VM;
    PwGuestCall next={0};
    next.state=state;next.entry=state->eip;next.esp=esp;
    next.stack_low=state->stack_low;next.stack_high=state->stack_high;
    memcpy(&next.return_pc,(const void *)(uintptr_t)esp,4);
    next.nonvolatile[0]=state->gpr[3];next.nonvolatile[1]=state->gpr[5];
    next.nonvolatile[2]=state->gpr[6];next.nonvolatile[3]=state->gpr[7];
    next.fixed_bytes=fixed_bytes;next.convention=convention;
    next.variadic=(unsigned)variadic;next.active=1;*call=next;
    return PW_OK;
}
static int read_arg(const PwGuestCall *call,uint32_t offset,void *out,unsigned bytes)
{
    int status=live_frame(call);
    if(status!=PW_OK)return status;
    if(!out)return PW_ERR_PRECONDITION;
    if(!call->variadic && (uint64_t)offset+bytes>call->fixed_bytes)return PW_ERR_LIMIT;
    uint64_t address=(uint64_t)call->esp+4+offset;
    if(address+bytes>call->stack_high)return PW_ERR_VM;
    memcpy(out,(const void *)(uintptr_t)address,bytes);
    return PW_OK;
}
int pw_guest_call_u32(const PwGuestCall *call,uint32_t offset,uint32_t *value)
{ return read_arg(call,offset,value,4); }
int pw_guest_call_u64(const PwGuestCall *call,uint32_t offset,uint64_t *value)
{ return read_arg(call,offset,value,8); }
int pw_guest_call_finish(PwGuestCall *call,unsigned bits,uint64_t value)
{
    int status=live_frame(call);
    if(status!=PW_OK)return status;
    if(bits!=0 && bits!=32 && bits!=64)return PW_ERR_UNSUPPORTED;
    PwX86State *s=call->state;
    if(s->gpr[3]!=call->nonvolatile[0] || s->gpr[5]!=call->nonvolatile[1] ||
       s->gpr[6]!=call->nonvolatile[2] || s->gpr[7]!=call->nonvolatile[3])return PW_ERR_STATE;
    uint32_t pop=4+(call->convention==PW_GUEST_STDCALL?call->fixed_bytes:0);
    if((uint64_t)call->esp+pop>call->stack_high)return PW_ERR_VM;
    if(bits)s->gpr[0]=(uint32_t)value;
    if(bits==64)s->gpr[2]=(uint32_t)(value>>32);
    s->gpr[4]=call->esp+pop;s->eip=call->return_pc;
    call->active=0;
    return PW_OK;
}
int pw_guest_callback_enter(PwGuestCallback *cb,PwX86State *s,uint32_t target,
                            uint32_t token,const uint32_t *args,uint32_t count,
                            PwGuestConvention convention)
{
    if(!cb || !s || !target || !token || (count && !args) ||
       (convention!=PW_GUEST_CDECL && convention!=PW_GUEST_STDCALL))return PW_ERR_PRECONDITION;
    if(cb->active)return PW_ERR_STATE;
    uint64_t bytes=(uint64_t)count*4,total=bytes+4;
    uint32_t esp=s->gpr[4];
    if(esp>s->stack_high || total>esp || esp-total<s->stack_low || esp-total==0)
        return PW_ERR_VM;
    PwGuestCallback next={0};
    next.state=s;memcpy(next.saved_gpr,s->gpr,sizeof(s->gpr));
    next.saved_eip=s->eip;next.saved_flags=s->eflags;
    next.stack_low=s->stack_low;next.stack_high=s->stack_high;
    next.saved_chain_budget=s->chain_budget;
    next.saved_step_retired=s->step_retired;
    next.saved_step_transitions=s->step_transitions;
    next.saved_last_exit_slot=s->last_exit_slot;
    next.saved_reg_loads=s->reg_loads;
    next.saved_reg_stores=s->reg_stores;
    next.saved_reg_reconciliations=s->reg_reconciliations;
    next.saved_reg_spills=s->reg_spills;
    next.saved_deferred_flags=s->deferred_flags;
    next.return_token=token;next.argument_bytes=(uint32_t)bytes;
    next.convention=convention;next.active=1;
    uint32_t new_esp=esp-(uint32_t)total;
    if(count)memmove((void *)(uintptr_t)(new_esp+4),args,(size_t)bytes);
    memcpy((void *)(uintptr_t)new_esp,&token,4);
    s->gpr[4]=new_esp;s->eip=target;*cb=next;
    return PW_OK;
}
int pw_guest_callback_leave(PwGuestCallback *cb,unsigned bits,uint64_t *result)
{
    if(!cb || !cb->active || !cb->state)return PW_ERR_STATE;
    if(!result || (bits!=0 && bits!=32 && bits!=64))return PW_ERR_PRECONDITION;
    PwX86State *s=cb->state;
    uint32_t expected=cb->saved_gpr[4]-(cb->convention==PW_GUEST_CDECL?cb->argument_bytes:0);
    if(s->eip!=cb->return_token || s->gpr[4]!=expected ||
       s->stack_low!=cb->stack_low || s->stack_high!=cb->stack_high ||
       s->gpr[3]!=cb->saved_gpr[3] || s->gpr[5]!=cb->saved_gpr[5] ||
       s->gpr[6]!=cb->saved_gpr[6] || s->gpr[7]!=cb->saved_gpr[7])return PW_ERR_STATE;
    uint64_t value=bits?s->gpr[0]:0;
    if(bits==64)value|=(uint64_t)s->gpr[2]<<32;
    memcpy(s->gpr,cb->saved_gpr,sizeof(s->gpr));
    s->eip=cb->saved_eip;s->eflags=cb->saved_flags;
    s->chain_budget=cb->saved_chain_budget;
    s->step_retired=cb->saved_step_retired;
    s->step_transitions=cb->saved_step_transitions;
    s->last_exit_slot=cb->saved_last_exit_slot;
    s->reg_loads=cb->saved_reg_loads;
    s->reg_stores=cb->saved_reg_stores;
    s->reg_reconciliations=cb->saved_reg_reconciliations;
    s->reg_spills=cb->saved_reg_spills;
    s->deferred_flags=cb->saved_deferred_flags;
    cb->active=0;*result=value;return PW_OK;
}
