/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "../native/pw_agc_submit_lifecycle.h"
#include "../include/prospero_win.h"
#include <assert.h>
#include <stdint.h>

static unsigned sequence,submit_order,suspend_order,submits,suspends;
static int32_t submit_result,suspend_result;

static int32_t mock_submit(void *description)
{
    assert(description==(void *)(uintptr_t)0x1234u);
    submit_order=++sequence;submits++;return submit_result;
}
static int32_t mock_suspend(void)
{
    suspend_order=++sequence;suspends++;return suspend_result;
}
static void reset(void)
{
    sequence=submit_order=suspend_order=submits=suspends=0;
    submit_result=suspend_result=0;
}
int main(void)
{
    void *description=(void *)(uintptr_t)0x1234u;
    reset();
    assert(pw_agc_submit_and_suspend(description,mock_submit,mock_suspend)==PW_OK);
    assert(submits==1u && suspends==1u && submit_order<suspend_order);

    reset();submit_result=-77;
    assert(pw_agc_submit_and_suspend(description,mock_submit,mock_suspend)==PW_ERR_STATE);
    assert(submits==1u && suspends==0u);

    reset();suspend_result=-88;
    assert(pw_agc_submit_and_suspend(description,mock_submit,mock_suspend)==PW_ERR_STATE);
    assert(submits==1u && suspends==1u);

    reset();
    assert(pw_agc_submit_and_suspend(NULL,mock_submit,mock_suspend)==PW_ERR_PRECONDITION);
    assert(pw_agc_submit_and_suspend(description,NULL,mock_suspend)==PW_ERR_PRECONDITION);
    assert(pw_agc_submit_and_suspend(description,mock_submit,NULL)==PW_ERR_PRECONDITION);
    assert(submits==0u && suspends==0u);
    return 0;
}
