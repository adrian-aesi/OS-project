import tkinter as tk
from tkinter import ttk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.memory_manager import MemorySimulator, TOTAL, OS_SIZE, PROC_COLORS

# ─────────────────────────────────────────────
#  Color palette  (matches code 2 dark theme)
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
WARNING  = "#ffd166"

# Status badge colors (adapted from code 1 logic, dark-theme palette)
STATUS_STYLE = {
    "waiting": (SURFACE,      TEXT_DIM),
    "ready":   ("#1e3a5f",    "#7eb8f7"),
    "running": ("#1a3d1a",    SUCCESS),
    "done":    ("#2a2a2a",    "#666677"),
}

EVENT_COLORS = {
    "green": SUCCESS,
    "blue":  "#7eb8f7",
    "red":   ERROR,
    "amber": WARNING,
    "gray":  TEXT_DIM,
}

# Memory map geometry
MEM_W  = 170
MEM_H  = 320
GANTT_H = 14


class MemoryScreen:

    def __init__(self, parent_frame):
        self.parent   = parent_frame
        self.sim      = MemorySimulator()
        self.algo_var = tk.StringVar(value="rr")
        self._banner_after = None

        self._build_ui()
        self.parent.after(60, self._render)

    # ══════════════════════════════════════════
    #  UI BUILD
    # ══════════════════════════════════════════

    def _build_ui(self):
        self.parent.configure(bg=BG)

        # Title bar
        title_bar = tk.Frame(self.parent, bg=SURFACE, pady=10)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="MVT Memory Management Simulator",
                 font=("Consolas", 18, "bold"), fg=ACCENT, bg=SURFACE).pack()
        tk.Label(title_bar, text="Multiprogramming with Variable Tasks — FCFS · SJF · Round Robin",
                 font=("Consolas", 10), fg=TEXT_DIM, bg=SURFACE).pack()

        # Controls bar
        self._build_controls_bar()

        # Banner (compaction notification)
        self._build_banner()

        # Divider
        tk.Frame(self.parent, bg=BORDER, height=1).pack(fill="x")

        # Main body
        body = tk.Frame(self.parent, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=10)

        self._build_left_panel(body)
        self._build_right_panel(body)

    # ── Controls bar ──────────────────────────────────────────────────────────

    def _build_controls_bar(self):
        bar = tk.Frame(self.parent, bg=SURFACE, pady=8, padx=14)
        bar.pack(fill="x")

        # Algorithm selector
        tk.Label(bar, text="Algorithm:", font=("Consolas", 10),
                 fg=TEXT_DIM, bg=SURFACE).pack(side="left")

        algo_map = [("Round Robin", "rr"), ("FCFS", "fcfs"), ("SJF", "sjf")]
        self._algo_btns = {}
        seg = tk.Frame(bar, bg=BORDER, padx=1, pady=1)
        seg.pack(side="left", padx=(6, 0))
        for label, val in algo_map:
            b = tk.Button(
                seg, text=label, font=("Consolas", 9, "bold"),
                bd=0, padx=10, pady=5, cursor="hand2",
                command=lambda v=val: self._set_algo(v)
            )
            b.pack(side="left")
            self._algo_btns[val] = b
        self._update_algo_btns()

        # Quantum field (RR only)
        self._quantum_frame = tk.Frame(bar, bg=SURFACE)
        self._quantum_frame.pack(side="left", padx=(8, 0))
        tk.Label(self._quantum_frame, text="q =", font=("Consolas", 9),
                 fg=TEXT_DIM, bg=SURFACE).pack(side="left")
        self.quantum_var = tk.StringVar(value="5")
        tk.Entry(
            self._quantum_frame, textvariable=self.quantum_var,
            width=3, font=("Consolas", 10, "bold"),
            bg=BG, fg=ACCENT2, relief="flat", bd=4,
            insertbackground=ACCENT2, justify="center"
        ).pack(side="left", padx=(4, 0))

        # Compaction toggle
        self.compact_btn = tk.Button(
            bar, text="Compaction: OFF",
            font=("Consolas", 9, "bold"),
            bg=SURFACE, fg=TEXT_DIM,
            bd=1, relief="solid", highlightbackground=BORDER,
            cursor="hand2", padx=10, pady=4,
            command=self._toggle_compaction
        )
        self.compact_btn.pack(side="left", padx=(12, 0))

        # Time display
        self.time_lbl = tk.Label(
            bar, text="t = 0",
            font=("Consolas", 12, "bold"),
            fg=ACCENT2, bg=BG,
            padx=10, pady=4, bd=1, relief="solid",
            highlightbackground=BORDER
        )
        self.time_lbl.pack(side="left", padx=(12, 0))

        # Step button
        self.step_btn = self._btn(bar, "▶  Step +1", self._step, ACCENT, width=12)
        self.step_btn.pack(side="left", padx=(10, 0))

        # Reset button
        self._btn(bar, "↺  Reset", self._reset, TEXT_DIM, width=10).pack(side="left", padx=(6, 0))

    # ── Banner ────────────────────────────────────────────────────────────────

    def _build_banner(self):
        self.banner_frame = tk.Frame(
            self.parent, bg="#2a1f00",
            highlightbackground=WARNING, highlightthickness=1
        )
        self.banner_lbl = tk.Label(
            self.banner_frame, text="",
            bg="#2a1f00", fg=WARNING,
            font=("Consolas", 9, "bold"), padx=10, pady=5
        )
        self.banner_lbl.pack()

    # ── Left: memory map ──────────────────────────────────────────────────────

    def _build_left_panel(self, parent):
        left = tk.Frame(parent, bg=BG, width=MEM_W + 40)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        mem_section = tk.LabelFrame(
            left, text=" Memory Map (256K) ",
            bg=BG, fg=ACCENT, font=("Consolas", 11, "bold"),
            bd=1, relief="solid", labelanchor="nw"
        )
        mem_section.pack(fill="both", expand=True)

        self.mem_canvas = tk.Canvas(
            mem_section, bg=SURFACE, bd=0,
            highlightthickness=1, highlightbackground=BORDER,
            width=MEM_W, height=MEM_H
        )
        self.mem_canvas.pack(pady=(8, 4), padx=8)

        # Fragmentation bar
        frow = tk.Frame(mem_section, bg=BG)
        frow.pack(fill="x", padx=8)
        tk.Label(frow, text="Ext. frag.", bg=BG, fg=TEXT_DIM,
                 font=("Consolas", 8)).pack(side="left")
        self.frag_pct_lbl = tk.Label(frow, text="0%", bg=BG, fg=TEXT_DIM,
                                      font=("Consolas", 8, "bold"))
        self.frag_pct_lbl.pack(side="right")

        fbar_bg = tk.Frame(mem_section, bg=BORDER, height=5, width=MEM_W)
        fbar_bg.pack(anchor="w", padx=8, pady=(2, 4))
        fbar_bg.pack_propagate(False)
        self.frag_bar = tk.Frame(fbar_bg, bg=ERROR, height=5)
        self.frag_bar.place(x=0, y=0, relheight=1.0, width=0)

        self.free_lbl = tk.Label(
            mem_section, text=f"Free: {TOTAL - OS_SIZE}K (1 hole)",
            bg=BG, fg=TEXT_DIM, font=("Consolas", 8)
        )
        self.free_lbl.pack(anchor="w", padx=8, pady=(0, 6))

    # ── Right: controls + table + gantt + events ──────────────────────────────

    def _build_right_panel(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # Add / Remove process
        add_section = tk.LabelFrame(
            right, text=" Add / Remove Process ",
            bg=BG, fg=ACCENT, font=("Consolas", 11, "bold"),
            bd=1, relief="solid", labelanchor="nw"
        )
        add_section.pack(fill="x", pady=(0, 8))
        self._build_add_form(add_section)

        # Process table
        table_section = tk.LabelFrame(
            right, text=" Process Table ",
            bg=BG, fg=ACCENT, font=("Consolas", 11, "bold"),
            bd=1, relief="solid", labelanchor="nw"
        )
        table_section.pack(fill="x", pady=(0, 8))
        self._build_proc_table(table_section)

        # Gantt chart
        gantt_section = tk.LabelFrame(
            right, text=" Gantt Chart ",
            bg=BG, fg=ACCENT, font=("Consolas", 11, "bold"),
            bd=1, relief="solid", labelanchor="nw"
        )
        gantt_section.pack(fill="x", pady=(0, 8))
        gh = 24 + len(self.sim.base_jobs) * (GANTT_H + 8)
        self.gantt_canvas = tk.Canvas(
            gantt_section, bg=SURFACE, bd=0,
            highlightthickness=0, height=gh
        )
        self.gantt_canvas.pack(fill="x", expand=True, padx=6, pady=(4, 8))
        self.gantt_canvas.bind("<Configure>", lambda e: self._render_gantt())

        # Event log
        event_section = tk.LabelFrame(
            right, text=" Event Log ",
            bg=BG, fg=ACCENT, font=("Consolas", 11, "bold"),
            bd=1, relief="solid", labelanchor="nw"
        )
        event_section.pack(fill="both", expand=True)
        self._build_event_log(event_section)

    # ── Add / Remove form ─────────────────────────────────────────────────────

    def _build_add_form(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=10, pady=8)

        tk.Label(row, text="Mem (K):", font=("Consolas", 9),
                 fg=TEXT_DIM, bg=BG).pack(side="left")
        self.add_mem_var = tk.StringVar(value="40")
        tk.Entry(row, textvariable=self.add_mem_var, width=6,
                 font=("Consolas", 10), bg=SURFACE, fg=TEXT,
                 relief="flat", bd=4, insertbackground=TEXT,
                 justify="center").pack(side="left", padx=(4, 12))

        tk.Label(row, text="Burst:", font=("Consolas", 9),
                 fg=TEXT_DIM, bg=BG).pack(side="left")
        self.add_burst_var = tk.StringVar(value="10")
        tk.Entry(row, textvariable=self.add_burst_var, width=6,
                 font=("Consolas", 10), bg=SURFACE, fg=TEXT,
                 relief="flat", bd=4, insertbackground=TEXT,
                 justify="center").pack(side="left", padx=(4, 12))

        self._btn(row, "+ Add", self._add_process, SUCCESS, width=8).pack(side="left", padx=(0, 16))

        # Separator
        tk.Frame(row, bg=BORDER, width=1, height=22).pack(side="left", padx=(0, 14))

        tk.Label(row, text="Remove Job ID:", font=("Consolas", 9),
                 fg=TEXT_DIM, bg=BG).pack(side="left")
        self.remove_id_var = tk.StringVar(value="")
        tk.Entry(row, textvariable=self.remove_id_var, width=4,
                 font=("Consolas", 10), bg=SURFACE, fg=TEXT,
                 relief="flat", bd=4, insertbackground=TEXT,
                 justify="center").pack(side="left", padx=(4, 8))
        self._btn(row, "Remove", self._remove_process, ERROR, width=8).pack(side="left")

        self.add_status_lbl = tk.Label(
            parent, text="", bg=BG, fg=TEXT_DIM, font=("Consolas", 8)
        )
        self.add_status_lbl.pack(anchor="w", padx=10, pady=(0, 4))

    # ── Process table ─────────────────────────────────────────────────────────

    def _build_proc_table(self, parent):
        cols   = ("Job", "Mem", "Burst", "Remaining", "Status", "Address")
        widths = (70,    60,    60,      80,           100,      80)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Mem.Treeview",
                         background=SURFACE, foreground=TEXT, rowheight=26,
                         fieldbackground=SURFACE, font=("Consolas", 10), borderwidth=0)
        style.configure("Mem.Treeview.Heading",
                         background=BORDER, foreground=ACCENT2,
                         font=("Consolas", 10, "bold"), relief="flat")
        style.map("Mem.Treeview", background=[("selected", ACCENT)])

        self.proc_tree = ttk.Treeview(
            parent, columns=cols, show="headings",
            height=max(3, len(self.sim.base_jobs)),
            selectmode="none", style="Mem.Treeview"
        )
        for col, w in zip(cols, widths):
            self.proc_tree.heading(col, text=col)
            self.proc_tree.column(col, width=w, minwidth=w, anchor="center")

        for st, (bg, fg) in STATUS_STYLE.items():
            self.proc_tree.tag_configure(st, background=bg, foreground=fg)

        self.proc_tree.pack(fill="x", padx=6, pady=(0, 6))

    # ── Event log ─────────────────────────────────────────────────────────────

    def _build_event_log(self, parent):
        wrap = tk.Frame(parent, bg=SURFACE,
                        highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        sb = tk.Scrollbar(wrap, width=12, bg=BORDER)
        sb.pack(side="right", fill="y")

        self.event_text = tk.Text(
            wrap, bg=SURFACE, fg=TEXT_DIM, bd=0,
            font=("Consolas", 9), height=7,
            highlightthickness=0, state="disabled",
            wrap="word", yscrollcommand=sb.set
        )
        sb.config(command=self.event_text.yview)
        self.event_text.pack(fill="both", expand=True, padx=6, pady=6)

        for key, col in EVENT_COLORS.items():
            self.event_text.tag_configure(key, foreground=col)

    # ══════════════════════════════════════════
    #  ACTIONS
    # ══════════════════════════════════════════

    def _add_process(self):
        try:
            mem   = int(self.add_mem_var.get().strip())
            burst = int(self.add_burst_var.get().strip())
        except ValueError:
            self._set_status("Mem and Burst must be integers.", error=True)
            return
        ok, msg = self.sim.add_job(mem, burst)
        self._set_status(msg, error=not ok)
        if ok:
            self._rebuild_gantt_height()
            self._refresh_table_height()
            self._render()

    def _remove_process(self):
        raw = self.remove_id_var.get().strip()
        if not raw:
            self._set_status("Enter a Job ID to remove.", error=True)
            return
        try:
            job_id = int(raw)
        except ValueError:
            self._set_status("Job ID must be an integer.", error=True)
            return
        ok, msg = self.sim.remove_job(job_id)
        self._set_status(msg, error=not ok)
        if ok:
            self.remove_id_var.set("")
            self._rebuild_gantt_height()
            self._refresh_table_height()
            self._render()

    def _set_status(self, msg, error=False):
        self.add_status_lbl.config(
            text=msg,
            fg=ERROR if error else SUCCESS
        )
        self.parent.after(3500, lambda: self.add_status_lbl.config(text=""))

    def _rebuild_gantt_height(self):
        n  = len(self.sim.base_jobs)
        gh = 24 + n * (GANTT_H + 8)
        self.gantt_canvas.config(height=gh)

    def _refresh_table_height(self):
        n = len(self.sim.base_jobs)
        self.proc_tree.config(height=max(3, n))

    def _update_algo_btns(self):
        val = self.algo_var.get()
        for v, b in self._algo_btns.items():
            if v == val:
                b.config(bg=ACCENT, fg=BG)
            else:
                b.config(bg=SURFACE, fg=TEXT_DIM)
        if hasattr(self, "_quantum_frame"):
            if val == "rr":
                self._quantum_frame.pack(side="left", padx=(8, 0))
            else:
                self._quantum_frame.pack_forget()

    def _set_algo(self, val):
        self.algo_var.set(val)
        self._update_algo_btns()
        self._reset()

    def _toggle_compaction(self):
        self.sim.compaction_on = not self.sim.compaction_on
        state = "ON" if self.sim.compaction_on else "OFF"
        self.compact_btn.config(
            bg=ACCENT  if self.sim.compaction_on else SURFACE,
            fg=BG      if self.sim.compaction_on else TEXT_DIM,
            text=f"Compaction: {state}"
        )
        self._reset()

    def _reset(self):
        self.sim.reset()
        self._hide_banner()
        self.step_btn.config(state="normal", bg=ACCENT, fg=BG)
        self._rebuild_gantt_height()
        self._render()

    def _get_quantum(self):
        try:
            return max(1, int(self.quantum_var.get().strip()))
        except ValueError:
            self.quantum_var.set("5")
            return 5

    def _step(self):
        compact_msg = self.sim.step(self.algo_var.get(), quantum=self._get_quantum())
        if compact_msg:
            self._show_banner(compact_msg)
        if self.sim.finished:
            self.step_btn.config(state="disabled", bg=SURFACE, fg=TEXT_DIM)
        self._render()

    # ── Banner ────────────────────────────────────────────────────────────────

    def _show_banner(self, msg):
        self.banner_lbl.config(text=f"=> {msg}")
        self.banner_frame.pack(fill="x", padx=14, pady=(0, 4))
        if self._banner_after:
            self.parent.after_cancel(self._banner_after)
        self._banner_after = self.parent.after(3500, self._hide_banner)

    def _hide_banner(self):
        self.banner_frame.pack_forget()
        self._banner_after = None

    # ══════════════════════════════════════════
    #  RENDER
    # ══════════════════════════════════════════

    def _render(self):
        self.time_lbl.config(text=f"t = {self.sim.time}")
        self._render_mem()
        self._render_proc_table()
        self._render_gantt()
        self._render_events()

    def _render_mem(self):
        c = self.mem_canvas
        c.delete("all")
        W, H = MEM_W, MEM_H

        # Build segment list: OS block + in-memory processes + free holes
        segs = [{"size": OS_SIZE, "label": f"OS\n{OS_SIZE}K",
                  "bg": "#5F5E5A", "fg": "#F1EFE8"}]

        in_mem = sorted([p for p in self.sim.procs if p["addr"] >= 0],
                        key=lambda p: p["addr"])
        cur = OS_SIZE
        for p in in_mem:
            if p["addr"] > cur:
                gap = p["addr"] - cur
                segs.append({"size": gap, "label": f"free\n{gap}K",
                              "bg": SURFACE, "fg": TEXT_DIM})
            segs.append({"size": p["mem"],
                         "label": f"J{p['id']}\n{p['mem']}K",
                         "bg": PROC_COLORS[p["ci"]], "fg": "#ffffff"})
            cur = p["addr"] + p["mem"]
        if cur < TOTAL:
            gap = TOTAL - cur
            segs.append({"size": gap, "label": f"free\n{gap}K",
                          "bg": SURFACE, "fg": TEXT_DIM})

        # Draw from bottom (address 0 = bottom, TOTAL = top)
        y = H
        for seg in segs:
            h = max(int(seg["size"] / TOTAL * H), 2)
            y -= h
            c.create_rectangle(0, y, W, y + h,
                                fill=seg["bg"], outline=BORDER, width=1)
            lines  = seg["label"].split("\n")
            mid_y  = y + h // 2
            offset = 6 if len(lines) > 1 and h >= 28 else 0
            if h >= 16:
                c.create_text(W // 2, mid_y - offset,
                              text=lines[0], fill=seg["fg"],
                              font=("Consolas", 8, "bold"))
                if offset:
                    c.create_text(W // 2, mid_y + offset + 2,
                                  text=lines[1], fill=seg["fg"],
                                  font=("Consolas", 7))

        # Fragmentation indicator
        frag  = self.sim.get_fragmentation()
        bar_w = int(MEM_W * frag / 100)
        self.frag_pct_lbl.config(text=f"{frag}%")
        self.frag_bar.place(x=0, y=0, relheight=1.0, width=bar_w)

        fk = self.sim.free_k()
        hn = len(self.sim.holes)
        self.free_lbl.config(
            text=f"Free: {fk}K ({hn} hole{'s' if hn != 1 else ''})"
        )

    def _render_proc_table(self):
        for row in self.proc_tree.get_children():
            self.proc_tree.delete(row)
        for p in self.sim.procs:
            addr = f"{p['addr']}K" if p["addr"] >= 0 else "-"
            self.proc_tree.insert(
                "", "end",
                values=(f"J{p['id']}", f"{p['mem']}K",
                        p["burst"], p["remaining"], p["status"], addr),
                tags=(p["status"],)
            )

    def _render_gantt(self):
        c = self.gantt_canvas
        c.delete("all")
        W = c.winfo_width()
        if W <= 1:
            return

        maxT    = max(self.sim.time, 1)
        lbl_w   = 46
        track_w = W - lbl_w - 10
        y0      = 16

        # Time axis labels
        step = max(1, maxT // 10)
        for t in range(0, maxT + 1, step):
            x = lbl_w + int(t / maxT * track_w)
            c.create_text(x, y0 - 5, text=str(t), fill=TEXT_DIM,
                          font=("Consolas", 7), anchor="s")

        # Per-process rows
        for idx, p in enumerate(self.sim.procs):
            y = y0 + idx * (GANTT_H + 8)
            c.create_text(lbl_w - 4, y + GANTT_H // 2,
                          text=f"J{p['id']}", fill=TEXT_DIM,
                          font=("Consolas", 8, "bold"), anchor="e")
            # Background track
            c.create_rectangle(lbl_w, y, lbl_w + track_w, y + GANTT_H,
                                fill=SURFACE, outline=BORDER)
            ticks = self.sim.gantt[p["id"]]
            if ticks:
                cell_w = track_w / maxT
                for ti, tick in enumerate(ticks):
                    x0 = lbl_w + int(ti * cell_w)
                    x1 = lbl_w + int((ti + 1) * cell_w)
                    if tick == "run":
                        c.create_rectangle(x0, y, x1, y + GANTT_H,
                                           fill=PROC_COLORS[p["ci"]], outline="")

    def _render_events(self):
        self.event_text.config(state="normal")
        self.event_text.delete("1.0", "end")
        for msg, color in self.sim.events:
            self.event_text.insert("end", msg + "\n", color)
        self.event_text.config(state="disabled")

    # ── Helper ────────────────────────────────────────────────────────────────

    def _btn(self, parent, text, command, color, width=12, font_size=10):
        return tk.Button(
            parent, text=text, command=command, width=width,
            font=("Consolas", font_size, "bold"),
            bg=color, fg=BG,
            activebackground=TEXT, activeforeground=BG,
            relief="flat", cursor="hand2", pady=5
        )
