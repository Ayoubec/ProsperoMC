/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Exercise the real CWD wrappers with an actually exhausted RLIMIT_NOFILE. */
#include "pw_wine_cwd.h"
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <unistd.h>

int __real_open(const char *, int, ...);
int __real_close(int);
int __real_unlink(const char *);
int __real_rmdir(const char *);

static char jar_path[1024], region_path[1024], directory[1024];
static pthread_barrier_t ready, exhausted;

static int visit(const char *name, void *context)
{
    (void)name;
    (void)context;
    return 0;
}

static void attempt(const char *operation)
{
    unsigned int flags;
    errno = 0;
    if (!strcmp(operation, "open")) assert(open(jar_path, O_RDONLY) == -1);
    else if (!strcmp(operation, "openat")) assert(openat(AT_FDCWD, jar_path, O_RDONLY) == -1);
    else if (!strcmp(operation, "fopen")) assert(!fopen(jar_path, "rb"));
    else if (!strcmp(operation, "opendir")) assert(!opendir(directory));
    else if (!strcmp(operation, "directory-scan"))
        assert(pw_cwd_scan_directory(AT_FDCWD, directory, visit, NULL, &flags) == -1);
    else assert(0);
    /* fstat, path validation and the stderr writes must not replace EMFILE. */
    assert(errno == EMFILE);
}

static void *worker(void *context)
{
    pthread_barrier_wait(&ready);
    pthread_barrier_wait(&exhausted);
    attempt(context);
    return NULL;
}

int main(int argc, char **argv)
{
    struct rlimit original, limited;
    char folder[] = "/tmp/prosperomc-fd-XXXXXX";
    int descriptors[128], count = 0, fd;
    pthread_t threads[8];
    unsigned int i;
    int concurrent;

    assert(argc == 2);
    concurrent = !strcmp(argv[1], "concurrent");
    assert(mkdtemp(folder));
    snprintf(directory, sizeof(directory), "%s", folder);
    snprintf(jar_path, sizeof(jar_path), "%s/runtime.jar", folder);
    snprintf(region_path, sizeof(region_path), "%s/r.0.0.mca", folder);
    assert((fd = __real_open(jar_path, O_WRONLY | O_CREAT | O_EXCL, 0600)) >= 0);
    assert(!__real_close(fd));
    assert((fd = __real_open(region_path, O_WRONLY | O_CREAT | O_EXCL, 0600)) >= 0);
    assert(!__real_close(fd));
    /* Prevent unrelated missing symlink-table probes from winning the origin. */
    pw_cwd_probe_directory(directory);
    assert(!getrlimit(RLIMIT_NOFILE, &original));
    assert(original.rlim_cur >= 64);
    limited = original;
    limited.rlim_cur = 64;
    if (concurrent) {
        assert(!pthread_barrier_init(&ready, NULL, 9));
        assert(!pthread_barrier_init(&exhausted, NULL, 9));
        for (i = 0; i < 8; ++i) assert(!pthread_create(&threads[i], NULL, worker, "open"));
        pthread_barrier_wait(&ready);
    }
    assert(!setrlimit(RLIMIT_NOFILE, &limited));
    assert((fd = open(region_path, O_RDONLY)) >= 0);
    descriptors[count++] = fd;
    assert((fd = open(jar_path, O_RDONLY)) >= 0);
    descriptors[count++] = fd;
    assert((fd = dup(fd)) >= 0);
    descriptors[count++] = fd;
    pw_cwd_track(fd, jar_path);
    assert((fd = __real_open(region_path, O_RDONLY)) >= 0);
    descriptors[count++] = fd;
    pw_cwd_track(fd, jar_path); /* stale record: inode mismatch must be rejected */
    while ((fd = __real_open(jar_path, O_RDONLY)) >= 0) {
        assert(count < (int)(sizeof(descriptors) / sizeof(descriptors[0])));
        descriptors[count++] = fd;
        pw_cwd_track(fd, jar_path);
    }
    assert(errno == EMFILE);
    /* Only the requested wrapper reports; filler failures bypass the shim. */
    if (!concurrent) attempt(argv[1]);
    else {
        pthread_barrier_wait(&exhausted);
        for (i = 0; i < 8; ++i) assert(!pthread_join(threads[i], NULL));
    }
    assert(!setrlimit(RLIMIT_NOFILE, &original));
    for (i = 0; i < (unsigned int)count; ++i) assert(!close(descriptors[i]));
    /* Ordinary errors still retain their own errno and do not report again. */
    errno = 0;
    assert(open("/prosperomc-fd-fixture-missing-file", O_RDONLY) == -1 && errno == ENOENT);
    assert(!__real_unlink(jar_path));
    assert(!__real_unlink(region_path));
    assert(!__real_rmdir(directory));
    return 0;
}
