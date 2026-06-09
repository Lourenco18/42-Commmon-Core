import heapq, sys

def push(h, dl, cid):
    h = list(h)
    heapq.heappush(h, (dl, -cid))
    return h

def pop(h):
    h = list(h)
    dl, nc = heapq.heappop(h)
    return (dl, -nc), h

def run(label, entries, expected):
    print(f"\n{label}")
    h = []
    for dl, cid in entries:
        h = push(h, dl, cid)
    ok = True
    for i, exp in enumerate(expected):
        (dl, cid), h = pop(h)
        if cid == exp:
            s = "[PASS]"
        else:
            s = f"[FAIL] expected coder{exp}"
            ok = False
        print(f"    pos {i+1} -> coder{cid} (deadline={dl}) {s}")
    print("  =>", "[PASS]" if ok else "[FAIL]")
    return ok

print("\n=== EDF Tie-breaker Tests ===")
r  = run("Test 1: same deadline ids=1,2,3 -> pop: 3 2 1",
         [(1000,1),(1000,2),(1000,3)], [3,2,1])
r &= run("Test 2: same deadline ids=5,3,1 -> pop: 5 3 1",
         [(500,5),(500,3),(500,1)], [5,3,1])
r &= run("Test 3: mixed+tie dl=800,500,1000,500 -> pop: 5 2 3 1",
         [(800,3),(500,2),(1000,1),(500,5)], [5,2,3,1])
r &= run("Test 4: no tie dl=300,200,100 -> pop: 3 2 1",
         [(300,1),(200,2),(100,3)], [3,2,1])
print("\n===", "ALL TESTS PASSED" if r else "SOME TESTS FAILED", "===\n")
sys.exit(0 if r else 1)