/* SPDX-License-Identifier: LGPL-2.1-or-later */
/*
 * Virtual-memory contract for manual mapping.
 *
 * A backend reserves one contiguous span per image, then commits and
 * protects sub-ranges of it. The measured FW 12.02 backend uses one mapping
 * and supports mprotect from RW to RX. Two aliases remain an optional
 * backend capability: writes go to write_base and execution to exec_base,
 * which are equal unless PW_VM_CAP_ALIASED_EXEC is advertised.
 *
 * Consequence for callers: a base relocation delta is computed against
 * exec_base, the address the code will observe, and the patched bytes are
 * written through write_base. Mixing the two is the defect this split
 * exists to make impossible to write by accident.
 */
#ifndef PROSPERO_WIN_VM_H
#define PROSPERO_WIN_VM_H

#include "prospero_win.h"

/* Backend capabilities. */
enum {
    /* exec_base is a distinct mapping of the same pages as write_base. */
    PW_VM_CAP_ALIASED_EXEC = 1u << 0,
    /* protect() can change a committed range in place. */
    PW_VM_CAP_PROTECT = 1u << 1,
    /* reserve_at succeeds only at the requested exec address, without replacement. */
    PW_VM_CAP_EXACT_ADDRESS = 1u << 2,
};

typedef struct PwVmRegion {
    void *write_base;     /* readable and writable while mapping is in progress */
    void *exec_base;      /* address the image runs from; equals write_base
                           * unless PW_VM_CAP_ALIASED_EXEC is set */
    size_t bytes;
    size_t alignment;
    void *handle;         /* backend-owned bookkeeping */
} PwVmRegion;

typedef struct PwVmBackend {
    void *context;
    unsigned capabilities;
    /*
     * Protection granularity. This is not always the PE section alignment:
     * PE images are routinely laid out on 4 KiB boundaries while a console
     * mapping is coarser, so two sections can share one protectable page
     * and the mapper has to apply the union of their protections. The count
     * of pages that needed a union is reported, never hidden.
     */
    size_t page_bytes;
    int (*reserve)(void *context, size_t bytes, size_t alignment,
                   PwVmRegion *out);
    int (*commit)(void *context, const PwVmRegion *region, size_t offset,
                  size_t bytes, unsigned protection);
    int (*protect)(void *context, const PwVmRegion *region, size_t offset,
                   size_t bytes, unsigned protection);
    int (*release)(void *context, PwVmRegion *region);
    /* Optional, read only when PW_VM_CAP_EXACT_ADDRESS is set. On failure
     * no mapping is retained and out is unchanged. Never replace an existing
     * reservation. bytes may be rounded up to the backend page size. */
    int (*reserve_at)(void *context, uint64_t address, size_t bytes,
                      size_t alignment, PwVmRegion *out);
} PwVmBackend;

/* True when every required entry point is present. */
int pw_vm_backend_valid(const PwVmBackend *backend);

/* Checks that offset+bytes stays inside region without wrapping. */
int pw_vm_region_contains(const PwVmRegion *region, size_t offset,
                          size_t bytes);

#endif
