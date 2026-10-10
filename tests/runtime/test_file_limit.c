/* Verify the real process limit, rather than just the requested value. */
#define _DEFAULT_SOURCE
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>
#define PS5LOG_LOG(...) do { printf(__VA_ARGS__); putchar('\n'); } while (0)
#include "pm_file_limit.h"

int main(void)
{
    struct rlimit saved, low, raised;
    int files[1024];
    assert(!getrlimit(RLIMIT_NOFILE, &saved));
    low = saved;
    low.rlim_cur = 64;
    assert(!setrlimit(RLIMIT_NOFILE, &low));
    pm_prepare_file_limit();
    assert(!getrlimit(RLIMIT_NOFILE, &raised));
    assert(raised.rlim_cur >= 4096);
    for (unsigned i = 0; i < 1024; ++i) {
        files[i] = open("/dev/null", O_RDONLY);
        assert(files[i] >= 0);
    }
    errno = EACCES;
    pm_report_file_inventory();
    assert(errno == EACCES);
    for (unsigned i = 0; i < 1024; ++i) close(files[i]);
    assert(!setrlimit(RLIMIT_NOFILE, &saved));
    pm_prepare_file_limit();
    assert(!getrlimit(RLIMIT_NOFILE, &raised));
    assert(raised.rlim_cur >= saved.rlim_cur);
    puts("FILE_LIMIT_REAL_HANDLES_PASS");
    return 0;
}
