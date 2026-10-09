/* SPDX-License-Identifier: LGPL-2.1-or-later */
/*
 * Stable, allocation-free names for result and protection codes.
 *
 * Telemetry and the host tools print these, so they are part of the
 * evidence contract: the validator matches on them.
 */
#include "../include/prospero_win.h"

const char *pw_result_name(int result)
{
    switch (result) {
    case PW_OK: return "ok";
    case PW_ERR_PRECONDITION: return "precondition";
    case PW_ERR_NOT_PE: return "not-pe";
    case PW_ERR_TRUNCATED: return "truncated";
    case PW_ERR_MALFORMED: return "malformed";
    case PW_ERR_UNSUPPORTED: return "unsupported";
    case PW_ERR_OVERFLOW: return "overflow";
    case PW_ERR_LIMIT: return "limit";
    case PW_ERR_NOT_FOUND: return "not-found";
    case PW_ERR_VM: return "vm";
    case PW_ERR_STATE: return "state";
    case PW_ERR_X87_TRAP: return "x87-trap";
    default: return "unknown";
    }
}

const char *pw_protection_name(unsigned protection)
{
    static const char *const names[8] = {
        "---", "r--", "-w-", "rw-", "--x", "r-x", "-wx", "rwx",
    };
    return names[protection & 7u];
}
