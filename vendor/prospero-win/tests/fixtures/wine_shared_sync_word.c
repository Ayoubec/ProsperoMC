/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Ordinary bounded operations on the exact patch header. No Wine process,
 * application pointers, backend ABI or server handle/lifetime emulation. */
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include "ps5_sync_word.h"

static void init_fast(struct pw_sync_word *cell, unsigned kind, unsigned value, unsigned max)
{
    pw_sync_word_init(cell, kind, value, max);
    assert(pw_sync_word_publish(cell, value));
}

static void event_matrix(void)
{
    struct pw_sync_word cell;
    unsigned kind, initial, set, old, snapshot;
    for (kind = PW_SYNC_AUTO_EVENT; kind <= PW_SYNC_MANUAL_EVENT; ++kind)
        for (initial = 0; initial <= 1; ++initial)
        {
            init_fast(&cell, kind, initial, 1);
            assert(pw_sync_word_try_wait(&cell) == (int)initial);
            assert(pw_sync_word_load(&cell) ==
                   (kind == PW_SYNC_MANUAL_EVENT ? initial : 0));
            for (set = 0; set <= 1; ++set)
            {
                init_fast(&cell, kind, initial, 1);
                old = 99;
                assert(pw_sync_word_try_event(&cell, set, &old));
                assert(old == initial && pw_sync_word_load(&cell) == set);
                assert(pw_sync_word_freeze(&cell, &snapshot) && snapshot == set);
                old = 99;
                assert(!pw_sync_word_try_event(&cell, !set, &old) && old == 99);
                assert(!pw_sync_word_try_wait(&cell));
                snapshot = 99;
                assert(!pw_sync_word_freeze(&cell, &snapshot) && snapshot == 99);
                assert(!pw_sync_word_publish(&cell, 2));
                assert(pw_sync_word_load(&cell) & PW_SYNC_WORD_SLOW);
                assert(pw_sync_word_publish(&cell, set));
            }
            old = 99;
            assert(!pw_sync_word_try_event(&cell, 2, &old) && old == 99);
            assert(!pw_sync_word_try_event(&cell, -1, &old) && old == 99);
            assert(!pw_sync_word_try_release(&cell, 1, &old) && old == 99);
        }
}

static void semaphore_matrix(void)
{
    struct pw_sync_word cell;
    unsigned maximum, initial, release, previous, snapshot;
    for (maximum = 1; maximum <= 7; ++maximum)
        for (initial = 0; initial <= maximum; ++initial)
        {
            init_fast(&cell, PW_SYNC_SEMAPHORE, initial, maximum);
            assert(pw_sync_word_try_wait(&cell) == (initial != 0));
            assert(pw_sync_word_load(&cell) == (initial ? initial - 1 : 0));
            for (release = 0; release <= maximum + 1; ++release)
            {
                int expected = release && release <= maximum - initial;
                init_fast(&cell, PW_SYNC_SEMAPHORE, initial, maximum);
                previous = 99;
                assert(pw_sync_word_try_release(&cell, release, &previous) == expected);
                assert(previous == (expected ? initial : 99));
                assert(pw_sync_word_load(&cell) == (expected ? initial + release : initial));
                assert(pw_sync_word_freeze(&cell, &snapshot));
                assert(snapshot == (expected ? initial + release : initial));
                previous = 99;
                assert(!pw_sync_word_try_release(&cell, 1, &previous) && previous == 99);
                assert(!pw_sync_word_try_wait(&cell));
                assert(!pw_sync_word_publish(&cell, maximum + 1));
                assert(pw_sync_word_publish(&cell, initial));
            }
            previous = 99;
            assert(!pw_sync_word_try_event(&cell, 1, &previous) && previous == 99);
        }
    init_fast(&cell, PW_SYNC_SEMAPHORE, PW_SYNC_WORD_MAX_COUNT - 1, PW_SYNC_WORD_MAX_COUNT);
    assert(!pw_sync_word_try_release(&cell, UINT32_MAX, &previous));
    assert(pw_sync_word_try_release(&cell, 1, &previous));
    assert(previous == PW_SYNC_WORD_MAX_COUNT - 1);
    previous = 99;
    assert(!pw_sync_word_try_release(&cell, 1, &previous) && previous == 99);
    assert(pw_sync_word_try_wait(&cell));
    assert(pw_sync_word_load(&cell) == PW_SYNC_WORD_MAX_COUNT - 1);
}

static void freeze_rejects_loaded_state(void)
{
    struct pw_sync_word cell;
    unsigned kind, snapshot;
    for (kind = PW_SYNC_AUTO_EVENT; kind <= PW_SYNC_SEMAPHORE; ++kind)
    {
        uint64_t observed, next;
        init_fast(&cell, kind, 1, kind == PW_SYNC_SEMAPHORE ? 3 : 1);
        observed = pw_sync_word_load(&cell);
        next = kind == PW_SYNC_MANUAL_EVENT ? observed : observed - 1;
        assert(pw_sync_word_freeze(&cell, &snapshot) && snapshot == 1);
        /* A client which already loaded the old fast value, including the
         * manual event's unchanged value, cannot succeed after freeze. */
        assert(!__atomic_compare_exchange_n(&cell.word, &observed, next, 0,
                                            __ATOMIC_ACQUIRE, __ATOMIC_RELAXED));
        assert(pw_sync_word_load(&cell) == (PW_SYNC_WORD_SLOW | 1));
    }
}

static struct pw_sync_word concurrent;
struct worker { unsigned producer, completed; };

static void *count_worker(void *arg)
{
    struct worker *worker = arg;
    unsigned i, old;
    for (i = 0; i < 30000; ++i)
    {
        int success = worker->producer ? pw_sync_word_try_release(&concurrent, 1, &old)
                                       : pw_sync_word_try_wait(&concurrent);
        worker->completed += success;
        if (!(i % 128)) sched_yield();
    }
    return NULL;
}

static void concurrent_transfer(void)
{
    pthread_t threads[4];
    struct worker workers[4] = {{1,0}, {0,0}, {1,0}, {0,0}};
    unsigned i, snapshot, legacy_added = 0, legacy_taken = 0;
    unsigned produced, consumed;
    init_fast(&concurrent, PW_SYNC_SEMAPHORE, 3, 17);
    for (i = 0; i < 4; ++i) assert(!pthread_create(&threads[i], NULL, count_worker, &workers[i]));
    for (i = 0; i < 3000; ++i)
    {
        assert(pw_sync_word_freeze(&concurrent, &snapshot));
        assert(snapshot <= 17);
        /* The sole server owner adopts state, changes it, and republishes;
         * clients may concurrently attempt valid operations throughout. */
        if (!(i & 1) && snapshot < 17) { ++snapshot; ++legacy_added; }
        else if ((i & 1) && snapshot) { --snapshot; ++legacy_taken; }
        assert(pw_sync_word_publish(&concurrent, snapshot));
        if (!(i % 32)) sched_yield();
    }
    for (i = 0; i < 4; ++i) assert(!pthread_join(threads[i], NULL));
    assert(pw_sync_word_freeze(&concurrent, &snapshot));
    produced = workers[0].completed + workers[2].completed;
    consumed = workers[1].completed + workers[3].completed;
    assert(3 + produced + legacy_added == consumed + legacy_taken + snapshot);
}

static struct pw_sync_word ready, ack;
static unsigned payload;

static void await(struct pw_sync_word *cell)
{
    unsigned i;
    for (i = 0; i < 1000000; ++i)
    {
        if (pw_sync_word_try_wait(cell)) return;
        if (!(i % 64)) sched_yield();
    }
    assert(!"bounded event handoff failed to complete");
}

static void signal(struct pw_sync_word *cell)
{
    unsigned previous;
    assert(pw_sync_word_try_event(cell, 1, &previous) && !previous);
}

static void *reader(void *unused)
{
    unsigned i;
    (void)unused;
    for (i = 1; i <= 2000; ++i)
    {
        await(&ready);
        assert(payload == i);
        signal(&ack);
    }
    return NULL;
}

static void event_memory_order(void)
{
    pthread_t thread;
    unsigned i;
    init_fast(&ready, PW_SYNC_AUTO_EVENT, 0, 1);
    init_fast(&ack, PW_SYNC_AUTO_EVENT, 0, 1);
    assert(!pthread_create(&thread, NULL, reader, NULL));
    for (i = 1; i <= 2000; ++i)
    {
        payload = i;
        signal(&ready);
        await(&ack);
    }
    assert(!pthread_join(thread, NULL));
    assert(!pw_sync_word_load(&ready) && !pw_sync_word_load(&ack));
}

int main(void)
{
    event_matrix();
    semaphore_matrix();
    freeze_rejects_loaded_state();
    concurrent_transfer();
    event_memory_order();
    puts("shared sync word PASS: auto/manual event transitions, semaphore bounds and previous count, "
         "failure outputs, slow authority, stale CAS rejection, four-thread count conservation, "
         "2000 event payload handoffs");
    return 0;
}
