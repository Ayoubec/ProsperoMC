/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef PW_X87_H
#define PW_X87_H
#include "pw_guest_fp.h"
#include <stddef.h>
#include <stdint.h>

typedef enum PwX87Action {
    PW_X87_FLD_F32,
    PW_X87_FLD_F64,
    PW_X87_FILD_I32,
    PW_X87_FLD_ST,
    PW_X87_FLD1,
    PW_X87_FLDZ,
    PW_X87_FST_F32,
    PW_X87_FSTP_F32,
    PW_X87_FST_F64,
    PW_X87_FSTP_F64,
    PW_X87_FST_ST,
    PW_X87_FSTP_ST,
    PW_X87_FNSTSW_AX,
    PW_X87_FABS,
    PW_X87_FCHS,
    PW_X87_FSQRT,
    PW_X87_FSIN,
    PW_X87_FCOS,
    PW_X87_FACOS,
    PW_X87_FADD_F32,
    PW_X87_FADD_F64,
    PW_X87_FADD_ST,
    PW_X87_FADD_TO_ST,
    PW_X87_FADDP_ST,
    PW_X87_FMUL_F32,
    PW_X87_FMUL_F64,
    PW_X87_FMUL_ST,
    PW_X87_FMUL_TO_ST,
    PW_X87_FMULP_ST,
    PW_X87_FSUB_F32,
    PW_X87_FSUB_F64,
    PW_X87_FSUB_ST,
    PW_X87_FSUBR_ST,
    PW_X87_FSUB_TO_ST,
    PW_X87_FSUBR_TO_ST,
    PW_X87_FSUBP_ST,
    PW_X87_FSUBR_F32,
    PW_X87_FSUBR_F64,
    PW_X87_FDIV_F32,
    PW_X87_FDIV_F64,
    PW_X87_FDIV_ST,
    PW_X87_FDIV_TO_ST,
    PW_X87_FDIVR_TO_ST,
    PW_X87_FDIVR_F32,
    PW_X87_FDIVR_F64,
    PW_X87_FDIVP_ST,
    PW_X87_FDIVRP_ST,
    PW_X87_FCOM_F32,
    PW_X87_FCOM_F64,
    PW_X87_FCOM_ST,
    PW_X87_FCOMP_ST,
    PW_X87_FCOMPP,
    PW_X87_FCOMP_F32,
    PW_X87_FCOMP_F64,
    PW_X87_FUCOMPP
} PwX87Action;

/* Execute one isolated guest x87 data-transfer operation. `operand` is a
 * validated host alias for memory forms, a logical ST index for register
 * forms, and ignored for constants/status. All conversion arithmetic is
 * integer-only and never installs guest state in the host FP environment. */
int pw_x87_execute(PwGuestFp *,PwX87Action,uintptr_t operand,uint16_t *ax);
#endif
