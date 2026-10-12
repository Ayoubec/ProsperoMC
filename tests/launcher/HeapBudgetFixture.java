package org.prosperomc;

public final class HeapBudgetFixture {
    public static void main(String[] args) {
        HeapDiagnostics.probe();
        long reported=Runtime.getRuntime().maxMemory();
        if(reported>=4096L*1024*1024||reported<3500L*1024*1024)
            throw new AssertionError("Unexpected ParallelGC reported capacity: "+reported);
        System.out.println("HEAP_BUDGET_RESERVE_PASS");
    }
}
