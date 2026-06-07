import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Allow running this file directly for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cpu.process import Process
from cpu.fcfs import FCFS
from cpu.sjf import SJF
from cpu.priority import PriorityScheduling
from cpu.rr import RoundRobin


# ─────────────────────────────────────────────
#  Color palette
# ─────────────────────────────────────────────
BG         = "#1e1e2e"
SURFACE    = "#2a2a3e"
ACCENT     = "#7c6af7"
ACCENT2    = "#56cfb2"
TEXT       = "#e0e0f0"
TEXT_DIM   = "#888899"
BORDER     = "#3a3a55"
ERROR      = "#f28b82"
SUCCESS    = "#a8d8a8"

GANTT_COLORS = [
    "#7c6af7", "#56cfb2", "#f7a05a", "#f28b82",
    "#a8d8a8", "#ffd166", "#06d6a0", "#ef476f",
    "#118ab2", "#ffc8dd", "#b5e48c", "#f4a261",
]


class CPUScreen:

    def __init__(self, parent_frame):
        """
        parent_frame: the content Frame from HomeScreen.
        All widgets are built inside it.
        """
        self.parent = parent_frame
        self.processes = []          # list of Process objects
        self.row_entries = []        # list of dicts with entry widgets per row

        self._build_ui()

    # ══════════════════════════════════════════
    #  UI BUILD
    # ══════════════════════════════════════════

    def _build_ui(self):
        self.parent.configure(bg=BG)

        # ── Top title ──────────────────────────
        title_bar = tk.Frame(self.parent, bg=SURFACE, pady=10)
        title_bar.pack(fill="x")

        tk.Label(
            title_bar,
            text="CPU Scheduling Simulator",
            font=("Consolas", 18, "bold"),
            fg=ACCENT, bg=SURFACE
        ).pack()

        tk.Label(
            title_bar,
            text="Add processes below, then choose an algorithm to run",
            font=("Consolas", 10),
            fg=TEXT_DIM, bg=SURFACE
        ).pack()

        # ── Main scrollable body ───────────────
        body = tk.Frame(self.parent, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=10)

        # ── Process input table ────────────────
        self._build_input_table(body)

        # ── Algorithm controls ─────────────────
        self._build_algo_controls(body)

        # ── Results area (scrollable) ──────────
        self._build_results_area(body)

    def _build_input_table(self, parent):
        section = tk.LabelFrame(
            parent, text=" Process Table ", bg=BG,
            fg=ACCENT, font=("Consolas", 11, "bold"),
            bd=1, relief="solid", labelanchor="nw"
        )
        section.pack(fill="x", pady=(0, 10))

        # Header row
        headers = ["PID", "Arrival Time", "Burst Time", "Priority", "Quantum", ""]
        col_widths = [6, 14, 12, 10, 10, 6]

        header_row = tk.Frame(section, bg=SURFACE)
        header_row.pack(fill="x", padx=5, pady=(5, 0))

        for h, w in zip(headers, col_widths):
            tk.Label(
                header_row, text=h, width=w,
                font=("Consolas", 10, "bold"),
                fg=ACCENT2, bg=SURFACE, anchor="center"
            ).pack(side="left", padx=2)

        # Scrollable rows container
        rows_outer = tk.Frame(section, bg=BG)
        rows_outer.pack(fill="x", padx=5, pady=5)

        canvas = tk.Canvas(rows_outer, bg=BG, height=140, highlightthickness=0)
        scrollbar = ttk.Scrollbar(rows_outer, orient="vertical", command=canvas.yview)
        self.rows_frame = tk.Frame(canvas, bg=BG)

        self.rows_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons
        btn_row = tk.Frame(section, bg=BG)
        btn_row.pack(fill="x", padx=5, pady=(0, 8))

        self._btn(btn_row, "+ Add Row", self._add_row, ACCENT).pack(side="left", padx=4)
        self._btn(btn_row, "✕ Remove Last", self._remove_last_row, ERROR).pack(side="left", padx=4)
        self._btn(btn_row, "⟳ Clear All", self._clear_rows, TEXT_DIM).pack(side="left", padx=4)

        # Start with 3 default rows
        for _ in range(3):
            self._add_row()

    def _add_row(self):
        row_num = len(self.row_entries) + 1
        row_frame = tk.Frame(self.rows_frame, bg=BG)
        row_frame.pack(fill="x", pady=2)

        entries = {}
        col_widths = [6, 14, 12, 10, 10]
        fields = ["pid", "arrival", "burst", "priority", "quantum"]
        defaults = [f"P{row_num}", "0", "0", "0", "2"]

        for field, w, default in zip(fields, col_widths, defaults):
            e = tk.Entry(
                row_frame, width=w,
                font=("Consolas", 10),
                bg=SURFACE, fg=TEXT,
                insertbackground=TEXT,
                relief="flat", bd=4,
                justify="center"
            )
            e.insert(0, default)
            e.pack(side="left", padx=2)
            entries[field] = e

        # Delete button for this row
        del_btn = tk.Button(
            row_frame, text="✕", width=3,
            font=("Consolas", 9),
            bg=SURFACE, fg=ERROR,
            activebackground=ERROR, activeforeground=BG,
            relief="flat", cursor="hand2",
            command=lambda f=row_frame, e=entries: self._delete_row(f, e)
        )
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

    def _build_algo_controls(self, parent):
        section = tk.LabelFrame(
            parent, text=" Algorithm Selection ", bg=BG,
            fg=ACCENT, font=("Consolas", 11, "bold"),
            bd=1, relief="solid", labelanchor="nw"
        )
        section.pack(fill="x", pady=(0, 10))

        ctrl = tk.Frame(section, bg=BG)
        ctrl.pack(fill="x", padx=10, pady=10)

        # Algorithm radio buttons
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

        tk.Label(
            algo_frame, text="Choose Algorithm:",
            font=("Consolas", 10, "bold"),
            fg=TEXT, bg=BG
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        for i, (label, value) in enumerate(algos):
            rb = tk.Radiobutton(
                algo_frame, text=label, variable=self.algo_var, value=value,
                font=("Consolas", 10),
                fg=TEXT, bg=BG,
                selectcolor=SURFACE,
                activebackground=BG, activeforeground=ACCENT,
                cursor="hand2"
            )
            rb.grid(row=i + 1, column=0, sticky="w", padx=20, pady=1)

        # Run button
        run_frame = tk.Frame(ctrl, bg=BG)
        run_frame.pack(side="right", padx=20)

        self._btn(
            run_frame, "▶  RUN", self._run_algorithm,
            ACCENT, width=16, font_size=13
        ).pack(pady=4)

        self._btn(
            run_frame, "⟳  Reset Results", self._clear_results,
            TEXT_DIM, width=16
        ).pack(pady=4)

    def _build_results_area(self, parent):
        self.results_frame = tk.Frame(parent, bg=BG)
        self.results_frame.pack(fill="both", expand=True)

    # ══════════════════════════════════════════
    #  RUN ALGORITHM
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

        self._show_results(results, gantt, algo)

    def _parse_processes(self):
        if not self.row_entries:
            messagebox.showwarning("No Processes", "Please add at least one process.")
            return None

        processes = []
        for i, row in enumerate(self.row_entries):
            try:
                pid     = row["pid"].get().strip() or f"P{i+1}"
                arrival = int(row["arrival"].get())
                burst   = int(row["burst"].get())
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
                messagebox.showerror("Input Error", f"Row {i+1}: All time/priority/quantum fields must be integers.")
                return None

        return processes

    # ══════════════════════════════════════════
    #  DISPLAY RESULTS
    # ══════════════════════════════════════════

    def _show_results(self, results, gantt, algo):
        self._clear_results()

        algo_names = {
            "FCFS": "First Come First Served",
            "SJF": "Shortest Job First (Non-Preemptive)",
            "SRTF": "Shortest Remaining Time First (Preemptive)",
            "PRIORITY_NP": "Priority Scheduling (Non-Preemptive)",
            "PRIORITY_P": "Priority Scheduling (Preemptive)",
            "RR": "Round Robin",
        }

        # ── Section title ──────────────────────
        tk.Label(
            self.results_frame,
            text=f"Results  —  {algo_names.get(algo, algo)}",
            font=("Consolas", 13, "bold"),
            fg=ACCENT2, bg=BG
        ).pack(pady=(10, 4))

        # ── Gantt Chart ────────────────────────
        self._draw_gantt(gantt)

        # ── Stats table ────────────────────────
        self._draw_stats_table(results)

    def _draw_gantt(self, gantt):
        gantt_section = tk.LabelFrame(
            self.results_frame, text=" Gantt Chart ", bg=BG,
            fg=ACCENT, font=("Consolas", 11, "bold"),
            bd=1, relief="solid"
        )
        gantt_section.pack(fill="x", pady=(6, 4), padx=4)

        # Canvas for the chart
        canvas_height = 80
        canvas = tk.Canvas(
            gantt_section, bg=SURFACE,
            height=canvas_height, highlightthickness=0
        )
        canvas.pack(fill="x", padx=8, pady=8)

        # We need to know total time for scaling
        if not gantt:
            return

        total_time = gantt[-1][2]
        if total_time == 0:
            return

        # Build colour map per pid
        pids = list(dict.fromkeys(seg[0] for seg in gantt if seg[0] != "IDLE"))
        color_map = {pid: GANTT_COLORS[i % len(GANTT_COLORS)] for i, pid in enumerate(pids)}
        color_map["IDLE"] = BORDER

        # Draw after canvas is rendered so we know its width
        def _render(event=None):
            canvas.delete("all")
            W = canvas.winfo_width()
            if W < 10:
                W = 800
            bar_y1, bar_y2 = 10, 50
            label_y = 58

            for seg in gantt:
                pid, start, end = seg
                x1 = (start / total_time) * W
                x2 = (end / total_time) * W
                color = color_map.get(pid, ACCENT)

                # Bar
                canvas.create_rectangle(
                    x1, bar_y1, x2, bar_y2,
                    fill=color, outline=BG, width=2
                )

                # Process label inside bar (if wide enough)
                mid_x = (x1 + x2) / 2
                bar_w = x2 - x1
                if bar_w > 20:
                    canvas.create_text(
                        mid_x, (bar_y1 + bar_y2) / 2,
                        text=str(pid),
                        font=("Consolas", 9, "bold"),
                        fill=BG if pid != "IDLE" else TEXT_DIM
                    )

                # Time label below bar (start)
                label_x = max(x1, 6)  # prevent clipping at left edge
                canvas.create_text(
                    label_x, label_y,
                    text=str(start),
                    font=("Consolas", 8),
                    fill=TEXT_DIM, anchor="n"
                )

            # Final time label
            canvas.create_text(
                W - 2, label_y,
                text=str(total_time),
                font=("Consolas", 8),
                fill=TEXT_DIM, anchor="ne"
            )

        canvas.bind("<Configure>", _render)
        canvas.after(50, _render)

    def _draw_stats_table(self, results):
        table_section = tk.LabelFrame(
            self.results_frame, text=" Process Results ", bg=BG,
            fg=ACCENT, font=("Consolas", 11, "bold"),
            bd=1, relief="solid"
        )
        table_section.pack(fill="x", pady=(4, 6), padx=4)

        columns = ("PID", "Arrival", "Burst", "Priority", "Completion", "Turnaround", "Waiting", "Response")
        col_widths = (70, 70, 70, 70, 90, 100, 80, 90)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "CPU.Treeview",
            background=SURFACE,
            foreground=TEXT,
            rowheight=26,
            fieldbackground=SURFACE,
            font=("Consolas", 10),
            borderwidth=0
        )
        style.configure(
            "CPU.Treeview.Heading",
            background=BORDER,
            foreground=ACCENT2,
            font=("Consolas", 10, "bold"),
            relief="flat"
        )
        style.map("CPU.Treeview", background=[("selected", ACCENT)])

        tree = ttk.Treeview(
            table_section,
            columns=columns,
            show="headings",
            height=min(len(results), 8),
            style="CPU.Treeview"
        )

        for col, w in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center", minwidth=w)

        for p in results:
            tree.insert("", "end", values=(
                p.pid,
                p.arrival_time,
                p.burst_time,
                p.priority,
                p.completion_time,
                p.turnaround_time,
                p.waiting_time,
                p.response_time
            ))

        tree.pack(fill="x", padx=8, pady=8)

        # ── Averages row ─────────────────────
        if results:
            n = len(results)
            avg_tat = sum(p.turnaround_time for p in results) / n
            avg_wt  = sum(p.waiting_time    for p in results) / n

            avg_bar = tk.Frame(table_section, bg=SURFACE, pady=6)
            avg_bar.pack(fill="x", padx=8, pady=(0, 8))

            for label, val in [
                ("Avg Turnaround", avg_tat),
                ("Avg Waiting",    avg_wt),
            ]:
                tk.Label(
                    avg_bar,
                    text=f"{label}: {val:.2f}",
                    font=("Consolas", 10, "bold"),
                    fg=ACCENT2, bg=SURFACE
                ).pack(side="left", padx=20)

    # ══════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════

    def _clear_results(self):
        for w in self.results_frame.winfo_children():
            w.destroy()

    def _btn(self, parent, text, command, color, width=14, font_size=10):
        return tk.Button(
            parent, text=text, command=command,
            width=width,
            font=("Consolas", font_size, "bold"),
            bg=color, fg=BG,
            activebackground=TEXT, activeforeground=BG,
            relief="flat", cursor="hand2",
            pady=6
        )