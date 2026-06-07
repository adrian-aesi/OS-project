import copy
from collections import deque


class RoundRobin:

    def calculate(self, processes, quantum=None):
        """
        Round Robin scheduling.
        Uses per-process quantum if provided in process.quantum,
        or falls back to the global `quantum` argument.
        Returns (results, gantt_chart).
        """
        procs = copy.deepcopy(processes)
        n = len(procs)

        # Determine quantum to use
        q = quantum
        if q is None or q <= 0:
            # Try to get from first process (all should share same quantum in RR)
            q = procs[0].quantum if procs and procs[0].quantum > 0 else 1

        # Sort initially by arrival time
        procs_sorted = sorted(procs, key=lambda p: (p.arrival_time, p.pid))

        remaining_bt = {p.pid: p.burst_time for p in procs_sorted}
        proc_map = {p.pid: p for p in procs_sorted}

        started = {p.pid: False for p in procs_sorted}
        response_time = {}

        gantt = []
        current_time = 0
        done = []
        completed = 0

        queue = deque()
        arrived = set()

        # Add all processes with arrival_time == 0
        for p in procs_sorted:
            if p.arrival_time <= current_time:
                queue.append(p.pid)
                arrived.add(p.pid)

        while completed < n:
            if not queue:
                # CPU idle — jump to next arrival
                not_done = [p for p in procs_sorted if remaining_bt[p.pid] > 0 and p.pid not in arrived]
                if not not_done:
                    break
                next_arrival = min(p.arrival_time for p in not_done)
                gantt.append(("IDLE", current_time, next_arrival))
                current_time = next_arrival
                # Enqueue newly arrived
                for p in procs_sorted:
                    if p.arrival_time <= current_time and p.pid not in arrived and remaining_bt[p.pid] > 0:
                        queue.append(p.pid)
                        arrived.add(p.pid)
                continue

            pid = queue.popleft()
            p = proc_map[pid]

            if not started[pid]:
                response_time[pid] = current_time - p.arrival_time
                started[pid] = True

            exec_time = min(q, remaining_bt[pid])
            start = current_time
            end = current_time + exec_time

            gantt.append((pid, start, end))
            remaining_bt[pid] -= exec_time
            current_time = end

            # Enqueue any new arrivals that came in during this slice
            for proc in procs_sorted:
                if proc.pid not in arrived and proc.arrival_time <= current_time and remaining_bt[proc.pid] > 0:
                    queue.append(proc.pid)
                    arrived.add(proc.pid)

            if remaining_bt[pid] == 0:
                p.completion_time = current_time
                p.turnaround_time = p.completion_time - p.arrival_time
                p.waiting_time = p.turnaround_time - p.burst_time
                p.response_time = response_time[pid]
                done.append(p)
                completed += 1
            else:
                # Re-queue this process
                queue.append(pid)

        return done, gantt