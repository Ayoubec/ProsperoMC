/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef PW_AGC_PS5_H
#define PW_AGC_PS5_H
#include "../include/prospero_win.h"
#include <stddef.h>
#include <stdint.h>

typedef struct PwAgcPs5 {
    void *command;
    int64_t physical;
    size_t bytes;
    volatile uint64_t *fence;
    uint64_t submits;
    unsigned module_loaded,reserved,allocated,mapped;
    int unmap_rc,release_rc,munmap_rc,unload_rc;
} PwAgcPs5;

int pw_agc_ps5_open(PwAgcPs5 *);
int pw_agc_ps5_close(PwAgcPs5 *);
int pw_agc_ps5_copy_flip(PwAgcPs5 *,int video_handle,int buffer_index,
                         const void *source,void *destination,uint32_t bytes,
                         uint64_t flip_arg);
#endif
