/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "pw_agc_submit_lifecycle.h"
#include "../include/prospero_win.h"

int pw_agc_submit_and_suspend(void *description,PwAgcSubmitDcbFn submit,
                              PwAgcSuspendPointFn suspend_point)
{
    if(!description || !submit || !suspend_point)return PW_ERR_PRECONDITION;
    if(submit(description))return PW_ERR_STATE;
    /* A successful submit owns in-flight storage even if suspension fails;
     * callers therefore retain their ordinary fence/retirement path. */
    if(suspend_point())return PW_ERR_STATE;
    return PW_OK;
}
