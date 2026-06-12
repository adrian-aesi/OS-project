# gui/storage_screen.py — Disk Scheduling GUI (CODE 2 design adapted to CODE 1 dark theme)

import math
import sys
import os
import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.disk import build_steps

# ─── Palette (CODE 1 dark theme) ───────────────────────────────────────────────
BG        = "#1e1e2e"
SURFACE   = "#2a2a3e"
ACCENT    = "#7c6af7"
ACCENT2   = "#56cfb2"
TEXT      = "#e0e0f0"
TEXT_DIM  = "#888899"
BORDER    = "#3a3a55"
ERROR     = "#f28b82"
SUCCESS   = "#a8d8a8"

# Info badge colours (mirrors CODE 2's INFO_BG / INFO_TEXT but dark-themed)
INFO_BG   = "#1e2a4a"
INFO_TEXT = "#7eb8f7"
INFO_BDR  = "#3a5a8a"


class StorageScreen:

    def __init__(self, parent_frame):
        self.parent   = parent_frame
        self.steps    = []
        self.step_idx = 0
        self.total_mv = 0
        self.chart_ys     = []
        self.chart_labels = []
        self._user_zoomed = False
        self._disk        = 200

        self._build_ui()

    # ══════════════════════════════════════════
    #  UI BUILD
    # ══════════════════════════════════════════

    def _build_ui(self):
        self.parent.configure(bg=BG)

        # ── Title bar ─────────────────────────────────────────────────────────
        title_bar = tk.Frame(self.parent, bg=SURFACE, pady=10)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="Disk Scheduling Simulator",
                 font=("Consolas", 18, "bold"), fg=ACCENT, bg=SURFACE).pack()
        tk.Label(title_bar, text="FCFS · SSTF · SCAN · C-SCAN · LOOK · C-LOOK",
                 font=("Consolas", 10), fg=TEXT_DIM, bg=SURFACE).pack()

        # ── Main scrollable content ────────────────────────────────────────────
        outer = tk.Frame(self.parent, bg=BG, padx=16, pady=12)
        outer.pack(fill="both", expand=True)

        # ── Input controls row ────────────────────────────────────────────────
        top = tk.Frame(outer, bg=BG)
        top.pack(fill="x", pady=(0, 10))

        # Head position
        f1 = tk.Frame(top, bg=BG)
        f1.pack(side="left", padx=(0, 12))
        tk.Label(f1, text="Initial head position", bg=BG, fg=TEXT_DIM,
                 font=("Consolas", 9)).pack(anchor="w")
        self.var_head = tk.StringVar(value="53")
        self._styled_entry(f1, self.var_head, width=8).pack(ipady=4, padx=1)

        # Queue
        f2 = tk.Frame(top, bg=BG)
        f2.pack(side="left", padx=(0, 12))
        tk.Label(f2, text="Queue (comma-separated)", bg=BG, fg=TEXT_DIM,
                 font=("Consolas", 9)).pack(anchor="w")
        self.var_queue = tk.StringVar(value="98,183,37,122,14,124,65,67")
        self._styled_entry(f2, self.var_queue, width=28).pack(ipady=4, padx=1)

        # Direction (only shown for SCAN / LOOK)
        self.dir_frame = tk.Frame(top, bg=BG)
        tk.Label(self.dir_frame, text="Initial direction", bg=BG, fg=TEXT_DIM,
                 font=("Consolas", 9)).pack(anchor="w")
        self.var_dir = tk.StringVar(value="up")
        style = ttk.Style()
        style.configure("Dark.TCombobox",
                         fieldbackground=SURFACE, background=SURFACE,
                         foreground=TEXT, selectbackground=ACCENT,
                         selectforeground=BG)
        dir_combo = ttk.Combobox(self.dir_frame, textvariable=self.var_dir,
                                 state="readonly", width=10,
                                 font=("Consolas", 10))
        dir_combo["values"] = ["up", "down"]
        dir_combo.set("up")
        dir_combo.pack(ipady=2)

        # Disk size
        f4 = tk.Frame(top, bg=BG)
        f4.pack(side="left", padx=(0, 0))
        tk.Label(f4, text="Disk size (tracks)", bg=BG, fg=TEXT_DIM,
                 font=("Consolas", 9)).pack(anchor="w")
        self.var_disk = tk.StringVar(value="200")
        self._styled_entry(f4, self.var_disk, width=7).pack(ipady=4, padx=1)

        # ── Algorithm selector buttons ─────────────────────────────────────────
        algo_row = tk.Frame(outer, bg=BG)
        algo_row.pack(fill="x", pady=(0, 10))

        self._algo_btns = {}
        for name in ["fcfs", "sstf", "scan", "cscan", "look", "clook"]:
            b = tk.Button(algo_row, text=name.upper(),
                          font=("Consolas", 9, "bold"),
                          relief="flat", cursor="hand2",
                          padx=12, pady=5,
                          command=lambda n=name: self._select_algo(n))
            b.pack(side="left", padx=(0, 6))
            self._algo_btns[name] = b
        self._select_algo("fcfs", init=True)

        # ── Action buttons ─────────────────────────────────────────────────────
        act_row = tk.Frame(outer, bg=BG)
        act_row.pack(fill="x", pady=(0, 12))

        self.btn_start = tk.Button(act_row, text="▶  Start",
                                   font=("Consolas", 10),
                                   relief="flat", cursor="hand2",
                                   padx=14, pady=6,
                                   bg=ACCENT, fg=BG,
                                   activebackground=ACCENT, activeforeground=BG,
                                   command=self.start_sim)
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_step = tk.Button(act_row, text="→  Next step",
                                  font=("Consolas", 10),
                                  relief="flat", cursor="hand2",
                                  padx=14, pady=6,
                                  bg=SURFACE, fg=TEXT,
                                  activebackground=SURFACE, activeforeground=TEXT,
                                  state="disabled",
                                  command=self.do_step)
        self.btn_step.pack(side="left", padx=(0, 8))

        self.btn_reset = tk.Button(act_row, text="↺  Reset",
                                   font=("Consolas", 10),
                                   relief="flat", cursor="hand2",
                                   padx=14, pady=6,
                                   bg=SURFACE, fg=TEXT,
                                   activebackground=SURFACE, activeforeground=TEXT,
                                   command=self.reset_sim)
        self.btn_reset.pack(side="left")

        # ── Stats cards ────────────────────────────────────────────────────────
        stats_row = tk.Frame(outer, bg=BG)
        stats_row.pack(fill="x", pady=(0, 10))
        for col in range(4):
            stats_row.columnconfigure(col, weight=1, uniform="stat")

        self.stat_vars = {
            "head":  tk.StringVar(value="—"),
            "step":  tk.StringVar(value="—"),
            "move":  tk.StringVar(value="—"),
            "total": tk.StringVar(value="0"),
        }
        labels = ["Current track", "Step", "Movement this step", "Total head movement"]
        keys   = ["head", "step", "move", "total"]
        for col, (lbl, key) in enumerate(zip(labels, keys)):
            card = tk.Frame(stats_row, bg=SURFACE,
                            highlightthickness=1, highlightbackground=BORDER)
            card.grid(row=0, column=col, padx=(0, 8) if col < 3 else 0, sticky="nsew")
            tk.Label(card, text=lbl, bg=SURFACE, fg=TEXT_DIM,
                     font=("Consolas", 9)).pack(anchor="w", padx=10, pady=(8, 0))
            tk.Label(card, textvariable=self.stat_vars[key], bg=SURFACE, fg=TEXT,
                     font=("Consolas", 16, "bold")).pack(anchor="w", padx=10, pady=(0, 8))

        # ── Step info label ────────────────────────────────────────────────────
        self.step_info_var = tk.StringVar(value="Configure settings and press Start.")
        tk.Label(outer, textvariable=self.step_info_var, bg=BG, fg=TEXT_DIM,
                 font=("Consolas", 10), anchor="w").pack(fill="x", pady=(0, 8))

        # ── Chart ──────────────────────────────────────────────────────────────
        chart_frame = tk.Frame(outer, bg=BG, height=310)
        chart_frame.pack(fill="x", pady=(0, 8))
        chart_frame.pack_propagate(False)

        self.fig = Figure(figsize=(8, 2.8), dpi=96, facecolor=BG)
        self.ax  = self.fig.add_subplot(111, facecolor=SURFACE)
        self._style_axes()

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().configure(bg=BG, highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Toolbar
        toolbar_frame = tk.Frame(chart_frame, bg=SURFACE)
        toolbar_frame.pack(fill="x", side="bottom")
        self._toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        self._toolbar.config(bg=SURFACE)
        for child in self._toolbar.winfo_children():
            try:
                child.config(bg=SURFACE, fg=TEXT)
            except Exception:
                pass
        self._toolbar.pack(side="left")

        tk.Button(toolbar_frame, text="⤢ Auto-fit",
                  font=("Consolas", 8),
                  bg=SURFACE, fg=TEXT_DIM,
                  relief="flat", cursor="hand2",
                  padx=6, pady=2,
                  command=self._autofit_chart).pack(side="right", padx=4, pady=2)

        self.canvas.mpl_connect("button_release_event", self._on_chart_interact)
        self.canvas.mpl_connect("scroll_event",         self._on_chart_interact)

        # ── Step table ─────────────────────────────────────────────────────────
        table_frame = tk.Frame(outer, bg=BG)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("Step", "From", "To", "Distance", "Cumulative")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=8)
        for c in cols:
            self.tree.heading(c, text=c, anchor="w")
            self.tree.column(c, width=100, anchor="w", stretch=True)

        tst = ttk.Style()
        tst.theme_use("default")
        tst.configure("StorageDark.Treeview",
                       background=SURFACE, fieldbackground=SURFACE,
                       foreground=TEXT, rowheight=26,
                       font=("Consolas", 10), borderwidth=0)
        tst.configure("StorageDark.Treeview.Heading",
                       background=BG, foreground=TEXT_DIM,
                       font=("Consolas", 9), relief="flat", borderwidth=0)
        tst.map("StorageDark.Treeview",
                background=[("selected", INFO_BG)],
                foreground=[("selected", INFO_TEXT)])

        self.tree.configure(style="StorageDark.Treeview")

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _styled_entry(self, parent, textvariable, width):
        return tk.Entry(parent, textvariable=textvariable, width=width,
                        relief="flat",
                        bg=SURFACE, fg=TEXT,
                        insertbackground=TEXT,
                        font=("Consolas", 10),
                        highlightthickness=1,
                        highlightbackground=BORDER,
                        highlightcolor=ACCENT)

    def _on_chart_interact(self, event):
        mode = self._toolbar.mode
        if mode in ("zoom rect", "pan/zoom"):
            self._user_zoomed = True

    def _autofit_chart(self):
        self._user_zoomed = False
        if self.chart_ys:
            xs = list(range(len(self.chart_ys)))
            self.ax.set_xlim(-0.5, max(len(xs) - 0.5, 1))
            self.ax.set_ylim(0, self._disk - 1)
            self.canvas.draw_idle()

    def _style_axes(self):
        ax = self.ax
        ax.set_xlabel("Step",         color=TEXT_DIM, fontsize=10)
        ax.set_ylabel("Track number", color=TEXT_DIM, fontsize=10)
        ax.tick_params(colors=TEXT_DIM, labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        ax.set_facecolor(SURFACE)
        self.fig.patch.set_facecolor(BG)
        self.fig.subplots_adjust(left=0.07, right=0.99, top=0.95, bottom=0.18)

    def _select_algo(self, name, init=False):
        for n, b in self._algo_btns.items():
            if n == name:
                b.configure(bg=ACCENT, fg=BG,
                            activebackground=ACCENT, activeforeground=BG)
            else:
                b.configure(bg=SURFACE, fg=TEXT_DIM,
                            activebackground=SURFACE, activeforeground=TEXT_DIM)
        self._algo = name
        needs_dir = name in ("scan", "look")
        if not init:
            if needs_dir:
                self.dir_frame.pack(side="left", padx=(0, 12))
            else:
                self.dir_frame.pack_forget()
            self.reset_sim()

    def _parse_inputs(self):
        try:
            head = int(self.var_head.get())
        except ValueError:
            head = 53
        raw   = self.var_queue.get().split(",")
        queue = [int(s.strip()) for s in raw if s.strip().lstrip("-").isdigit()]
        try:
            disk = int(self.var_disk.get())
        except ValueError:
            disk = 200
        direction = self.var_dir.get()
        return head, queue, direction, disk

    # ══════════════════════════════════════════
    #  SIMULATION CONTROL
    # ══════════════════════════════════════════

    def start_sim(self):
        head, queue, direction, disk = self._parse_inputs()
        if not queue:
            return
        self.steps    = build_steps(head, queue, direction, disk, self._algo)
        self.step_idx = 0
        self.total_mv = 0

        self.stat_vars["head"].set(str(head))
        self.stat_vars["step"].set(f"0 / {len(self.steps)}")
        self.stat_vars["move"].set("—")
        self.stat_vars["total"].set("0")
        self.step_info_var.set('Press "Next step" to advance.')

        self.btn_step.configure(state="normal")
        self.btn_start.configure(state="disabled")

        for row in self.tree.get_children():
            self.tree.delete(row)

        self._init_chart(head, disk)

    def do_step(self):
        if self.step_idx >= len(self.steps):
            return
        s    = self.steps[self.step_idx]
        dist = abs(s["to"] - s["from"])
        self.total_mv += dist
        self.step_idx += 1

        self.stat_vars["head"].set(str(s["to"]))
        self.stat_vars["step"].set(f"{self.step_idx} / {len(self.steps)}")
        jump_note = " (jump — not counted for C-SCAN/C-LOOK return)" if s.get("jump") else ""
        self.stat_vars["move"].set(f"{dist}{jump_note} tracks")
        self.stat_vars["total"].set(f"{self.total_mv} tracks")
        self.step_info_var.set(s["note"])

        # Table rows: de-highlight previous, highlight current
        for row in self.tree.get_children():
            self.tree.item(row, tags=("done",))
        self.tree.tag_configure("done",    foreground=TEXT_DIM, background=SURFACE)
        self.tree.tag_configure("current", foreground=INFO_TEXT, background=INFO_BG)

        iid = self.tree.insert("", "end",
                               values=(self.step_idx, s["from"], s["to"], dist, self.total_mv),
                               tags=("current",))
        self.tree.see(iid)

        self._update_chart(s)

        if self.step_idx >= len(self.steps):
            self.btn_step.configure(state="disabled")
            self.step_info_var.set(f"✓ Done!  Total head movement: {self.total_mv} tracks.")

    def reset_sim(self):
        self.steps        = []
        self.step_idx     = 0
        self.total_mv     = 0
        self.chart_ys     = []
        self.chart_labels = []

        self.stat_vars["head"].set("—")
        self.stat_vars["step"].set("—")
        self.stat_vars["move"].set("—")
        self.stat_vars["total"].set("0")
        self.step_info_var.set("Configure settings and press Start.")

        self.btn_step.configure(state="disabled")
        self.btn_start.configure(state="normal")

        for row in self.tree.get_children():
            self.tree.delete(row)

        self.ax.clear()
        self._style_axes()
        self._user_zoomed = False
        self.canvas.draw_idle()

    # ══════════════════════════════════════════
    #  CHART HELPERS
    # ══════════════════════════════════════════

    def _init_chart(self, head, disk):
        self.chart_ys     = [head]
        self.chart_labels = ["Start"]
        self._disk        = disk
        self._user_zoomed = False

        self.ax.clear()
        self._style_axes()
        self.ax.set_ylim(0, disk - 1)
        self.ax.set_xlim(-0.5, max(0.5, len(self.steps) + 0.5))
        self.ax.set_xticks([0])
        self.ax.set_xticklabels(["Start"], fontsize=8)
        self.ax.plot([0], [head], "o-", color=ACCENT, linewidth=1.8,
                     markersize=5, markerfacecolor=ACCENT)
        self.ax.grid(True, color=BORDER, linewidth=0.5, linestyle="-")
        self.fig.tight_layout(pad=0.6)
        self.canvas.draw()

    def _update_chart(self, step):
        if step.get("jump"):
            self.chart_ys.append(float("nan"))
            self.chart_labels.append("↩")

        self.chart_ys.append(step["to"])
        self.chart_labels.append(f"Step {self.step_idx}")

        xs = list(range(len(self.chart_ys)))

        if self._user_zoomed:
            saved_xlim = self.ax.get_xlim()
            saved_ylim = self.ax.get_ylim()
        else:
            saved_xlim = None
            saved_ylim = None

        self.ax.clear()
        self._style_axes()

        rot = 45 if len(self.chart_labels) > 10 else 0
        self.ax.set_xticks(xs)
        self.ax.set_xticklabels(self.chart_labels,
                                fontsize=7 if len(xs) > 15 else 8,
                                rotation=rot,
                                ha="right" if rot else "center")
        self.ax.grid(True, color=BORDER, linewidth=0.5)

        seg_x, seg_y = [], []
        for x, y in zip(xs, self.chart_ys):
            if math.isnan(y):
                if len(seg_x) > 1:
                    self.ax.plot(seg_x, seg_y, "-", color=ACCENT, linewidth=1.8)
                seg_x, seg_y = [], []
            else:
                seg_x.append(x)
                seg_y.append(y)
        if seg_x:
            self.ax.plot(seg_x, seg_y, "o-", color=ACCENT, linewidth=1.8,
                         markersize=4, markerfacecolor=ACCENT)

        if saved_xlim is not None:
            new_xmax  = max(len(xs) - 0.5, 1)
            new_xlim  = (saved_xlim[0], max(saved_xlim[1], new_xmax))
            self.ax.set_xlim(new_xlim)
            self.ax.set_ylim(saved_ylim)
        else:
            self.ax.set_xlim(-0.5, max(len(xs) - 0.5, 1))
            self.ax.set_ylim(0, self._disk - 1)

        self.fig.tight_layout(pad=0.6)
        self.canvas.draw_idle()
