import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cpu.process import Process
from cpu.fcfs import FCFS
from cpu.sjf import SJF
from cpu.priority import PriorityScheduling
from cpu.rr import RoundRobin


# ─────────────────────────────────────────────
#  Color palette  (your existing palette)
# ─────────────────────────────────────────────
BG       = "#1e1e2e"
SURFACE  = "#2a2a3e"
ACCENT   = "#7c6af7"
ACCENT2  = "#56cfb2"
TEXT     = "#e0e0f0"
TEXT_DIM = "#888899"
BORDER   = "#3a3a55"
ERROR    = "#f28b82"
SUCCESS  = "#a8d8a8"

# Per-process Gantt colours (from classmate, extended)
PROC_COLORS = [
    "#7c6af7", "#56cfb2", "#f7a05a", "#f28b82",
    "#a8d8a8", "#ffd166", "#06d6a0", "#ef476f",
    "#118ab2", "#ffc8dd", "#b5e48c", "#f4a261",
]

# Gantt geometry
CW    = 26   # cell width  (pixels per time unit)
ROW_H = 30   # row height
CH    = 22   # cell/bar height
TOP   = 18   # top margin for time labels


def _blend(hex_col: str, alpha: float) -> str:
    """Blend hex_col toward BG by alpha (0=BG, 1=full colour)."""
    r, g, b   = int(hex_col[1:3], 16), int(hex_col[3:5], 16), int(hex_col[5:7], 16)
    br, bg_, bb = int(BG[1:3], 16),    int(BG[3:5], 16),      int(BG[5:7], 16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r * alpha + br * (1 - alpha)),
        int(g * alpha + bg_ * (1 - alpha)),
        int(b * alpha + bb * (1 - alpha)),
    )


def _gantt_to_log(gantt: list, processes: list) -> list:
    """
    Convert scheduler output [(pid, start, end), ...] into a per-tick log
    [{'pid': pid_or_None, 't': t}, ...] that the Gantt renderer expects.
    Works with your existing FCFS / SJF / Priority / RR output.
    """
    if not gantt:
        return []
    total = gantt[-1][2]
    log = []
    seg_map = {}  # t -> pid
    for pid, start, end in gantt:
        for t in range(start, end):
            seg_map[t] = None if pid == "IDLE" else pid
    for t in range(total):
        log.append({"pid": seg_map.get(t), "t": t})
    return log


class CPUScreen:

    def __init__(self, parent_frame):
        self.parent   = parent_frame
        self.processes = []
        self.row_entries = []

        # Gantt canvas refs (rebuilt each run)
        self._gantt_canvas = None
        self._gantt_hsb    = None

        self._build_ui()

    # ══════════════════════════════════════════
    #  UI BUILD
    # ══════════════════════════════════════════

    def _build_ui(self):
        self.parent.configure(bg=BG)

        title_bar = tk.Frame(self.parent, bg=SURFACE, pady=10)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="CPU Scheduling Simulator",
                 font=("Consolas", 18, "bold"), fg=ACCENT, bg=SURFACE).pack()
        tk.Label(title_bar, text="Add processes below, then choose an algorithm to run",
                 font=("Consolas", 10), fg=TEXT_DIM, bg=SURFACE).pack()

        body = tk.Frame(self.parent, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=10)

        self._build_input_table(body)
        self._build_algo_controls(body)
        self._build_results_area(body)

    # ── Process input table ────────────────────────────────────────────────
    def _build_input_table(self, parent):
        section = tk.LabelFrame(parent, text=" Process Table ", bg=BG,
                                fg=ACCENT, font=("Consolas", 11, "bold"),
                                bd=1, relief="solid", labelanchor="nw")
        section.pack(fill="x", pady=(0, 10))

        headers   = ["PID", "Arrival Time", "Burst Time", "Priority", "Quantum", ""]
        col_widths = [6, 14, 12, 10, 10, 6]

        header_row = tk.Frame(section, bg=SURFACE)
        header_row.pack(fill="x", padx=5, pady=(5, 0))
        for h, w in zip(headers, col_widths):
            tk.Label(header_row, text=h, width=w,
                     font=("Consolas", 10, "bold"),
                     fg=ACCENT2, bg=SURFACE, anchor="center").pack(side="left", padx=2)

        rows_outer = tk.Frame(section, bg=BG)
        rows_outer.pack(fill="x", padx=5, pady=5)

        canvas = tk.Canvas(rows_outer, bg=BG, height=140, highlightthickness=0)
        scrollbar = ttk.Scrollbar(rows_outer, orient="vertical", command=canvas.yview)
        self.rows_frame = tk.Frame(canvas, bg=BG)
        self.rows_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

        btn_row = tk.Frame(section, bg=BG)
        btn_row.pack(fill="x", padx=5, pady=(0, 8))
        self._btn(btn_row, "+ Add Row",      self._add_row,         ACCENT).pack(side="left", padx=4)
        self._btn(btn_row, "✕ Remove Last",  self._remove_last_row, ERROR ).pack(side="left", padx=4)
        self._btn(btn_row, "⟳ Clear All",    self._clear_rows,      TEXT_DIM).pack(side="left", padx=4)

        for _ in range(3):
            self._add_row()

    def _add_row(self):
        row_num = len(self.row_entries) + 1
        row_frame = tk.Frame(self.rows_frame, bg=BG)
        row_frame.pack(fill="x", pady=2)

        entries    = {}
        col_widths = [6, 14, 12, 10, 10]
        fields     = ["pid", "arrival", "burst", "priority", "quantum"]
        defaults   = [f"P{row_num}", "0", "0", "0", "2"]

        for field, w, default in zip(fields, col_widths, defaults):
            e = tk.Entry(row_frame, width=w, font=("Consolas", 10),
                         bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                         relief="flat", bd=4, justify="center")
            e.insert(0, default)
            e.pack(side="left", padx=2)
            entries[field] = e

        del_btn = tk.Button(row_frame, text="✕", width=3,
                            font=("Consolas", 9), bg=SURFACE, fg=ERROR,
                            activebackground=ERROR, activeforeground=BG,
                            relief="flat", cursor="hand2",
                            command=lambda f=row_frame, en=entries: self._delete_row(f, en))
        del_btn.pack(side="left", padx=2)

        entries["_frame"] = row_frame
        self.row_entries.append(entries)

    def _delete_row(self, frame, entries):
        frame.destroy()
        self.row_entries = [e for e in self.row_entries if e is not entries]

    def _remove_last_row(self):
        if self.row_entries:
            last = self.row_entries.pop()
            last["_frame"].destroy()

    def _clear_rows(self):
        for e in self.row_entries:
            e["_frame"].destroy()
        self.row_entries.clear()

    # ── Algorithm controls ─────────────────────────────────────────────────
    def _build_algo_controls(self, parent):
        section = tk.LabelFrame(parent, text=" Algorithm Selection ", bg=BG,
                                fg=ACCENT, font=("Consolas", 11, "bold"),
                                bd=1, relief="solid", labelanchor="nw")
        section.pack(fill="x", pady=(0, 10))

        ctrl = tk.Frame(section, bg=BG)
        ctrl.pack(fill="x", padx=10, pady=10)

        self.algo_var = tk.StringVar(value="FCFS")
        algos = [
            ("1.  First Come First Served (FCFS)",         "FCFS"),
            ("2.  Shortest Job First — Non-Preemptive",    "SJF"),
            ("3.  Shortest Job First — Preemptive (SRTF)", "SRTF"),
            ("4.  Priority — Non-Preemptive",              "PRIORITY_NP"),
            ("5.  Priority — Preemptive",                  "PRIORITY_P"),
            ("6.  Round Robin (RR)",                       "RR"),
        ]

        algo_frame = tk.Frame(ctrl, bg=BG)
        algo_frame.pack(side="left")

        tk.Label(algo_frame, text="Choose Algorithm:",
                 font=("Consolas", 10, "bold"), fg=TEXT, bg=BG
                 ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        for i, (label, value) in enumerate(algos):
            tk.Radiobutton(algo_frame, text=label, variable=self.algo_var, value=value,
                           font=("Consolas", 10), fg=TEXT, bg=BG,
                           selectcolor=SURFACE, activebackground=BG, activeforeground=ACCENT,
                           cursor="hand2").grid(row=i + 1, column=0, sticky="w", padx=20, pady=1)

        run_frame = tk.Frame(ctrl, bg=BG)
        run_frame.pack(side="right", padx=20)
        self._btn(run_frame, "▶  RUN",         self._run_algorithm, ACCENT,   width=16, font_size=13).pack(pady=4)
        self._btn(run_frame, "⟳  Reset Results", self._clear_results, TEXT_DIM, width=16).pack(pady=4)

    # ── Results area ───────────────────────────────────────────────────────
    def _build_results_area(self, parent):
        self.results_frame = tk.Frame(parent, bg=BG)
        self.results_frame.pack(fill="both", expand=True)

    # ══════════════════════════════════════════
    #  RUN
    # ══════════════════════════════════════════

    def _run_algorithm(self):
        processes = self._parse_processes()
        if processes is None:
            return

        algo = self.algo_var.get()
        self._clear_results()

        try:
            if algo == "FCFS":
                results, gantt = FCFS().calculate(processes)
            elif algo == "SJF":
                results, gantt = SJF().calculate(processes, preemptive=False)
            elif algo == "SRTF":
                results, gantt = SJF().calculate(processes, preemptive=True)
            elif algo == "PRIORITY_NP":
                results, gantt = PriorityScheduling().calculate(processes, preemptive=False)
            elif algo == "PRIORITY_P":
                results, gantt = PriorityScheduling().calculate(processes, preemptive=True)
            elif algo == "RR":
                results, gantt = RoundRobin().calculate(processes)
            else:
                return
        except Exception as ex:
            messagebox.showerror("Calculation Error", str(ex))
            return

        self._show_results(results, gantt, algo, processes)

    def _parse_processes(self):
        if not self.row_entries:
            messagebox.showwarning("No Processes", "Please add at least one process.")
            return None

        processes = []
        for i, row in enumerate(self.row_entries):
            try:
                pid      = row["pid"].get().strip() or f"P{i+1}"
                arrival  = int(row["arrival"].get())
                burst    = int(row["burst"].get())
                priority = int(row["priority"].get())
                quantum  = int(row["quantum"].get())

                if burst <= 0:
                    messagebox.showerror("Input Error", f"Row {i+1}: Burst time must be > 0.")
                    return None
                if arrival < 0:
                    messagebox.showerror("Input Error", f"Row {i+1}: Arrival time must be ≥ 0.")
                    return None

                processes.append(Process(pid, arrival, burst, priority, quantum))
            except ValueError:
                messagebox.showerror("Input Error",
                    f"Row {i+1}: All time/priority/quantum fields must be integers.")
                return None

        return processes

    # ══════════════════════════════════════════
    #  DISPLAY RESULTS
    # ══════════════════════════════════════════

    def _show_results(self, results, gantt, algo, original_processes):
        self._clear_results()

        algo_names = {
            "FCFS":        "First Come First Served",
            "SJF":         "Shortest Job First (Non-Preemptive)",
            "SRTF":        "Shortest Remaining Time First (Preemptive)",
            "PRIORITY_NP": "Priority Scheduling (Non-Preemptive)",
            "PRIORITY_P":  "Priority Scheduling (Preemptive)",
            "RR":          "Round Robin",
        }

        tk.Label(self.results_frame,
                 text=f"Results  —  {algo_names.get(algo, algo)}",
                 font=("Consolas", 13, "bold"), fg=ACCENT2, bg=BG
                 ).pack(pady=(10, 4))

        # ── Gantt chart (classmate's per-process row style) ────────────────
        self._draw_gantt_rows(gantt, original_processes)

        # ── Stats table ────────────────────────────────────────────────────
        self._draw_stats_table(results)

    # ══════════════════════════════════════════
    #  GANTT CHART  (classmate's row-per-process design)
    # ══════════════════════════════════════════

    def _draw_gantt_rows(self, gantt: list, processes: list):
        """
        Render a per-process row Gantt chart (adapted from classmate's
        _build_gantt_shell + _redraw_gantt), driven by your scheduler output.
        """
        # Build colour map  pid -> colour
        color_map = {}
        for i, p in enumerate(processes):
            color_map[p.pid] = PROC_COLORS[i % len(PROC_COLORS)]

        # Convert [(pid, start, end)] → per-tick log [{pid, t}, ...]
        log = _gantt_to_log(gantt, processes)
        maxT = len(log)
        if maxT == 0:
            return

        n     = len(processes)
        cv_h  = TOP + n * ROW_H + 8
        cv_w  = 48 + maxT * CW + 20   # initial; scrollable

        # Finish times per process (for "waiting" shading)
        fin = {}
        for p in processes:
            slots = [e["t"] for e in log if e["pid"] == p.pid]
            fin[p.pid] = (slots[-1] + 1) if slots else float("inf")

        # ── outer frame ────────────────────────────────────────────────────
        outer = tk.LabelFrame(self.results_frame, text=" Gantt Chart ",
                              bg=BG, fg=ACCENT, font=("Consolas", 11, "bold"),
                              bd=1, relief="solid")
        outer.pack(fill="x", pady=(6, 4), padx=4)

        holder = tk.Frame(outer, bg=BG)
        holder.pack(fill="x", padx=8, pady=(4, 8))

        hsb = tk.Scrollbar(holder, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        gc = tk.Canvas(holder, bg=SURFACE, height=cv_h,
                       highlightthickness=0,
                       xscrollcommand=hsb.set)
        gc.pack(side="top", fill="x", expand=True)
        hsb.config(command=gc.xview)

        self._gantt_canvas = gc
        self._gantt_hsb    = hsb

        def _draw():
            gc.delete("all")
            gc.configure(scrollregion=(0, 0, cv_w, cv_h))

            X0 = 48

            # Time labels across the top
            for i in range(maxT + 1):
                gc.create_text(X0 + i * CW, 2, text=str(i),
                               fill=TEXT_DIM, font=("Consolas", 7), anchor="n")

            # One row per process
            for ri, p in enumerate(processes):
                col = color_map[p.pid]
                y0  = TOP + ri * ROW_H
                yc  = y0 + CH // 2

                # Process label on the left
                gc.create_text(2, yc, text=p.pid,
                               fill=TEXT_DIM, font=("Consolas", 9, "bold"), anchor="w")

                for t in range(maxT):
                    entry   = log[t]
                    is_run  = entry["pid"] == p.pid
                    arrived = t >= p.arrival_time
                    is_done = t >= fin[p.pid]
                    x0_ = X0 + t * CW
                    x1_ = x0_ + CW

                    if is_run:
                        # Solid colour — this process is running
                        gc.create_rectangle(x0_, y0, x1_, y0 + CH,
                                            fill=col, outline=col)
                        gc.create_text(x0_ + CW // 2, yc, text=p.pid,
                                       fill="white", font=("Consolas", 7, "bold"))
                    elif arrived and not is_done:
                        # Faded colour — process is waiting/ready
                        gc.create_rectangle(x0_, y0, x1_, y0 + CH,
                                            fill=_blend(col, 0.18),
                                            outline=_blend(col, 0.40))
                    else:
                        # Dark — not arrived yet or already finished
                        gc.create_rectangle(x0_, y0, x1_, y0 + CH,
                                            fill=SURFACE, outline=BORDER)

            gc.xview_moveto(0)  # start scrolled to the left

        gc.after(50, _draw)

    # ══════════════════════════════════════════
    #  STATS TABLE  (your original design, unchanged)
    # ══════════════════════════════════════════

    def _draw_stats_table(self, results):
        table_section = tk.LabelFrame(self.results_frame, text=" Process Results ",
                                      bg=BG, fg=ACCENT, font=("Consolas", 11, "bold"),
                                      bd=1, relief="solid")
        table_section.pack(fill="x", pady=(4, 6), padx=4)

        columns   = ("PID", "Arrival", "Burst", "Priority", "Completion", "Turnaround", "Waiting", "Response")
        col_widths = (70,    70,        70,      70,         90,           100,           80,        90)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("CPU.Treeview",
                         background=SURFACE, foreground=TEXT, rowheight=26,
                         fieldbackground=SURFACE, font=("Consolas", 10), borderwidth=0)
        style.configure("CPU.Treeview.Heading",
                         background=BORDER, foreground=ACCENT2,
                         font=("Consolas", 10, "bold"), relief="flat")
        style.map("CPU.Treeview", background=[("selected", ACCENT)])

        tree = ttk.Treeview(table_section, columns=columns, show="headings",
                            height=min(len(results), 8), style="CPU.Treeview")

        for col, w in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center", minwidth=w)

        for p in results:
            tree.insert("", "end", values=(
                p.pid, p.arrival_time, p.burst_time, p.priority,
                p.completion_time, p.turnaround_time, p.waiting_time, p.response_time
            ))

        tree.pack(fill="x", padx=8, pady=8)

        if results:
            n       = len(results)
            avg_tat = sum(p.turnaround_time for p in results) / n
            avg_wt  = sum(p.waiting_time    for p in results) / n

            avg_bar = tk.Frame(table_section, bg=SURFACE, pady=6)
            avg_bar.pack(fill="x", padx=8, pady=(0, 8))
            for label, val in [("Avg Turnaround", avg_tat), ("Avg Waiting", avg_wt)]:
                tk.Label(avg_bar, text=f"{label}: {val:.2f}",
                         font=("Consolas", 10, "bold"),
                         fg=ACCENT2, bg=SURFACE).pack(side="left", padx=20)

    # ══════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════

    def _clear_results(self):
        for w in self.results_frame.winfo_children():
            w.destroy()
        self._gantt_canvas = None
        self._gantt_hsb    = None

    def _btn(self, parent, text, command, color, width=14, font_size=10):
        return tk.Button(parent, text=text, command=command, width=width,
                         font=("Consolas", font_size, "bold"),
                         bg=color, fg=BG,
                         activebackground=TEXT, activeforeground=BG,
                         relief="flat", cursor="hand2", pady=6)
