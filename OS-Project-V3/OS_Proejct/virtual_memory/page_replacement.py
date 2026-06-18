# virtual_memory/page_replacement.py  — Page Replacement Algorithm logic
# Ported from CODE 2 (virtualmemory.py) into the CODE 1 project structure.

DESCS = {
    "fifo":   "FIFO — the page that was loaded first is replaced first. Simple but can worsen with more frames (Belady's anomaly).",
    "lru":    "LRU — replaces the page unused for the longest time. Better than FIFO in practice; no Belady's anomaly.",
    "opt":    "OPT (optimal/MIN) — replaces the page not needed for the longest future time. Theoretical best; used as a benchmark.",
    "second": "Second chance (clock) — FIFO with a reference bit. A page with bit=1 gets a second chance; its bit is cleared and it moves to the back of the queue.",
    "lfu":    "LFU (Least Frequently Used) — keeps a running count of references per page. The page with the lowest count is replaced. FIFO breaks ties.",
    "mfu":    "MFU (Most Frequently Used) — replaces the page with the highest count, arguing the least-used page was just brought in and still needs to be used.",
}

REF_STRINGS = {
    "Classic (7,0,1,2,0,3...)":       [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1],
    "Belady demo (1,2,3,4,1,2,5...)": [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5],
    "Thrashing demo":                  [0, 1, 2, 3, 0, 1, 4, 0, 1, 2, 3, 4],
}


# ── Algorithms ────────────────────────────────────────────────────────────────

def compute_fifo(refs, n):
    mem, queue, steps = [], [], []
    for p in refs:
        hit = p in mem
        victim = None
        new_mem = list(mem)
        if not hit:
            if len(mem) < n:
                new_mem.append(p)
                queue.append(p)
            else:
                victim = queue.pop(0)
                new_mem[new_mem.index(victim)] = p
                queue.append(p)
        mem = list(new_mem)
        steps.append({"page": p, "hit": hit, "victim": victim, "mem": list(mem), "counts": None})
    return steps


def compute_lru(refs, n):
    mem, recent, steps = [], [], []
    for p in refs:
        hit = p in mem
        victim = None
        new_mem = list(mem)
        if hit:
            recent = [x for x in recent if x != p]
            recent.append(p)
        else:
            if len(mem) < n:
                new_mem.append(p)
                recent.append(p)
            else:
                victim = recent.pop(0)
                new_mem[new_mem.index(victim)] = p
                recent.append(p)
        mem = list(new_mem)
        steps.append({"page": p, "hit": hit, "victim": victim, "mem": list(mem), "counts": None})
    return steps


def compute_opt(refs, n):
    mem, steps = [], []
    for i, p in enumerate(refs):
        hit = p in mem
        victim = None
        new_mem = list(mem)
        if not hit:
            if len(mem) < n:
                new_mem.append(p)
            else:
                farthest, vi = -1, -1
                future = refs[i + 1:]
                for j, pg in enumerate(mem):
                    try:
                        nxt = future.index(pg)
                    except ValueError:
                        vi = j
                        break
                    if nxt > farthest:
                        farthest = nxt
                        vi = j
                victim = new_mem[vi]
                new_mem[vi] = p
        mem = list(new_mem)
        steps.append({"page": p, "hit": hit, "victim": victim, "mem": list(mem), "counts": None})
    return steps


def compute_second(refs, n):
    mem, bits, ptr, steps = [], [], 0, []
    for p in refs:
        hit = p in mem
        victim = None
        new_mem = list(mem)
        new_bits = list(bits)
        if hit:
            new_bits[mem.index(p)] = 1
        else:
            if len(mem) < n:
                new_mem.append(p)
                new_bits.append(1)
            else:
                while new_bits[ptr] == 1:
                    new_bits[ptr] = 0
                    ptr = (ptr + 1) % n
                victim = new_mem[ptr]
                new_mem[ptr] = p
                new_bits[ptr] = 1
                ptr = (ptr + 1) % n
        mem = list(new_mem)
        bits = list(new_bits)
        steps.append({"page": p, "hit": hit, "victim": victim, "mem": list(mem),
                       "counts": None, "bits": list(bits)})
    return steps


def compute_counting(refs, n, mode):
    mem, counts, arrival, steps = [], {}, [], []
    for i, p in enumerate(refs):
        counts[p] = counts.get(p, 0) + 1
        hit = p in mem
        victim = None
        new_mem = list(mem)
        if not hit:
            if len(mem) < n:
                new_mem.append(p)
                arrival.append(p)
            else:
                def sort_key(pg, _counts=counts, _arrival=arrival, _mode=mode):
                    cnt = _counts.get(pg, 0)
                    arr = _arrival.index(pg) if pg in _arrival else 999
                    return (cnt if _mode == "lfu" else -cnt, arr)
                victim = sorted(mem, key=sort_key)[0]
                new_mem[new_mem.index(victim)] = p
                arrival = [x for x in arrival if x != victim]
                arrival.append(p)
        mem = list(new_mem)
        counts_snap = {pg: counts.get(pg, 0) for pg in sorted(set(refs[:i + 1]))}
        steps.append({"page": p, "hit": hit, "victim": victim, "mem": list(mem),
                       "counts": dict(counts_snap), "victim_page": victim})
    return steps


def compute(algo, refs, frames):
    if algo == "fifo":   return compute_fifo(refs, frames)
    if algo == "lru":    return compute_lru(refs, frames)
    if algo == "opt":    return compute_opt(refs, frames)
    if algo == "second": return compute_second(refs, frames)
    if algo == "lfu":    return compute_counting(refs, frames, "lfu")
    return compute_counting(refs, frames, "mfu")
