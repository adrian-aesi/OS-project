# gui/virtual_memory_screen.py — Page Replacement Algorithm GUI
# Logic from CODE 2 (virtualmemory.py), adapted to CODE 1's class-based
# StorageScreen / MemoryScreen pattern with the project's dark theme palette.

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from virtual_memory.page_replacement import compute, DESCS, REF_STRINGS

# ─── Palette (matches CODE 1 project dark theme) ─────────────────────────────
BG         = "#1e1e2e"
SURFACE    = "#2a2a3e"
ACCENT     = "#7c6af7"
ACCENT2    = "#56cfb2"
TEXT       = "#e0e0f0"
TEXT_DIM   = "#888899"
TEXT3      = "#555566"
BORDER     = "#3a3a55"
BORDER2    = "#4a4a66"
ERROR      = "#f28b82"
SUCCESS    = "#a8d8a8"

# Cell colours (adapted from CODE 2's rich palette → CODE 1 dark tones)
BLUE        = "#3a6abf"
BLUE_LIGHT  = "#a0c4f0"
BLUE_DARK   = "#0e2a55"
RED         = "#993C1D"
RED_LIGHT   = "#F5C4B3"
RED_DARK    = "#4A1B0C"
GREEN       = "#0F6E56"
ORANGE      = "#D85A30"
BAR_GRAY    = "#44445a"
BAR_GREEN   = "#1D9E75"
WHITE       = "#FFFFFF"
YELLOW      = "#C8A84B"


class VirtualMemoryScreen:
    """Page Replacement Algorithm Simulator embedded in the OS Project shell."""

    CELL = 34
    GAP  = 4

    def __init__(self, parent_frame):
        self.parent       = parent_frame
        self.algo         = "fifo"
        self.refs         = REF_STRINGS["Classic (7,0,1,2,0,3...)"]
        self.frames_count = 3
        self.steps        = []
        self.cur          = -1
        self._timer       = None
        self._playing     = False

        self._build_ui()
        self._compute_and_reset()

    # ══════════════════════════════════════════
    #  UI BUILD
    # ══════════════════════════════════════════

    def _build_ui(self):
        self.parent.configure(bg=BG)

        # ── Title bar ────────────────────────────────────────────────────────
        title_bar = tk.Frame(self.parent, bg=SURFACE, pady=10)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="Page Replacement Algorithm Simulator",
                 font=("Consolas", 18, "bold"), fg=ACCENT, bg=SURFACE).pack()
        tk.Label(title_bar,
                 text="Step through FIFO · LRU · OPT · Second Chance · LFU · MFU",
                 font=("Consolas", 10), fg=TEXT_DIM, bg=SURFACE).pack()

        # ── Content area (no inner scroll — home shell already scrolls) ───────
        outer = tk.Frame(self.parent, bg=BG, padx=18, pady=12)
        outer.pack(fill="both", expand=True)

        # ── Algorithm description banner ──────────────────────────────────────
        self.desc_var = tk.StringVar()
        desc_f = tk.Frame(outer, bg=SURFACE,
                          highlightthickness=1, highlightbackground=BORDER)
        desc_f.pack(fill="x", pady=(0, 8))
        tk.Frame(desc_f, bg=ACCENT, width=3).pack(side="left", fill="y")
        tk.Label(desc_f, textvariable=self.desc_var, bg=SURFACE, fg=TEXT_DIM,
                 font=("Consolas", 10), wraplength=760, justify="left",
                 padx=10, pady=8).pack(side="left", fill="x", expand=True)

        # ── Controls row ──────────────────────────────────────────────────────
        ctrl = tk.Frame(outer, bg=BG)
        ctrl.pack(fill="x", pady=(0, 4))
        ctrl.columnconfigure(0, weight=3)
        ctrl.columnconfigure(1, weight=1)
        ctrl.columnconfigure(2, weight=0)

        # Reference string preset
        lf0 = tk.Frame(ctrl, bg=BG)
        lf0.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        tk.Label(lf0, text="Reference string preset", bg=BG, fg=TEXT_DIM,
                 font=("Consolas", 9)).pack(anchor="w")
        self.ref_var = tk.StringVar(value="Classic (7,0,1,2,0,3...)")

        style = ttk.Style()
        style.configure("VM.TCombobox",
                         fieldbackground=SURFACE, background=SURFACE,
                         foreground=TEXT, selectbackground=ACCENT,
                         selectforeground=BG)
        style.map("VM.TCombobox",
                  fieldbackground=[("readonly", SURFACE)],
                  foreground=[("readonly", TEXT)])

        self.ref_cb = ttk.Combobox(lf0, textvariable=self.ref_var,
                                    values=list(REF_STRINGS.keys()),
                                    state="readonly", font=("Consolas", 10),
                                    style="VM.TCombobox")
        self.ref_cb.pack(fill="x")
        self.ref_cb.bind("<<ComboboxSelected>>", self._on_preset_selected)

        # Frames spinbox
        lf1 = tk.Frame(ctrl, bg=BG)
        lf1.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        tk.Label(lf1, text="Frames", bg=BG, fg=TEXT_DIM,
                 font=("Consolas", 9)).pack(anchor="w")
        self.frame_var = tk.IntVar(value=3)
        sb = tk.Spinbox(lf1, from_=1, to=9, textvariable=self.frame_var, width=5,
                        font=("Consolas", 11), bg=SURFACE, fg=TEXT,
                        insertbackground=TEXT, buttonbackground=BG,
                        relief="flat", bd=1,
                        highlightthickness=1, highlightbackground=BORDER,
                        highlightcolor=ACCENT)
        sb.pack(fill="x")
        sb.bind("<FocusOut>", lambda e: self._compute_and_reset())
        sb.bind("<Return>",   lambda e: self._compute_and_reset())
        self.frame_var.trace_add("write", lambda *_: self.parent.after(100, self._compute_and_reset))

        # Reset button
        lf2 = tk.Frame(ctrl, bg=BG)
        lf2.grid(row=0, column=2, sticky="s")
        tk.Button(lf2, text="↺  Reset", command=self._compute_and_reset,
                  bg=SURFACE, fg=TEXT, font=("Consolas", 10), relief="flat",
                  padx=12, pady=5, cursor="hand2",
                  activebackground=BORDER, activeforeground=TEXT).pack()

        # ── Custom reference string ───────────────────────────────────────────
        custom_f = tk.Frame(outer, bg=BG)
        custom_f.pack(fill="x", pady=(4, 8))
        tk.Label(custom_f, text="Custom string:", bg=BG, fg=TEXT_DIM,
                 font=("Consolas", 9)).pack(side="left", padx=(0, 6))
        self.custom_var = tk.StringVar()
        custom_entry = tk.Entry(custom_f, textvariable=self.custom_var,
                                font=("Consolas", 10), bg=SURFACE, fg=TEXT,
                                insertbackground=TEXT, relief="flat",
                                highlightthickness=1, highlightbackground=BORDER,
                                highlightcolor=ACCENT)
        custom_entry.pack(side="left", fill="x", expand=True, ipady=4)
        custom_entry.bind("<Return>", lambda e: self._use_custom())
        tk.Label(custom_f, text="(e.g. 1,2,3,4,1,2)", bg=BG, fg=TEXT3,
                 font=("Consolas", 9, "italic")).pack(side="left", padx=(6, 8))
        tk.Button(custom_f, text="Use", command=self._use_custom,
                  bg=ACCENT, fg=BG, font=("Consolas", 9, "bold"),
                  relief="flat", padx=10, pady=4, cursor="hand2",
                  activebackground=ACCENT, activeforeground=BG).pack(side="left")

        # ── Algorithm tabs ────────────────────────────────────────────────────
        tab_frame = tk.Frame(outer, bg=BG)
        tab_frame.pack(fill="x", pady=(0, 8))
        self.tab_btns = {}
        for key, lbl in [("fifo", "FIFO"), ("lru", "LRU"), ("opt", "OPT"),
                          ("second", "Second Chance"), ("lfu", "LFU"), ("mfu", "MFU")]:
            btn = tk.Button(tab_frame, text=lbl,
                            command=lambda k=key: self._set_algo(k),
                            font=("Consolas", 10), relief="flat",
                            padx=10, pady=5, cursor="hand2")
            btn.pack(side="left", padx=(0, 6))
            self.tab_btns[key] = btn
        self._style_tabs()

        # ── Legend ────────────────────────────────────────────────────────────
        leg = tk.Frame(outer, bg=BG)
        leg.pack(fill="x", pady=(0, 8))
        for color, border, lbl in [
            (BLUE,       None,   "Current reference"),
            (RED,        None,   "Page fault"),
            (GREEN,      None,   "Page hit"),
            (BLUE_LIGHT, BLUE,   "Newly loaded"),
            (RED_LIGHT,  ORANGE, "Evicted"),
        ]:
            dot = tk.Frame(leg, bg=color, width=12, height=12,
                           highlightthickness=1 if border else 0,
                           highlightbackground=border or color)
            dot.pack(side="left", padx=(0, 3))
            dot.pack_propagate(False)
            tk.Label(leg, text=lbl, bg=BG, fg=TEXT_DIM,
                     font=("Consolas", 9)).pack(side="left", padx=(0, 14))

        # ── Info box ──────────────────────────────────────────────────────────
        info_f = tk.Frame(outer, bg=SURFACE,
                          highlightthickness=1, highlightbackground=BORDER)
        info_f.pack(fill="x", pady=(0, 8))
        tk.Frame(info_f, bg=ACCENT2, width=3).pack(side="left", fill="y")
        self.info_var = tk.StringVar(value="Press Next or Play to begin.")
        tk.Label(info_f, textvariable=self.info_var, bg=SURFACE, fg=TEXT,
                 font=("Consolas", 10), wraplength=760, justify="left",
                 padx=10, pady=8, anchor="w").pack(side="left", fill="x", expand=True)

        # ── Simulation card ───────────────────────────────────────────────────
        sim_card = tk.Frame(outer, bg=SURFACE,
                             highlightthickness=1, highlightbackground=BORDER)
        sim_card.pack(fill="x", pady=(0, 8))

        # Reference string row
        tk.Label(sim_card, text="REFERENCE STRING", bg=SURFACE, fg=TEXT_DIM,
                 font=("Consolas", 8, "bold"), pady=6, padx=12).pack(anchor="w")
        ref_cf = tk.Frame(sim_card, bg=SURFACE)
        ref_cf.pack(fill="x")
        self.ref_canvas = tk.Canvas(ref_cf, bg=SURFACE, height=self.CELL + 8,
                                     highlightthickness=0)
        ref_xscroll = ttk.Scrollbar(ref_cf, orient="horizontal",
                                     command=self.ref_canvas.xview)
        self.ref_canvas.configure(xscrollcommand=ref_xscroll.set)
        self.ref_canvas.pack(fill="x", padx=10, pady=(0, 2))
        ref_xscroll.pack(fill="x", padx=10, pady=(0, 6))

        tk.Frame(sim_card, bg=BORDER, height=1).pack(fill="x")

        # Frames area
        tk.Label(sim_card, text="FRAMES AT EACH STEP", bg=SURFACE, fg=TEXT_DIM,
                 font=("Consolas", 8, "bold"), pady=6, padx=12).pack(anchor="w")
        fr_cf = tk.Frame(sim_card, bg=SURFACE)
        fr_cf.pack(fill="x")
        self.frame_canvas = tk.Canvas(fr_cf, bg=SURFACE, highlightthickness=0)
        fr_xscroll = ttk.Scrollbar(fr_cf, orient="horizontal",
                                    command=self.frame_canvas.xview)
        self.frame_canvas.configure(xscrollcommand=fr_xscroll.set)
        self.frame_canvas.pack(fill="x", padx=10, pady=(0, 2))
        fr_xscroll.pack(fill="x", padx=10, pady=(0, 6))

        # Tally section (LFU/MFU only)
        self._tally_wrapper = tk.Frame(sim_card, bg=SURFACE)
        tk.Frame(self._tally_wrapper, bg=BORDER, height=1).pack(fill="x")
        self.tally_label_var = tk.StringVar(value="REFERENCE COUNTS")
        tk.Label(self._tally_wrapper, textvariable=self.tally_label_var,
                 bg=SURFACE, fg=TEXT_DIM,
                 font=("Consolas", 8, "bold"), pady=6, padx=12).pack(anchor="w")
        self.tally_inner = tk.Frame(self._tally_wrapper, bg=SURFACE)
        self.tally_inner.pack(fill="x", padx=12, pady=(0, 8))

        tk.Frame(sim_card, bg=BORDER, height=1).pack(fill="x")

        # Stats row
        stats_row = tk.Frame(sim_card, bg=BG)
        stats_row.pack(fill="x")
        self.stat_faults = tk.StringVar(value="0")
        self.stat_hits   = tk.StringVar(value="0")
        self.stat_rate   = tk.StringVar(value="0%")
        for var, lbl in [(self.stat_faults, "Page faults"),
                         (self.stat_hits,   "Hits"),
                         (self.stat_rate,   "Fault rate")]:
            f = tk.Frame(stats_row, bg=BG)
            f.pack(side="left", expand=True)
            tk.Label(f, textvariable=var, bg=BG, fg=TEXT,
                     font=("Consolas", 16, "bold"), pady=8).pack()
            tk.Label(f, text=lbl, bg=BG, fg=TEXT_DIM,
                     font=("Consolas", 9)).pack(pady=(0, 6))

        tk.Frame(sim_card, bg=BORDER, height=1).pack(fill="x")

        # Step controls
        step_row = tk.Frame(sim_card, bg=SURFACE)
        step_row.pack(fill="x", padx=10, pady=8)

        btn_kw = dict(bg=BG, fg=TEXT, font=("Consolas", 10), relief="flat",
                      padx=10, pady=4, cursor="hand2",
                      activebackground=BORDER, activeforeground=TEXT)
        tk.Button(step_row, text="← Prev", command=self._prev, **btn_kw).pack(side="left", padx=(0, 6))

        self.play_btn = tk.Button(step_row, text="▶ Play", command=self._toggle_play,
                                   bg=ACCENT, fg=BG, font=("Consolas", 10, "bold"),
                                   relief="flat", padx=12, pady=4, cursor="hand2",
                                   activebackground=ACCENT, activeforeground=BG)
        self.play_btn.pack(side="left", padx=(0, 6))

        tk.Button(step_row, text="Next →", command=self._next, **btn_kw).pack(side="left", padx=(0, 6))

        self.step_label = tk.Label(step_row, text="Step 0 / 0", bg=SURFACE, fg=TEXT_DIM,
                                    font=("Consolas", 10))
        self.step_label.pack(side="left", padx=8)

    # ══════════════════════════════════════════
    #  TAB STYLING
    # ══════════════════════════════════════════

    def _style_tabs(self):
        for key, btn in self.tab_btns.items():
            if key == self.algo:
                btn.configure(bg=ACCENT, fg=BG,
                               activebackground=ACCENT, activeforeground=BG)
            else:
                btn.configure(bg=SURFACE, fg=TEXT_DIM,
                               activebackground=SURFACE, activeforeground=TEXT_DIM)

    # ══════════════════════════════════════════
    #  INPUT HANDLERS
    # ══════════════════════════════════════════

    def _on_preset_selected(self, event=None):
        self.custom_var.set("")
        self._compute_and_reset()

    def _use_custom(self):
        raw = self.custom_var.get().strip()
        if not raw:
            return
        try:
            parsed = [int(x.strip()) for x in raw.replace(" ", ",").split(",") if x.strip()]
            if not parsed:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid input",
                                  "Enter comma-separated integers, e.g.  1, 2, 3, 4, 1, 2")
            return
        self._stop_play()
        self.refs = parsed
        self.ref_var.set("Custom")
        if "Custom" not in self.ref_cb["values"]:
            self.ref_cb["values"] = list(REF_STRINGS.keys()) + ["Custom"]
        self.steps = compute(self.algo, self.refs, self.frames_count)
        self.cur = -1
        self.desc_var.set(DESCS[self.algo])
        self._render()

    # ══════════════════════════════════════════
    #  CORE LOGIC
    # ══════════════════════════════════════════

    def _set_algo(self, algo):
        self.algo = algo
        self._style_tabs()
        self.desc_var.set(DESCS[algo])
        self._compute_and_reset()

    def _compute_and_reset(self):
        self._stop_play()
        key = self.ref_var.get()
        if key != "Custom":
            self.refs = REF_STRINGS.get(key, REF_STRINGS["Classic (7,0,1,2,0,3...)"])
        try:
            fc = int(self.frame_var.get())
        except Exception:
            fc = 3
        self.frames_count = max(1, min(9, fc))
        self.steps = compute(self.algo, self.refs, self.frames_count)
        self.cur = -1
        self.desc_var.set(DESCS[self.algo])
        self._render()

    # ══════════════════════════════════════════
    #  RENDER
    # ══════════════════════════════════════════

    def _render(self):
        is_counting = self.algo in ("lfu", "mfu")
        if is_counting:
            self._tally_wrapper.pack(fill="x")
        else:
            self._tally_wrapper.pack_forget()

        self._draw_ref_cells()
        self._draw_frame_grid()
        if is_counting and self.cur >= 0:
            self._draw_tally()
        self._update_info()
        self._update_stats()

    def _draw_ref_cells(self):
        c = self.ref_canvas
        c.delete("all")
        CELL, GAP, pad = self.CELL, self.GAP, 4
        for i, r in enumerate(self.refs):
            x = pad + i * (CELL + GAP)
            y = pad
            if i == self.cur:
                bg = GREEN if self.steps[self.cur]["hit"] else RED
                fg = WHITE
                outline = bg
            elif self.cur >= 0 and i < self.cur:
                bg = RED if not self.steps[i]["hit"] else SURFACE
                fg = WHITE if not self.steps[i]["hit"] else TEXT_DIM
                outline = RED if not self.steps[i]["hit"] else BORDER
            else:
                bg = SURFACE
                fg = TEXT_DIM
                outline = BORDER
            c.create_rectangle(x, y, x + CELL, y + CELL, fill=bg, outline=outline, width=1)
            c.create_text(x + CELL // 2, y + CELL // 2, text=str(r),
                          fill=fg, font=("Consolas", 11, "bold"))
        total_w = pad + len(self.refs) * (CELL + GAP) + pad
        c.configure(scrollregion=(0, 0, total_w, CELL + 8), height=CELL + 8)

    def _draw_frame_grid(self):
        c = self.frame_canvas
        c.delete("all")
        CELL, GAP, HDR = self.CELL, self.GAP, 16
        n = self.frames_count
        col_w = CELL + GAP
        pad = 4
        total_h = HDR + n * (CELL + GAP) + pad

        if self.cur < 0:
            x = pad
            c.create_text(x + CELL // 2, HDR // 2, text="—",
                          fill=TEXT3, font=("Consolas", 8))
            for f in range(n):
                y = HDR + f * (CELL + GAP)
                c.create_rectangle(x, y, x + CELL, y + CELL,
                                   fill=BG, outline=BORDER, width=1)
                c.create_text(x + CELL // 2, y + CELL // 2, text="—",
                              fill=TEXT3, font=("Consolas", 10))
            c.configure(scrollregion=(0, 0, pad + CELL + pad, total_h), height=total_h)
            return

        for step in range(self.cur + 1):
            s = self.steps[step]
            x = pad + step * col_w
            c.create_text(x + CELL // 2, HDR // 2, text=str(step + 1),
                          fill=TEXT3, font=("Consolas", 8))
            for f in range(n):
                y = HDR + f * (CELL + GAP)
                val = s["mem"][f] if f < len(s["mem"]) else None
                if val is None:
                    bg, fg, outline, lbl = BG, TEXT3, BORDER, ""
                elif step == self.cur and not s["hit"] and val == s["page"]:
                    bg, fg, outline, lbl = BLUE_LIGHT, BLUE_DARK, BLUE, str(val)
                elif (step == self.cur and val == s.get("victim")
                      and s["victim"] is not None):
                    bg, fg, outline, lbl = RED_LIGHT, RED_DARK, ORANGE, str(val)
                else:
                    bg, fg, outline, lbl = BG, TEXT, BORDER, str(val)
                c.create_rectangle(x, y, x + CELL, y + CELL,
                                   fill=bg, outline=outline, width=1)
                c.create_text(x + CELL // 2, y + CELL // 2, text=lbl,
                              fill=fg, font=("Consolas", 11, "bold"))

        total_w = pad + (self.cur + 1) * col_w + pad
        c.configure(scrollregion=(0, 0, total_w, total_h), height=total_h)

    def _draw_tally(self):
        for w in self.tally_inner.winfo_children():
            w.destroy()
        s = self.steps[self.cur]
        counts = s.get("counts") or {}
        if not counts:
            return

        max_count = max(counts.values(), default=1) or 1
        self.tally_label_var.set(
            "REFERENCE COUNTS  (lowest = victim)" if self.algo == "lfu"
            else "REFERENCE COUNTS  (highest = victim)")

        BAR_MAX_W = 300
        for pg in sorted(counts.keys()):
            cnt = counts[pg]
            in_mem    = pg in s["mem"]
            is_victim = pg == s.get("victim") and not s["hit"]
            is_cur    = pg == s["page"]

            row = tk.Frame(self.tally_inner, bg=SURFACE)
            row.pack(fill="x", pady=2)

            pg_bg  = BLUE_LIGHT if is_cur else BG
            pg_fg  = BLUE_DARK  if is_cur else TEXT
            pg_bdr = ACCENT     if is_cur else BORDER

            pg_box = tk.Frame(row, bg=pg_bg, width=28, height=28,
                              highlightthickness=1, highlightbackground=pg_bdr)
            pg_box.pack(side="left", padx=(0, 6))
            pg_box.pack_propagate(False)
            tk.Label(pg_box, text=str(pg), bg=pg_bg, fg=pg_fg,
                     font=("Consolas", 10, "bold")).place(relx=0.5, rely=0.5, anchor="center")

            bar_wrap = tk.Frame(row, bg=BG, height=20,
                                highlightthickness=1, highlightbackground=BORDER)
            bar_wrap.pack(side="left", fill="x", expand=True, padx=(0, 6))
            bar_wrap.pack_propagate(False)

            bar_color = (ORANGE    if is_victim else
                         BAR_GREEN if (is_cur and not is_victim) else
                         ACCENT    if in_mem else BAR_GRAY)
            text_col = BLUE_DARK if (in_mem and not is_victim) else "#CCCCCC"
            bar_w = max(4, int((cnt / max_count) * BAR_MAX_W))

            bar = tk.Frame(bar_wrap, bg=bar_color, height=20)
            bar.place(x=0, y=0, width=bar_w, height=20)
            tk.Label(bar, text="■" * cnt, bg=bar_color, fg=text_col,
                     font=("Consolas", 8)).place(x=4, y=2)

            tk.Label(row, text=str(cnt), bg=SURFACE, fg=TEXT_DIM,
                     font=("Consolas", 10), width=3, anchor="e").pack(side="left", padx=(0, 4))
            if is_victim:
                tk.Label(row, text="← evicted", bg=SURFACE, fg=ERROR,
                         font=("Consolas", 9, "bold")).pack(side="left")
            elif is_cur and not is_victim:
                tk.Label(row, text="← current", bg=SURFACE, fg=SUCCESS,
                         font=("Consolas", 9)).pack(side="left")

    def _update_info(self):
        if self.cur < 0:
            self.info_var.set("Press Next or Play to begin.")
            return
        s = self.steps[self.cur]
        if s["hit"]:
            msg = f"✓  Page {s['page']} is in memory — hit, no fault."
        elif s["victim"] is not None:
            msg = f"✗  Page fault!  Page {s['page']} not in memory.  Evicted page {s['victim']}."
        else:
            msg = f"✗  Page fault!  Page {s['page']} loaded into empty frame."
        if self.algo == "second" and s.get("bits"):
            msg += f"   Reference bits: [{', '.join(str(b) for b in s['bits'])}]"
        if self.algo in ("lfu", "mfu") and s.get("counts") and not s["hit"] and s["victim"] is not None:
            in_mem_p = [p for p in s["mem"] if p is not None]
            counts_str = ", ".join("{}({})".format(p, s["counts"].get(p, 0)) for p in in_mem_p)
            msg += f"   Counts in memory: {counts_str}."
        self.info_var.set(msg)

    def _update_stats(self):
        shown  = self.steps[:max(0, self.cur + 1)]
        faults = sum(1 for st in shown if not st["hit"])
        hits   = sum(1 for st in shown if     st["hit"])
        total  = len(shown)
        self.stat_faults.set(str(faults))
        self.stat_hits.set(str(hits))
        self.stat_rate.set(f"{round(faults / total * 100)}%" if total else "0%")
        self.step_label.configure(text=f"Step {max(0, self.cur + 1)} / {len(self.steps)}")

    # ══════════════════════════════════════════
    #  NAVIGATION
    # ══════════════════════════════════════════

    def _next(self):
        if self.cur < len(self.steps) - 1:
            self.cur += 1
            self._render()
        else:
            self._stop_play()

    def _prev(self):
        self._stop_play()
        if self.cur > -1:
            self.cur -= 1
            self._render()

    def _toggle_play(self):
        if self._playing:
            self._stop_play()
        else:
            self._start_play()

    def _start_play(self):
        self._playing = True
        self.play_btn.configure(text="⏸ Pause", bg=ERROR, fg=BG)
        self._tick()

    def _stop_play(self):
        self._playing = False
        if self._timer:
            self.parent.after_cancel(self._timer)
            self._timer = None
        self.play_btn.configure(text="▶ Play", bg=ACCENT, fg=BG)

    def _tick(self):
        if not self._playing:
            return
        if self.cur < len(self.steps) - 1:
            self.cur += 1
            self._render()
            self._timer = self.parent.after(750, self._tick)
        else:
            self._stop_play()
