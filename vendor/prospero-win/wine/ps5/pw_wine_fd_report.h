/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef PW_WINE_FD_REPORT_H
#define PW_WINE_FD_REPORT_H

/* Failure-only telemetry, once per shim module. No file is opened, closed,
 * allocated, or retried here. In particular, descriptors are not equivalent
 * to kernel open-file objects: dup shares an object, two opens of one inode
 * need not. The unique-inode count below is only a lower bound, not a cap. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <unistd.h>

typedef int (*pw_fd_path_lookup)(int, char *, size_t);
typedef int (*pw_fd_path_stat)(const char *, struct stat *);

static void pw_fd_report_write(const char *line)
{
    size_t left = strlen(line);
    while (left) {
        ssize_t sent = write(STDERR_FILENO, line, left);
        if (sent < 0 && errno == EINTR) continue;
        if (sent <= 0) break;
        line += sent;
        left -= (size_t)sent;
    }
}

static int pw_fd_suffix(const char *path, const char *suffix)
{
    size_t p = strlen(path), s = strlen(suffix), i;
    if (p < s) return 0;
    for (i = 0; i < s; ++i) {
        unsigned char c = (unsigned char)path[p - s + i];
        if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
        if (c != (unsigned char)suffix[i]) return 0;
    }
    return 1;
}

static void pw_fd_clean_path(char *out, size_t size, const char *path)
{
    size_t i;
    if (!path) path = "?";
    for (i = 0; i + 1 < size && path[i]; ++i)
        out[i] = (unsigned char)path[i] < 32 || path[i] == 127 ? '?' : path[i];
    out[i] = 0;
}

static void pw_wine_report_fd_failure(const char *operation, const char *failed_path,
                                     int flags, const void *caller,
                                     pw_fd_path_lookup lookup, pw_fd_path_stat path_stat)
{
    static int reported;
    struct { dev_t device; ino_t inode; } inodes[512];
    struct rlimit limit = {0, 0};
    unsigned int scan = 32768, fd, live = 0, regular = 0, directory = 0;
    unsigned int sockets = 0, devices = 0, other = 0, archives = 0, images = 0;
    unsigned int regions = 0, tracked = 0, stale = 0, unique = 0, saturated = 0, samples = 0;
    int saved = errno, have_limit;
    char line[1536], path[1024], clean[768];

    if ((saved != EMFILE && saved != ENFILE) ||
        __atomic_exchange_n(&reported, 1, __ATOMIC_RELAXED)) return;
    have_limit = !getrlimit(RLIMIT_NOFILE, &limit);
    if (have_limit && limit.rlim_cur < scan) scan = (unsigned int)limit.rlim_cur;
    pw_fd_clean_path(clean, sizeof(clean), failed_path);
    snprintf(line, sizeof(line), "wine-ps5: fd-exhaustion origin=%s errno=%d (%s) flags=0x%x caller=%p path=%s\n",
             operation, saved, saved == EMFILE ? "EMFILE" : "ENFILE", flags, caller, clean);
    pw_fd_report_write(line);
    for (fd = 0; fd < scan; ++fd) {
        struct stat st, named;
        unsigned int i;
        if (fstat((int)fd, &st)) continue;
        ++live;
        if (S_ISREG(st.st_mode)) ++regular;
        else if (S_ISDIR(st.st_mode)) ++directory;
        else if (S_ISSOCK(st.st_mode)) ++sockets;
        else if (S_ISCHR(st.st_mode) || S_ISBLK(st.st_mode)) ++devices;
        else ++other;
        if (S_ISREG(st.st_mode) || S_ISDIR(st.st_mode)) {
            for (i = 0; i < unique; ++i)
                if (inodes[i].device == st.st_dev && inodes[i].inode == st.st_ino) break;
            if (i == unique) {
                if (unique == sizeof(inodes) / sizeof(inodes[0])) saturated = 1;
                else { inodes[unique].device = st.st_dev; inodes[unique++].inode = st.st_ino; }
            }
        }
        if (!lookup || !path_stat || lookup((int)fd, path, sizeof(path))) continue;
        /* libc and other shim modules can close/reuse a tracked number. */
        if (path_stat(path, &named) || named.st_dev != st.st_dev || named.st_ino != st.st_ino) {
            ++stale;
            continue;
        }
        ++tracked;
        if (pw_fd_suffix(path, ".jar") || pw_fd_suffix(path, ".zip") || pw_fd_suffix(path, ".jmod")) ++archives;
        if (pw_fd_suffix(path, ".dll") || pw_fd_suffix(path, ".exe") || pw_fd_suffix(path, ".prx")) ++images;
        if (pw_fd_suffix(path, ".mca") || pw_fd_suffix(path, ".mcc")) ++regions;
        if (samples++ < 12) {
            pw_fd_clean_path(clean, sizeof(clean), path);
            snprintf(line, sizeof(line), "wine-ps5: fd-exhaustion sample fd=%u path=%s\n", fd, clean);
            pw_fd_report_write(line);
        }
    }
    snprintf(line, sizeof(line),
             "wine-ps5: fd-exhaustion census live=%u regular=%u directories=%u sockets=%u devices=%u other=%u "
             "tracked-module=%u stale-module=%u archives=%u images=%u regions=%u "
             "unique-inodes-lower-bound=%u inode-table-full=%u scan=%u rlimit-known=%d soft=%llu hard=%llu\n",
             live, regular, directory, sockets, devices, other, tracked, stale, archives, images, regions,
             unique, saturated, scan, have_limit, (unsigned long long)limit.rlim_cur,
             (unsigned long long)limit.rlim_max);
    pw_fd_report_write(line);
    errno = saved;
}
#endif
