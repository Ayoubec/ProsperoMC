/* SPDX-License-Identifier: LGPL-2.1-or-later */
#if defined(__linux__) && !defined(_DEFAULT_SOURCE)
#define _DEFAULT_SOURCE 1      /* MAP_ANONYMOUS under -std=c11 on glibc */
#endif

#include "pw_vm_posix.h"

#include <sys/mman.h>
#include <unistd.h>

#if !defined(MAP_ANONYMOUS) && defined(MAP_ANON)
#define MAP_ANONYMOUS MAP_ANON
#endif

static int posix_protection(unsigned protection)
{
    int flags = 0;

    if ((protection & PW_PROT_READ) != 0u)
        flags |= PROT_READ;
    if ((protection & PW_PROT_WRITE) != 0u)
        flags |= PROT_WRITE;
    if ((protection & PW_PROT_EXEC) != 0u)
        flags |= PROT_EXEC;
    return flags == 0 ? PROT_NONE : flags;
}

static size_t page_bytes(void)
{
    const long value = sysconf(_SC_PAGESIZE);

    return value > 0 ? (size_t)value : 4096u;
}

static int posix_reserve(void *context, size_t bytes, size_t alignment,
                         PwVmRegion *out)
{
    const size_t page = page_bytes();
    size_t effective;
    size_t reserved;
    size_t span;
    uint8_t *raw;
    uintptr_t aligned;
    size_t head;
    size_t tail;

    (void)context;
    if (!out || bytes == 0u || alignment == 0u ||
        (alignment & (alignment - 1u)) != 0u)
        return PW_ERR_PRECONDITION;
    /* A PE section alignment below the page size still needs page granularity. */
    effective = alignment < page ? page : alignment;
    if (bytes > (size_t)-1 - (page - 1u))
        return PW_ERR_OVERFLOW;
    /*
     * Round the reservation up to whole pages before trimming. A PE image
     * is section-aligned, commonly to 4 KiB, while the platform page can be
     * larger — 16 KiB on this console — and then the tail address below is
     * not page aligned. munmap of a misaligned address either fails, which
     * leaves the padding mapped, or is rounded into the region being kept.
     * A 4 KiB-page host never sees this, because there an image size is
     * already a whole number of pages.
     */
    reserved = (bytes + page - 1u) & ~(page - 1u);
    if (reserved > (size_t)-1 - effective)
        return PW_ERR_OVERFLOW;
    span = reserved + effective;

    raw = mmap(NULL, span, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED)
        return PW_ERR_VM;
    aligned = ((uintptr_t)raw + effective - 1u) & ~(uintptr_t)(effective - 1u);
    head = (size_t)(aligned - (uintptr_t)raw);
    tail = span - head - reserved;
    /* Both ends fall on page boundaries now: `aligned` is `effective`
     * aligned, and `effective` is itself a multiple of the page size. */
    if (head != 0u)
        (void)munmap(raw, head);
    if (tail != 0u)
        (void)munmap((uint8_t *)aligned + reserved, tail);

    out->write_base = (void *)aligned;
    out->exec_base = (void *)aligned;
    out->bytes = reserved;
    out->alignment = effective;
    out->handle = NULL;
    return PW_OK;
}

static int posix_reserve_at(void *context, uint64_t address, size_t bytes,
                            size_t alignment, PwVmRegion *out)
{
    const size_t page = page_bytes();
    const size_t effective = alignment < page ? page : alignment;
    size_t reserved;
    void *raw;

    (void)context;
    if (!out || !address || !bytes || !alignment ||
        (alignment & (alignment - 1u)) != 0u ||
        address > UINTPTR_MAX || (address & (effective - 1u)) != 0u)
        return PW_ERR_PRECONDITION;
    if (bytes > SIZE_MAX - (page - 1u))
        return PW_ERR_OVERFLOW;
    reserved = (bytes + page - 1u) & ~(page - 1u);
    if (reserved > UINTPTR_MAX - (uintptr_t)address)
        return PW_ERR_OVERFLOW;
    /* A plain hint cannot displace live mappings. Accept only an exact
     * result, and release an alternate placement before reporting failure. */
    raw = mmap((void *)(uintptr_t)address, reserved, PROT_NONE,
               MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED)
        return PW_ERR_VM;
    if ((uintptr_t)raw != (uintptr_t)address) {
        (void)munmap(raw, reserved);
        return PW_ERR_VM;
    }
    out->write_base = raw;
    out->exec_base = raw;
    out->bytes = reserved;
    out->alignment = effective;
    out->handle = NULL;
    return PW_OK;
}

static int posix_commit(void *context, const PwVmRegion *region, size_t offset,
                        size_t bytes, unsigned protection)
{
    const size_t page = page_bytes();

    (void)context;
    if (!pw_vm_region_contains(region, offset, bytes))
        return PW_ERR_PRECONDITION;
    if ((offset & (page - 1u)) != 0u)
        return PW_ERR_PRECONDITION;
    if (bytes == 0u)
        return PW_OK;
    /* Round the tail up: the reservation itself is page aligned. */
    if (bytes > region->bytes - offset)
        return PW_ERR_PRECONDITION;
    bytes = (bytes + page - 1u) & ~(page - 1u);
    if (bytes > region->bytes - offset)
        bytes = region->bytes - offset;
    if (mprotect((uint8_t *)region->write_base + offset, bytes,
                 posix_protection(protection)) != 0)
        return PW_ERR_VM;
    return PW_OK;
}

static int posix_release(void *context, PwVmRegion *region)
{
    (void)context;
    if (!region || !region->write_base)
        return PW_ERR_PRECONDITION;
    if (munmap(region->write_base, region->bytes) != 0)
        return PW_ERR_VM;
    region->write_base = NULL;
    region->exec_base = NULL;
    region->bytes = 0u;
    region->handle = NULL;
    return PW_OK;
}

int pw_vm_posix_backend(PwVmBackend *backend)
{
    if (!backend)
        return PW_ERR_PRECONDITION;
    backend->context = NULL;
    backend->capabilities = PW_VM_CAP_PROTECT | PW_VM_CAP_EXACT_ADDRESS;
    backend->page_bytes = page_bytes();
    backend->reserve = posix_reserve;
    backend->commit = posix_commit;
    backend->protect = posix_commit;
    backend->release = posix_release;
    backend->reserve_at = posix_reserve_at;
    return PW_OK;
}
