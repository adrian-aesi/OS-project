import copy


class SJF:

    def calculate(self, processes, preemptive=False):
        """
        Shortest Job First scheduling.
        preemptive=False → classic SJF (non-preemptive)
        preemptive=True  → Shortest Remaining Time First (SRTF)
        Returns (results, gantt_chart).
        """
        if preemptive:
            return self._srtf(processes)
        else:
            return self._sjf(processes)

    # ------------------------------------------------------------------
    # Non-Preemptive SJF
    # ------------------------------------------------------------------
    def _sjf(self, processes):
        procs = copy.deepcopy(processes)
        remaining = list(procs)
        gantt = []
        current_time = 0
        done = []

        while remaining:
            # Processes that have arrived by current_time
            available = [p for p in remaining if p.arrival_time <= current_time]

            if not available:
                # CPU idle — jump to next arrival
                next_arrival = min(p.arrival_time for p in remaining)
                gantt.append(("IDLE", current_time, next_arrival))
                current_time = next_arrival
                continue

            # Pick the one with the shortest burst time (tie-break: arrival, then pid)
            chosen = min(available, key=lambda p: (p.burst_time, p.arrival_time, p.pid))
            remaining.remove(chosen)

            start = current_time
            end = current_time + chosen.burst_time

            gantt.append((chosen.pid, start, end))

            chosen.completion_time = end
            chosen.turnaround_time = chosen.completion_time - chosen.arrival_time
            chosen.waiting_time = chosen.turnaround_time - chosen.burst_time
            chosen.response_time = start - chosen.arrival_time

            current_time = end
            done.append(chosen)

        return done, gantt

    # ------------------------------------------------------------------
    # Preemptive SJF (SRTF)
    # ------------------------------------------------------------------
    def _srtf(self, processes):
        procs = copy.deepcopy(processes)
        n = len(procs)

        remaining_bt = {p.pid: p.burst_time for p in procs}
        started = {p.pid: False for p in procs}
        response_time = {}

        gantt = []
        current_time = 0
        done = []
        completed = 0

        while completed < n:
            available = [p for p in procs if p.arrival_time <= current_time and remaining_bt[p.pid] > 0]

            if not available:
                # CPU idle
                next_arrival = min(p.arrival_time for p in procs if remaining_bt[p.pid] > 0)
                if not gantt or gantt[-1][0] != "IDLE":
                    gantt.append(("IDLE", current_time, next_arrival))
                else:
                    gantt[-1] = ("IDLE", gantt[-1][1], next_arrival)
                current_time = next_arrival
                continue

            # Shortest remaining time (tie-break: arrival, then pid)
            chosen = min(available, key=lambda p: (remaining_bt[p.pid], p.arrival_time, p.pid))

            # Record response time on first run
            if not started[chosen.pid]:
                response_time[chosen.pid] = current_time - chosen.arrival_time
                started[chosen.pid] = True

            # Append to gantt (merge consecutive same-pid slices)
            if gantt and gantt[-1][0] == chosen.pid:
                gantt[-1] = (chosen.pid, gantt[-1][1], current_time + 1)
            else:
                gantt.append((chosen.pid, current_time, current_time + 1))

            remaining_bt[chosen.pid] -= 1
            current_time += 1

            if remaining_bt[chosen.pid] == 0:
                chosen.completion_time = current_time
                chosen.turnaround_time = chosen.completion_time - chosen.arrival_time
                chosen.waiting_time = chosen.turnaround_time - chosen.burst_time
                chosen.response_time = response_time[chosen.pid]
                done.append(chosen)
                completed += 1

        return done, gantt