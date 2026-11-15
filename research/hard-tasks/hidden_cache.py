"""Hidden stress test for H3 (single-flight TTL+LRU cache). Usage: python -I hidden_cache.py <path to sfcache.py>"""
import importlib.util
import random
import sys
import threading
import time

spec = importlib.util.spec_from_file_location("sfcache", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
checks = []


def chk(name, ok):
    checks.append((name, bool(ok)))


def run_threads(n, fn, timeout=20):
    ts = [threading.Thread(target=fn, args=(i,), daemon=True) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout)
    return not any(t.is_alive() for t in ts)


try:
    spec.loader.exec_module(mod)
    C = mod.SingleFlightCache
    C(capacity=1, ttl=1)
except Exception as e:  # stub or import error
    print(f"FAIL cannot construct SingleFlightCache: {e!r}\n0/11")
    sys.exit(0)

# 1 hit
c = C(capacity=4, ttl=100)
calls = []
c.get("a", lambda k: calls.append(k) or 1)
v = c.get("a", lambda k: calls.append(k) or 2)
chk("hit returns cached value without calling the loader", v == 1 and calls == ["a"])

# 2 single flight under 50 threads
c = C(capacity=10, ttl=100)
n_calls, lock = [0], threading.Lock()
barrier, results = threading.Barrier(50), []
def slow(k):
    with lock:
        n_calls[0] += 1
    time.sleep(0.3)
    return object()
def worker(i):
    barrier.wait()
    results.append(c.get("k", slow))
done = run_threads(50, worker)
chk("single flight: loader ran exactly once for 50 concurrent callers", done and n_calls[0] == 1)
chk("single flight: all 50 callers got the same object", done and len(results) == 50 and len({id(r) for r in results}) == 1)

# 3 errors propagate to all waiters, nothing cached, next call retries
c = C(capacity=10, ttl=100)
errs, n_calls = [], [0]
barrier = threading.Barrier(20)
def boom(k):
    with lock:
        n_calls[0] += 1
    time.sleep(0.2)
    raise ValueError("load failed")
def eworker(i):
    barrier.wait()
    try:
        c.get("e", boom)
    except ValueError as e:
        errs.append(e)
done = run_threads(20, eworker)
retry = c.get("e", lambda k: "ok")
chk("errors: loader ran once, all 20 waiters got the exception", done and n_calls[0] == 1 and len(errs) == 20)
chk("errors: nothing cached, next get retries", retry == "ok")

# 4 a slow load must not block other keys
c = C(capacity=10, ttl=100)
c.get("cached", lambda k: 1)
t = threading.Thread(target=lambda: c.get("slow", lambda k: time.sleep(1.5) or 1), daemon=True)
t.start(); time.sleep(0.1)
t0 = time.perf_counter(); c.get("cached", lambda k: 2); c.get("other", lambda k: 3); dt = time.perf_counter() - t0
t.join(5)
chk(f"no global blocking: other keys served in {dt:.2f}s while a 1.5s load runs", dt < 0.5)

# 5 LRU order (a hit counts as use)
c = C(capacity=3, ttl=100)
loads = []
L = lambda k: loads.append(k) or k
for k in "abc":
    c.get(k, L)
c.get("a", L)          # a becomes most recent
c.get("d", L)          # evicts b
loads.clear()
c.get("a", L); c.get("b", L)
chk("LRU: least recently used entry evicted, recently hit entry kept", loads == ["b"] and len(c) <= 3)

# 6 capacity + stats consistency under concurrent mixed load
c = C(capacity=10, ttl=1000)
over, gets = [0], [0]
def mixed(i):
    rng = random.Random(i)
    for _ in range(300):
        c.get(rng.randrange(60), lambda k: k)
        with lock:
            gets[0] += 1
        if len(c) > 10:
            over[0] += 1
done = run_threads(16, mixed, timeout=60)
st = c.stats()
chk("capacity never exceeded under 16 threads", done and over[0] == 0)
chk("stats: hits + misses == gets, len == loads - evictions",
    done and st["hits"] + st["misses"] == gets[0] and len(c) == st["loads"] - st["evictions"])

# 7 TTL with injected clock
now = [0.0]
c = C(capacity=4, ttl=10, clock=lambda: now[0])
n = [0]
c.get("t", lambda k: n.__setitem__(0, n[0] + 1) or n[0])
now[0] = 5.0; a = c.get("t", lambda k: 99)
now[0] = 10.5; b = c.get("t", lambda k: 42)
chk("TTL: fresh entry served, expired entry reloaded", a == 1 and b == 42)

# 8 invalidate during an in-flight load must not leave a stale value behind
c = C(capacity=4, ttl=100)
gate = threading.Event()
th = threading.Thread(target=lambda: c.get("x", lambda k: gate.wait(3) and "stale"), daemon=True)
th.start(); time.sleep(0.1)
c.invalidate("x"); gate.set(); th.join(5)
v = c.get("x", lambda k: "fresh")
chk("invalidate during load: stale value not re-inserted", v == "fresh")

for n_, ok in checks:
    print(("PASS " if ok else "FAIL ") + n_)
print(f"{sum(ok for _, ok in checks)}/{len(checks)}")
