class Process:
 
    def __init__(self, pid, arrival_time, burst_time, priority=0, quantum=0):
        self.pid = pid
        self.arrival_time = int(arrival_time)
        self.burst_time = int(burst_time)
        self.priority = int(priority)
        self.quantum = int(quantum)
 
        # Computed fields (filled after scheduling)
        self.completion_time = 0
        self.turnaround_time = 0
        self.waiting_time = 0
        self.response_time = 0