/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Link-only import facade; firmware supplies these implementations. */
#include <stdint.h>
int32_t sceAgcDriverSubmitDcb(void *d){(void)d;return -1;}
uint32_t sceAgcDriverGetWaitRenderingPacketSizeInDwords(void){return 0;}
uint32_t sceAgcDriverWaitUntilSafeForRendering(uint32_t **c,uint32_t n,uint32_t r,
    uint32_t h,int32_t i){(void)c;(void)n;(void)r;(void)h;(void)i;return 1;}
