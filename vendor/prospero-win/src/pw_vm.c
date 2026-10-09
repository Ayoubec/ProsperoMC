/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "../include/prospero_win_vm.h"

int pw_vm_backend_valid(const PwVmBackend *backend)
{
    if (!backend || !backend->reserve || !backend->commit ||
        !backend->release)
        return 0;
    if ((backend->capabilities & PW_VM_CAP_PROTECT) != 0u && !backend->protect)
        return 0;
    if ((backend->capabilities & PW_VM_CAP_EXACT_ADDRESS) != 0u &&
        !backend->reserve_at)
        return 0;
    if (backend->page_bytes == 0u ||
        (backend->page_bytes & (backend->page_bytes - 1u)) != 0u)
        return 0;
    return 1;
}

int pw_vm_region_contains(const PwVmRegion *region, size_t offset,
                          size_t bytes)
{
    if (!region || !region->write_base)
        return 0;
    if (bytes > region->bytes)
        return 0;
    return offset <= region->bytes - bytes;
}
