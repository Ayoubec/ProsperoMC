/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef PW_GUEST_CALL_H
#define PW_GUEST_CALL_H
#include "pw_x86_block.h"
typedef enum PwGuestConvention { PW_GUEST_CDECL=1, PW_GUEST_STDCALL=2 } PwGuestConvention;
typedef struct PwGuestCall {
    PwX86State *state;
    uint32_t entry, esp, return_pc, stack_low, stack_high;
    uint32_t nonvolatile[4]; /* EBX EBP ESI EDI */
    uint32_t fixed_bytes;
    PwGuestConvention convention;
    unsigned variadic, active;
} PwGuestCall;
/* Frame storage must be zero-initialized. The live RW guest stack remains
 * mapped for the frame lifetime. This marshals guest data; it never casts
 * a guest function address to a host function pointer. */
int pw_guest_call_begin(PwGuestCall *call,PwX86State *state,
                       PwGuestConvention convention,uint32_t fixed_bytes,int variadic);
int pw_guest_call_u32(const PwGuestCall *call,uint32_t byte_offset,uint32_t *value);
int pw_guest_call_u64(const PwGuestCall *call,uint32_t byte_offset,uint64_t *value);
/* integer_bits is 0 (void), 32 (EAX) or 64 (EDX:EAX). No floating or struct
 * returns. Failure changes neither guest state nor frame ownership. */
int pw_guest_call_finish(PwGuestCall *call,unsigned integer_bits,uint64_t value);
typedef struct PwGuestCallback {
    PwX86State *state;
    uint32_t saved_gpr[8],saved_eip,saved_flags,stack_low,stack_high;
    uint32_t saved_chain_budget,saved_step_retired,saved_step_transitions;
    uintptr_t saved_last_exit_slot;
    uint32_t saved_reg_loads,saved_reg_stores,saved_reg_reconciliations,saved_reg_spills;
    PwX86DeferredFlags saved_deferred_flags;
    uint32_t return_token,argument_bytes;
    PwGuestConvention convention;
    unsigned active;
} PwGuestCallback;
/* Schedules guest execution by changing guest EIP/ESP only. The caller must
 * run the engine and intercept its reserved return_token before instruction
 * fetch. Each nested callback needs its own zero-initialized frame. */
int pw_guest_callback_enter(PwGuestCallback *callback,PwX86State *state,
                            uint32_t target,uint32_t return_token,
                            const uint32_t *arguments,uint32_t count,
                            PwGuestConvention convention);
int pw_guest_callback_leave(PwGuestCallback *callback,unsigned integer_bits,uint64_t *result);
#endif
