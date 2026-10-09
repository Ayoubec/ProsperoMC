/* SPDX-License-Identifier: LGPL-2.1-or-later */
.text
.globl _start
_start:
    pushl $-1
    pushl $0x11223344
    call target
target:
    /* Output the guest stack after call, then terminate via Linux i386 ABI. */
    movl %esp, %ecx
    movl $12, %edx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
    movl $0xfffffff0, %eax
    movl $3, %ecx
    leal 0x20(%eax,%ecx,8), %edx
    pushl %edx
    movl %esp, %ecx
    movl $4, %edx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
/*
 * FS-prefixed absolute operands. The translated engine executes
 * "mov edi, fs:[0x18]" / "mov fs:[0x1c], edi" against the guest's own FS
 * base; here the host kernel installs a real 32-bit FS base through
 * set_thread_area (i386 syscall 243), so the oracle is native i386 code and
 * not a second implementation of the same arithmetic.
 */
    leal tls_block, %eax
    pushl $0x11                 /* seg_32bit | limit_in_pages */
    pushl $0xfffff              /* limit, in pages */
    pushl %eax                  /* base_addr */
    pushl $0xffffffff           /* entry_number: let the kernel choose */
    movl %esp, %ebx
    movl $243, %eax             /* __NR_set_thread_area */
    int $0x80
    cmpl $0, %eax
    jne tls_failed
    movl (%esp), %eax           /* selected GDT entry number */
    shll $3, %eax
    orl $3, %eax                /* selector = index*8 | RPL 3 */
    movw %ax, %fs
    addl $16, %esp
    movl $0x11223344, %fs:0x18
    movl %fs:0x18, %edi
    movl %edi, %fs:0x1c
    movl %fs:0x1c, %esi
    pushl %esi
    pushl %edi
    movl %esp, %ecx
    movl $8, %edx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
/*
 * LOCK-prefixed read-modify-write. Wine's critical sections use exactly
 * "lock add [mem], 1", and the translated engine emits the same host
 * prefix, so this value is the architectural result to match.
 */
    lock addl $1, lock_target
    movl lock_target, %eax
    pushl %eax
    movl %esp, %ecx
    movl $4, %edx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
/*
 * LOCK CMPXCHG to memory: the word is compared with the accumulator and the
 * source register is stored into it when they are equal. Two shapes, because
 * they are different behaviour: one where they are equal (the word takes the
 * source, EAX does not move and ZF is set) and one where they are not (the
 * word keeps its value and EAX takes what was there). Each reports the word,
 * the accumulator and the arithmetic flags, so an engine that got the store,
 * the accumulator or the flags wrong differs here.
 */
    movl $0x11223344, cmpxchg_target
    movl $0x11223344, %eax
    movl $0xaabbccdd, %edx
    lock cmpxchgl %edx, cmpxchg_target
    pushfl
    popl %ecx
    andl $0x8d5, %ecx
    pushl %ecx
    pushl %eax
    pushl cmpxchg_target
    movl %esp, %ecx
    movl $12, %edx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
    addl $12, %esp
    movl $0x11223344, cmpxchg_target
    movl $0x55667788, %eax
    movl $0x11111111, %edx
    lock cmpxchgl %edx, cmpxchg_target
    pushfl
    popl %ecx
    andl $0x8d5, %ecx
    pushl %ecx
    pushl %eax
    pushl cmpxchg_target
    movl %esp, %ecx
    movl $12, %edx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
    addl $12, %esp
/*
 * The accumulator's byte forms: "movb %al, target" stores only the low byte,
 * and "movb target, %al" replaces only it. ntdll's own locale code publishes
 * the code page it selected this way, so the value printed here is the
 * architectural one to match: only AL moves, the upper 24 bits stay.
 */
    movl $0x112233aa, %eax
    movb %al, byte_target
    movl $0x55667700, %eax
    movb byte_target, %al
    pushl %eax
    movl %esp, %ecx
    movl $4, %edx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
    addl $4, %esp
/*
 * Bit test and conditional move: "btsl %ecx, %eax" sets a bit and reports
 * the previous one in CF, and "cmovel %esi, %edx" moves only when ZF is set.
 * Both are re-emitted by the translated engine, so these are the values to
 * match.
 */
    movl $0x100, %eax
    movl $4, %ecx
    btsl %ecx, %eax
    movl $0x55, %edx
    movl $0xaa, %esi
    cmpl $0x55, %edx
    cmovel %esi, %edx
    pushl %edx
    pushl %eax
    movl %esp, %ecx
    movl $8, %edx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
    addl $8, %esp
/*
 * XCHG to memory: the operand and the register exchange values and the
 * instruction writes no flags, so the flags "xorl %eax,%eax" left behind (ZF
 * and PF, 0x44) must still be there afterwards. Three words are printed - the
 * flags after the exchange, the register and the word - so a translation that
 * only stored, that left the register alone, or that announced flags of its
 * own differs here.
 */
    movl $0x11223344, xchg_target
    movl $0xaabbccdd, %edx
    xorl %eax, %eax
    xchgl %edx, xchg_target
    pushfl
    popl %eax
    andl $0x8d5, %eax
    pushl %eax
    pushl %edx
    pushl xchg_target
    movl %esp, %ecx
    movl $12, %edx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
    addl $12, %esp
/*
 * The SSE lane. Every register the sequence reads is written by the sequence
 * itself first, so the host CPU's initial XMM state is irrelevant: the bytes
 * this prints are lanes, a lane mask and an extracted word, produced by real
 * native i386 instructions rather than by the emitter that is under test.
 */
    movl $sse_in, %esi
    movl $sse_out, %edi
    movdqu (%esi), %xmm0            /* 16 bytes in                      */
    movl $0x00010002, %eax
    movd %eax, %xmm1                /* one dword, upper lanes zeroed     */
    paddw %xmm1, %xmm0              /* 16-bit lanes add with wrap        */
    pshufd $0x00, %xmm0, %xmm2      /* broadcast the low lane            */
    punpckldq %xmm2, %xmm2          /* interleave low dwords             */
    movdqa %xmm0, %xmm3
    pand %xmm2, %xmm3               /* byte-wise and of the lanes        */
    movups %xmm3, (%edi)            /* 16 bytes out                      */
    pmovmskb %xmm3, %edx            /* one bit per lane sign             */
    pextrw $3, %xmm3, %ecx          /* lane 3's low word                 */
    movl %edx, sse_out+16
    movl %ecx, sse_out+20
    movl $24, %edx
    movl $sse_out, %ecx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
    movl $0, %ebx
    movl $1, %eax
    int $0x80
tls_failed:
    /* Report the failure loudly instead of faulting through a null base. */
    movl $2, %ebx
    movl $4, %eax
    int $0x80
    movl $1, %ebx
    movl $1, %eax
    int $0x80
.data
.align 4
lock_target:
    .long 5
.align 4
cmpxchg_target:
    .long 0
.align 4
byte_target:
    .long 0
.align 4
xchg_target:
    .long 0
.align 16
sse_in:
    .byte 0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08
    .byte 0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f,0x10
.bss
.align 16
tls_block:
    .space 256
.align 16
sse_out:
    .space 24
.section .note.GNU-stack,"",@progbits
