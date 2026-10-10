/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PM_FILE_LIMIT_H
#define PM_FILE_LIMIT_H

#include <errno.h>
#include <sys/resource.h>

/* Fabric keeps its nested mod JARs open. Wine's in-process server skips
 * the normal server init_limits(), so prepare the title before Wine starts.
 * This affects only this process; no system-wide limits are changed. */
static void pm_prepare_file_limit(void)
{
    struct rlimit before, requested, after;
    int error = 0;
    if (getrlimit(RLIMIT_NOFILE, &before)) {
        PS5LOG_LOG("PROSPEROMC file-limit query failed errno=%d", errno);
        return;
    }
    if (before.rlim_cur < 4096) {
        requested = before;
        requested.rlim_cur = 4096;
        if (requested.rlim_max < requested.rlim_cur)
            requested.rlim_max = requested.rlim_cur;
        if (setrlimit(RLIMIT_NOFILE, &requested)) {
            error = errno;
            /* An unprivileged title may still raise its soft limit to its
             * existing hard limit, without permission to raise the latter. */
            requested = before;
            requested.rlim_cur = before.rlim_max < 4096 ? before.rlim_max : 4096;
            if (requested.rlim_cur > before.rlim_cur && !setrlimit(RLIMIT_NOFILE, &requested))
                error = 0;
        }
    }
    if (getrlimit(RLIMIT_NOFILE, &after)) {
        PS5LOG_LOG("PROSPEROMC file-limit readback failed errno=%d", errno);
        return;
    }
    PS5LOG_LOG("PROSPEROMC file-limit before=%llu hard=%llu after=%llu hard=%llu target=4096 errno=%d",
        (unsigned long long)before.rlim_cur, (unsigned long long)before.rlim_max,
        (unsigned long long)after.rlim_cur, (unsigned long long)after.rlim_max, error);
}

#endif
