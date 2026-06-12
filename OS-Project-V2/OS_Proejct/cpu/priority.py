import copy


class PriorityScheduling:

    def calculate(self, processes, preemptive=False):
        """
        Priority Scheduling.
        Lower priority number = higher priority (like most OS textbooks).
        preemptive=False → non-preemptive
        preemptive=True  → preemptive (running process can be interrupted)
        Returns (results, gantt_chart).
        """
        if preemptive:
            return self._preemptive(processes)
        else:
            return self._non_preemptive(processes)

    # ------------------------------------------------------------------
    # Non-Preemptive Priority
    # ------------------------------------------------------------------
    def _non_preemptive(self, processes):
        procs = copy.deepcopy(processes)
        remaining = list(procs)
        gantt = []
        current_time = 0
        done = []

        while remaining:
            available = [p for p in remaining if p.arrival_time <= current_time]

            if not available:
                next_arrival = min(p.arrival_time for p in remaining)
                gantt.append(("IDLE", current_time, next_arrival))
                current_time = next_arrival
                continue

            # Highest priority = lowest number; tie-break by arrival then pid
            chosen = min(available, key=lambda p: (p.priority, p.arrival_time, p.pid))
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
    # Preemptive Priority
    # ------------------------------------------------------------------
    def _preemptive(self, processes):
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
                next_arrival = min(p.arrival_time for p in procs if remaining_bt[p.pid] > 0)
                if not gantt or gantt[-1][0] != "IDLE":
                    gantt.append(("IDLE", current_time, next_arrival))
                else:
                    gantt[-1] = ("IDLE", gantt[-1][1], next_arrival)
                current_time = next_arrival
                continue

            # Highest priority = lowest number; tie-break arrival then pid
            chosen = min(available, key=lambda p: (p.priority, p.arrival_time, p.pid))

            if not started[chosen.pid]:
                response_time[chosen.pid] = current_time - chosen.arrival_time
                started[chosen.pid] = True

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