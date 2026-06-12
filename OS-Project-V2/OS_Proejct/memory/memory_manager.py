"""
MVT Memory Simulator — Simulator logic only.
Ported from memManagement.py (code 1).
GUI is handled separately in gui/memory_screen.py.
"""

# ── Constants ─────────────────────────────────────────────────────────────────

TOTAL   = 256
OS_SIZE = 40

DEFAULT_JOBS = [
    {"id": 1, "mem": 60,  "burst": 10},
    {"id": 2, "mem": 100, "burst": 5},
    {"id": 3, "mem": 30,  "burst": 20},
    {"id": 4, "mem": 70,  "burst": 8},
    {"id": 5, "mem": 50,  "burst": 15},
]

PROC_COLORS = [
    "#4A90D9", "#5BAD7A", "#E07A3A", "#9B6DB5", "#D4535A",
    "#3AAFB9", "#C97B3A", "#6B9B37", "#B55A8C", "#4A7DB5",
    "#8B5E3C", "#5A8F7B", "#C4704A", "#7B6DB5", "#B5A33A",
]


# ── Simulator ─────────────────────────────────────────────────────────────────

class MemorySimulator:
    """
    MVT (Multiprogramming with Variable Tasks) memory simulator.
    Supports FCFS, SJF, and Round Robin scheduling with optional compaction.
    """

    def __init__(self):
        self.compaction_on = False
        self.base_jobs     = [dict(j) for j in DEFAULT_JOBS]
        self.reset()

    # ── Job management ────────────────────────────────────────────────────────

    def add_job(self, mem, burst):
        """Add a new job. Returns (ok, msg). Only valid before simulation starts."""
        if self.time > 0:
            return False, "Reset the simulation before adding jobs."
        if mem < 1 or mem > TOTAL - OS_SIZE:
            return False, f"Memory must be 1-{TOTAL - OS_SIZE}K."
        if burst < 1:
            return False, "Burst time must be at least 1."
        new_id = max((j["id"] for j in self.base_jobs), default=0) + 1
        self.base_jobs.append({"id": new_id, "mem": mem, "burst": burst})
        self.reset()
        return True, f"Job {new_id} added (mem={mem}K, burst={burst})."

    def remove_job(self, job_id):
        """Remove a job by id. Returns (ok, msg). Only valid before simulation starts."""
        if self.time > 0:
            return False, "Reset the simulation before removing jobs."
        before = len(self.base_jobs)
        self.base_jobs = [j for j in self.base_jobs if j["id"] != job_id]
        if len(self.base_jobs) == before:
            return False, f"No job with id {job_id}."
        self.reset()
        return True, f"Job {job_id} removed."

    # ── State ─────────────────────────────────────────────────────────────────

    def reset(self):
        self.time     = 0
        self.procs    = [
            {**j, "remaining": j["burst"], "status": "waiting",
             "ci": i % len(PROC_COLORS), "addr": -1}
            for i, j in enumerate(self.base_jobs)
        ]
        self.input_q  = list(self.procs)
        self.holes    = [{"start": OS_SIZE, "size": TOTAL - OS_SIZE}]
        self.gantt    = {p["id"]: [] for p in self.procs}
        self.events   = []
        self.rr_q     = []
        self.rr_left  = 0
        self.cur_proc = None
        self.finished = False

    # ── Internal helpers ──────────────────────────────────────────────────────

    def log(self, msg, color="gray"):
        self.events.insert(0, (msg, color))
        if len(self.events) > 40:
            self.events.pop()

    def merge_holes(self):
        self.holes.sort(key=lambda h: h["start"])
        merged = []
        for h in self.holes:
            if merged and merged[-1]["start"] + merged[-1]["size"] == h["start"]:
                merged[-1]["size"] += h["size"]
            else:
                merged.append(dict(h))
        self.holes = merged

    def allocate(self, proc):
        for i, hole in enumerate(self.holes):
            if hole["size"] >= proc["mem"]:
                proc["addr"]   = hole["start"]
                proc["status"] = "ready"
                hole["start"] += proc["mem"]
                hole["size"]  -= proc["mem"]
                if hole["size"] == 0:
                    self.holes.pop(i)
                self.merge_holes()
                return True
        return False

    def free_mem(self, proc):
        self.holes.append({"start": proc["addr"], "size": proc["mem"]})
        proc["addr"] = -1
        self.merge_holes()

    def compact(self):
        in_mem = sorted([p for p in self.procs if p["addr"] >= 0],
                        key=lambda p: p["addr"])
        cur   = OS_SIZE
        moved = False
        for p in in_mem:
            if p["addr"] != cur:
                moved = True
                p["addr"] = cur
            cur += p["mem"]
        total_free = TOTAL - cur
        self.holes = [{"start": cur, "size": total_free}] if total_free > 0 else []
        return moved

    def try_load(self, algo):
        for proc in list(self.input_q):
            if proc["status"] == "waiting":
                if self.allocate(proc):
                    self.input_q = [p for p in self.input_q if p["id"] != proc["id"]]
                    self.log(
                        f"t={self.time}: Job {proc['id']} loaded -> addr {proc['addr']}, size {proc['mem']}K",
                        "green"
                    )
                    if algo == "sjf":
                        self.rr_q.append(proc)
                        self.rr_q.sort(key=lambda p: p["remaining"])
                    else:
                        self.rr_q.append(proc)

    def do_tick(self, proc, algo):
        proc["remaining"] -= 1
        self.rr_left      -= 1
        self.gantt[proc["id"]].append("run")
        compact_msg = None

        if proc["remaining"] <= 0:
            proc["status"] = "done"
            self.log(f"t={self.time}: Job {proc['id']} done - freed {proc['mem']}K", "red")
            self.free_mem(proc)
            if self.compaction_on:
                moved = self.compact()
                if moved:
                    freed = sum(h["size"] for h in self.holes)
                    self.log(f"t={self.time}: Compaction -> {freed}K contiguous free", "amber")
                    compact_msg = (
                        f"t={self.time}: Compaction - holes merged into {freed}K contiguous block."
                    )
            self.try_load(algo)
            if self.cur_proc is proc:
                self.cur_proc = None
                self.rr_left  = 0
        else:
            proc["status"] = "running"

        return compact_msg

    # ── Main step ─────────────────────────────────────────────────────────────

    def step(self, algo, quantum=5):
        """Advance simulation by one tick. Returns compact_msg or None."""
        if self.finished:
            return None

        self.time += 1
        self.try_load(algo)
        compact_msg = None

        if algo == "rr":
            if self.cur_proc and self.rr_left > 0:
                compact_msg = self.do_tick(self.cur_proc, algo)
            else:
                if self.cur_proc and self.cur_proc["status"] != "done":
                    self.cur_proc["status"] = "ready"
                    self.rr_q.append(self.cur_proc)
                self.cur_proc = self.rr_q.pop(0) if self.rr_q else None
                self.rr_left  = quantum
                if self.cur_proc:
                    self.cur_proc["status"] = "running"
                    compact_msg = self.do_tick(self.cur_proc, algo)

        elif algo == "fcfs":
            if self.cur_proc and self.cur_proc["status"] == "running":
                compact_msg = self.do_tick(self.cur_proc, algo)
            else:
                self.cur_proc = self.rr_q.pop(0) if self.rr_q else None
                if self.cur_proc:
                    self.cur_proc["status"] = "running"
                    compact_msg = self.do_tick(self.cur_proc, algo)

        else:  # sjf
            if self.cur_proc and self.cur_proc["status"] == "running":
                compact_msg = self.do_tick(self.cur_proc, algo)
            else:
                self.rr_q.sort(key=lambda p: p["remaining"])
                self.cur_proc = self.rr_q.pop(0) if self.rr_q else None
                if self.cur_proc:
                    self.cur_proc["status"] = "running"
                    compact_msg = self.do_tick(self.cur_proc, algo)

        for p in self.procs:
            if p["status"] not in ("running", "done"):
                if p["addr"] >= 0:
                    p["status"] = "ready"
                self.gantt[p["id"]].append("idle")

        if all(p["status"] == "done" for p in self.procs):
            self.finished = True
            self.log(f"t={self.time}: All jobs complete!", "blue")

        return compact_msg

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_fragmentation(self):
        if len(self.holes) <= 1:
            return 0
        total   = sum(h["size"] for h in self.holes)
        largest = max((h["size"] for h in self.holes), default=0)
        if total == 0:
            return 0
        return round(((total - largest) / total) * 100)

    def free_k(self):
        return sum(h["size"] for h in self.holes)
