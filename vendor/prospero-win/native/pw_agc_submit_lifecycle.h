/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef PW_AGC_SUBMIT_LIFECYCLE_H
#define PW_AGC_SUBMIT_LIFECYCLE_H

#include <stdint.h>

typedef int32_t (*PwAgcSubmitDcbFn)(void *);
typedef int32_t (*PwAgcSuspendPointFn)(void);

/* Submit work, then establish the platform suspension point.  This does not
 * replace fence or VideoOut retirement and must only run once the command
 * bytes have been made visible to the GPU. */
int pw_agc_submit_and_suspend(void *description,PwAgcSubmitDcbFn submit,
                              PwAgcSuspendPointFn suspend_point);

#endif
