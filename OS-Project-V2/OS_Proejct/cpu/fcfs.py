class FCFS:

    def calculate(self, processes):
        """
        First-Come, First-Served scheduling.
        Sorts by arrival time and runs each process to completion.
        Returns (results, gantt_chart).
        """
        # Sort by arrival time (FCFS order)
        procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))

        gantt = []       # list of (pid, start, end)
        current_time = 0

        for p in procs:
            # CPU idles if the next process hasn't arrived yet
            if current_time < p.arrival_time:
                gantt.append(("IDLE", current_time, p.arrival_time))
                current_time = p.arrival_time

            start = current_time
            end = current_time + p.burst_time

            gantt.append((p.pid, start, end))

            p.completion_time = end
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            p.response_time = start - p.arrival_time

            current_time = end

        return procs, gantt