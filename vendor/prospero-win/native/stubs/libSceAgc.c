/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Link-only import facade; firmware supplies these implementations. */
#include <stdint.h>
#define U(x) ((void)(x))
int32_t sceAgcInit(void *s,uint32_t n){U(s);U(n);return -1;}
int32_t sceAgcSuspendPoint(void){return -1;}
uint32_t *sceAgcDcbDmaData(void *w,uint32_t a,uint32_t ds,uint32_t p,uint64_t d,
    uint32_t ss,uint32_t q,uint64_t s,uint32_t n,uint32_t rw,uint32_t dw,uint32_t sync)
{U(w);U(a);U(ds);U(p);U(d);U(ss);U(q);U(s);U(n);U(rw);U(dw);U(sync);return 0;}
uint32_t *sceAgcDcbSetFlip(void *w,uint32_t h,int32_t i,uint32_t m,int64_t a)
{U(w);U(h);U(i);U(m);U(a);return 0;}
