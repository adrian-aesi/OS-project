# gui/deadlock_screen.py — Deadlock Simulator GUI (CODE 1 logic adapted to CODE 2 dark theme)
#
# Drop-in screen class — mirrors the structure of CPUScreen / MemoryScreen /
# StorageScreen / VirtualMemoryScreen. Contains two tabs (ttk.Notebook):
#   - Banker's Algorithm  (safety check, resource request, deadlock detection)
#   - RAG / Wait-For Graph (interactive graph builder + cycle detection)
#
# All widget logic/structure is preserved exactly from deadlock.py; only the
# color palette and outer wrapping have been adapted to match the rest of
# the OS Simulator project.

import sys
import os
import math
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deadlock.deadlock_manager import (
    R, N, DA, DM, DAV, DDA, DDR, DDAV,
    clone_matrix, vec_str, safety, detect, detect_cycle
)

# ─── Palette (matches cpu_screen.py / memory_screen.py / storage_screen.py) ───
BG       = "#1e1e2e"
SURFACE  = "#2a2a3e"
ACCENT   = "#7c6af7"
ACCENT2  = "#56cfb2"
TEXT     = "#e0e0f0"
TEXT_DIM = "#888899"
BORDER   = "#3a3a55"
ERROR    = "#f28b82"
SUCCESS  = "#a8d8a8"

COL_SUCCESS_BG  = "#16331f"
COL_SUCCESS_TXT = SUCCESS
COL_DANGER_BG   = "#3a1d1d"
COL_DANGER_TXT  = ERROR
COL_INFO_TXT    = "#7eb8f7"

PROC_COLOR   = ACCENT
RES_COLOR    = "#e88b3a"
WFG_COLOR    = "#b06ef7"
REQ_COLOR    = "#e74c4c"
ASSIGN_COLOR = "#27c47a"
CYCLE_COLOR  = "#e74c4c"


# ════════════════════════════════════════════════════════════
#  Scrollable Frame helper
# ════════════════════════════════════════════════════════════

class ScrollableFrame(ttk.Frame):
    """A frame with a vertical scrollbar that scrolls its inner content."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._win, width=event.width)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>",   self._on_mousewheel)
        self.canvas.bind_all("<Button-5>",   self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ════════════════════════════════════════════════════════════
#  Banker's Algorithm Tab
# ════════════════════════════════════════════════════════════

class BankersTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.alloc  = clone_matrix(DA)
        self.max_   = clone_matrix(DM)
        self.avail  = DAV[:]
        self.result = None

        self.det_alloc = clone_matrix(DDA)
        self.det_req   = clone_matrix(DDR)
        self.det_avail = DDAV[:]

        # Outer scrollable container fills the tab
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        p = self.scroll.inner  # all children go here

        self._build_system_state(p)
        self._build_controls(p)
        self._build_request_section(p)
        self._build_safety_result(p)
        self._build_detection_section(p)

        self.refresh_main_table()

    # ------------------------------------------------------------------
    def _section_label(self, parent, text):
        ttk.Label(parent, text=text.upper(), foreground=TEXT_DIM,
                  font=("Consolas", 9, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

    # ---------- System state table ----------
    def _build_system_state(self, p):
        self._section_label(p, "System State")

        outer = ttk.Frame(p)
        outer.pack(fill="x", padx=12, pady=(0, 6))

        W_PROC   = 6
        W_CELL   = 4
        W_WORK   = 3

        # Single shared grid for header, available row, and all process rows
        # so every column lines up exactly regardless of widget type
        # (Spinbox vs Label render at different widths for the same `width=`).
        grid = ttk.Frame(outer)
        grid.pack(anchor="w")

        ttk.Label(grid, text="", width=W_PROC).grid(row=0, column=0)

        groups = [
            ("Allocation", 1),
            ("Max", 5),
            ("Need", 9),
            ("Available", 13),
        ]

        for title, col in groups:
            fg = COL_INFO_TXT if title == "Need" else TEXT
            ttk.Label(
                grid,
                text=title,
                foreground=fg,
                font=("Consolas", 9, "bold")
            ).grid(row=0, column=col, columnspan=3)

        ttk.Label(grid, text="Process", width=W_PROC).grid(row=1, column=0, rowspan=2, sticky="n")

        for block, base in enumerate([1,5,9,13]):
            for j, r in enumerate(R):
                fg = COL_INFO_TXT if block == 2 else TEXT
                ttk.Label(
                    grid,
                    text=r,
                    width=W_CELL,
                    foreground=fg,
                    anchor="center"
                ).grid(row=1, column=base+j)

        # ---- Available row (row 2) ----
        self.avail_vars = []
        for j in range(3):
            v = tk.StringVar(value=str(self.avail[j]))
            self.avail_vars.append(v)
            e = ttk.Spinbox(grid, textvariable=v, width=W_WORK, justify="center",
                            from_=0, to=20, increment=1, wrap=True)
            e.grid(row=2, column=13 + j, padx=1, pady=(2, 6))
            e.bind("<KeyRelease>", lambda ev: self._sync_avail())
            v.trace_add("write", lambda *args: self._sync_avail())

        # ---- Process rows (rows 3..3+N-1) ----
        self.alloc_vars  = [[tk.StringVar(value=str(self.alloc[i][j])) for j in range(3)] for i in range(N)]
        self.max_vars    = [[tk.StringVar(value=str(self.max_[i][j]))  for j in range(3)] for i in range(N)]
        self.need_labels = []
        self.work_labels = []

        base_row = 3
        for i in range(N):
            r_idx = base_row + i

            ttk.Label(grid, text="P" + str(i), width=W_PROC).grid(row=r_idx, column=0, pady=1)

            for j in range(3):
                var = self.alloc_vars[i][j]
                e = ttk.Spinbox(grid, textvariable=var, width=W_CELL, justify="center",
                                from_=0, to=20, increment=1, wrap=True)
                e.grid(row=r_idx, column=1 + j, padx=1, pady=1)
                e.bind("<KeyRelease>", lambda ev, ii=i: self._sync_alloc(ii))
                var.trace_add("write", lambda *args, ii=i: self._sync_alloc(ii))

            for j in range(3):
                var = self.max_vars[i][j]
                e = ttk.Spinbox(grid, textvariable=var, width=W_CELL, justify="center",
                                from_=0, to=20, increment=1, wrap=True)
                e.grid(row=r_idx, column=5 + j, padx=1, pady=1)
                e.bind("<KeyRelease>", lambda ev, ii=i: self._sync_max(ii))
                var.trace_add("write", lambda *args, ii=i: self._sync_max(ii))

            need_row = []
            for j in range(3):
                lbl = ttk.Label(grid, text="0", width=W_CELL, anchor="center",
                                foreground=COL_INFO_TXT, font=("Consolas", 9, "bold"))
                lbl.grid(row=r_idx, column=9 + j, padx=1, pady=1)
                need_row.append(lbl)
            self.need_labels.append(need_row)

            work_row = []
            for j in range(3):
                lbl = ttk.Label(grid, text="", width=W_WORK, anchor="center",
                                foreground=TEXT_DIM)
                lbl.grid(row=r_idx, column=13 + j, padx=1, pady=1)
                work_row.append(lbl)
            self.work_labels.append(work_row)

    # ---------- Controls ----------
    def _build_controls(self, p):
        frm = ttk.Frame(p)
        frm.pack(anchor="w", padx=12, pady=(0, 6))
        ttk.Button(frm, text="Check Safety", command=self.run_check).pack(side="left", padx=(0, 8))
        ttk.Button(frm, text="Reset",        command=self.reset).pack(side="left")

    # ---------- Safety badge ----------
    def _build_safety_result(self, p):
        self.safety_badge = tk.Label(self.request_result_frame, text="", anchor="w", padx=10, pady=6,
                                     font=("Consolas", 10, "bold"), wraplength=860, justify="left")
        self.safety_badge.pack_forget()

    # ---------- Resource Request ----------
    def _build_request_section(self, p):
        ttk.Separator(p, orient="horizontal").pack(fill="x", padx=12, pady=8)
        self._section_label(p, "Resource Request")

        ctrl = ttk.Frame(p)
        ctrl.pack(anchor="w", padx=12, pady=(0, 6))

        ttk.Label(ctrl, text="Process:").pack(side="left")
        self.req_proc_var = tk.StringVar(value="P1")
        ttk.Combobox(ctrl, textvariable=self.req_proc_var, width=5,
                     values=["P"+str(i) for i in range(N)],
                     state="readonly").pack(side="left", padx=(4, 16))

        ttk.Label(ctrl, text="Request vector:").pack(side="left")
        self.req_vec_vars = []
        for j in range(3):
            ttk.Label(ctrl, text=R[j], foreground=TEXT_DIM).pack(side="left", padx=(10, 2))
            v = tk.StringVar(value=str([1,0,2][j]))
            self.req_vec_vars.append(v)
            ttk.Spinbox(ctrl, textvariable=v, width=4, justify="center",
                        from_=0, to=20, increment=1, wrap=True).pack(side="left")

        ttk.Button(ctrl, text="Request", command=self.run_request).pack(side="left", padx=(16, 0))

        self.request_result_frame = ttk.Frame(p)
        self.request_result_frame.pack(fill="x", padx=12, pady=(0, 0))
        self.req_badge = tk.Label(self.request_result_frame, text="", anchor="w", padx=10, pady=6,
                                  font=("Consolas", 10, "bold"), wraplength=860, justify="left")
        self.req_badge.pack_forget()

    # ---------- Deadlock Detection ----------
    def _build_detection_section(self, p):
        ttk.Separator(p, orient="horizontal").pack(fill="x", padx=12, pady=8)
        self._section_label(p, "Deadlock Detection")

        # Available row
        avail_frm = ttk.Frame(p)
        avail_frm.pack(anchor="w", padx=12, pady=(0, 8))
        self.det_avail_vars = []
        for j in range(3):
            ttk.Label(avail_frm, text="  " + R[j], foreground=TEXT_DIM).pack(side="left")
            v = tk.StringVar(value=str(self.det_avail[j]))
            self.det_avail_vars.append(v)
            ttk.Spinbox(avail_frm, textvariable=v, width=4, justify="center",
                        from_=0, to=20, increment=1, wrap=True).pack(side="left", padx=(2, 0))

        # Matrices side by side
        matrices_frm = ttk.Frame(p)
        matrices_frm.pack(anchor="w", padx=12, pady=(0, 8))

        alloc_col = ttk.Frame(matrices_frm)
        alloc_col.pack(side="left", padx=(0, 40), anchor="n")
        ttk.Label(alloc_col, text="ALLOCATION", foreground=TEXT_DIM,
                  font=("Consolas", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self.det_alloc_vars = self._build_matrix_grid(alloc_col, self.det_alloc)

        req_col = ttk.Frame(matrices_frm)
        req_col.pack(side="left", anchor="n")
        ttk.Label(req_col, text="REQUEST (WAITING)", foreground=TEXT_DIM,
                  font=("Consolas", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self.det_req_vars = self._build_matrix_grid(req_col, self.det_req)

        ttk.Button(p, text="Detect Deadlock", command=self.run_detect).pack(anchor="w", padx=12, pady=(0, 8))

        self.det_steps_frame = ttk.Frame(p)
        self.det_steps_frame.pack(fill="x", padx=12)

        self.det_badge = tk.Label(p, text="", anchor="w", padx=10, pady=6,
                                  font=("Consolas", 10, "bold"), wraplength=860, justify="left")
        self.det_badge.pack_forget()

    def _build_matrix_grid(self, parent, matrix):
        hdr = ttk.Frame(parent)
        hdr.pack(anchor="w")
        ttk.Label(hdr, text="", width=5).grid(row=0, column=0)
        for j, r in enumerate(R):
            ttk.Label(hdr, text=r, width=5, anchor="center").grid(row=0, column=1+j)

        grid = ttk.Frame(parent)
        grid.pack(anchor="w")
        var_rows = []
        for i in range(N):
            ttk.Label(grid, text="P"+str(i), width=5).grid(row=i, column=0)
            row_vars = []
            for j in range(3):
                v = tk.StringVar(value=str(matrix[i][j]))
                row_vars.append(v)
                ttk.Spinbox(grid, textvariable=v, width=5, justify="center",
                        from_=0, to=20, increment=1, wrap=True).grid(row=i, column=1+j, pady=1, padx=1)
            var_rows.append(row_vars)
        return var_rows

    # ---------- Sync helpers ----------
    def _to_int(self, s):
        try:
            return max(0, int(s))
        except (ValueError, TypeError):
            return 0

    def _sync_alloc(self, i):
        for j in range(3):
            self.alloc[i][j] = self._to_int(self.alloc_vars[i][j].get())
        self.refresh_main_table()

    def _sync_max(self, i):
        for j in range(3):
            self.max_[i][j] = self._to_int(self.max_vars[i][j].get())
        self.refresh_main_table()

    def _sync_avail(self):
        for j in range(3):
            self.avail[j] = self._to_int(self.avail_vars[j].get())

    # ---------- Refresh ----------
    def refresh_main_table(self):
        need = [[self.max_[i][j] - self.alloc[i][j] for j in range(3)] for i in range(N)]
        for i in range(N):
            for j in range(3):
                val = need[i][j]
                self.need_labels[i][j].config(
                    text=str(val),
                    foreground=COL_DANGER_TXT if val < 0 else COL_INFO_TXT)

            if self.result:
                step = self.result["step_map"].get(i)
                if step:
                    for j in range(3):
                        self.work_labels[i][j].config(text=str(step["before"][j]))
                else:
                    for j in range(3):
                        self.work_labels[i][j].config(text="")
            else:
                for j in range(3):
                    self.work_labels[i][j].config(text="")

    # ---------- Actions ----------
    def run_check(self):
        self.req_badge.pack_forget()
        self.result = safety(self.alloc, self.max_, self.avail)
        self.refresh_main_table()
        self._show_safety_badge(self.result)

    def _show_safety_badge(self, res):
        if res["safe"]:
            seq_str = " → ".join("P"+str(i) for i in res["seq"])
            self.safety_badge.config(
                text="✓ Safe state — sequence: " + seq_str,
                bg=COL_SUCCESS_BG, fg=COL_SUCCESS_TXT)
        else:
            self.safety_badge.config(
                text="⚠ Unsafe state — deadlock possible",
                bg=COL_DANGER_BG, fg=COL_DANGER_TXT)
            messagebox.showwarning("Unsafe state", "Unsafe state detected — deadlock is possible.")
        self.safety_badge.pack(fill="x", pady=(0, 4))

    def run_request(self):
        for i in range(N):
            self._sync_alloc(i)
            self._sync_max(i)
        self._sync_avail()

        idx = int(self.req_proc_var.get().replace("P", ""))
        req_vec = [self._to_int(v.get()) for v in self.req_vec_vars]
        need = [[self.max_[r][c] - self.alloc[r][c] for c in range(3)] for r in range(N)]

        if any(req_vec[j] > need[idx][j] for j in range(3)):
            self._set_req_badge(False, f"Request exceeds Need for P{idx} — error")
            self.result = None; self.refresh_main_table(); return

        if any(req_vec[j] > self.avail[j] for j in range(3)):
            self._set_req_badge(False, f"Resources unavailable — P{idx} must wait")
            self.result = None; self.refresh_main_table(); return

        new_avail = [self.avail[j] - req_vec[j] for j in range(3)]
        new_alloc = clone_matrix(self.alloc)
        new_alloc[idx] = [new_alloc[idx][j] + req_vec[j] for j in range(3)]

        res = safety(new_alloc, self.max_, new_avail)
        if res["safe"]:
            self.alloc = new_alloc
            self.avail = new_avail
            for j in range(3):
                self.alloc_vars[idx][j].set(str(self.alloc[idx][j]))
                self.avail_vars[j].set(str(self.avail[j]))
            seq_str = " → ".join("P"+str(x) for x in res["seq"])
            self._set_req_badge(True, f"Request granted — safe. Sequence: {seq_str}")
            self.result = res
        else:
            self._set_req_badge(False, f"Unsafe state would result — P{idx} must wait")
            self.result = res
        self.refresh_main_table()

    def _set_req_badge(self, ok, msg):
        self.req_badge.config(
            text=("✓ " if ok else "⚠ ") + msg,
            bg=COL_SUCCESS_BG if ok else COL_DANGER_BG,
            fg=COL_SUCCESS_TXT if ok else COL_DANGER_TXT)
        self.req_badge.pack(fill="x", pady=(0, 4))

    def run_detect(self):
        for i in range(N):
            for j in range(3):
                self.det_alloc[i][j] = self._to_int(self.det_alloc_vars[i][j].get())
                self.det_req[i][j]   = self._to_int(self.det_req_vars[i][j].get())
        for j in range(3):
            self.det_avail[j] = self._to_int(self.det_avail_vars[j].get())

        res = detect(self.det_alloc, self.det_req, self.det_avail)

        for w in self.det_steps_frame.winfo_children():
            w.destroy()

        if res["steps"]:
            ttk.Label(self.det_steps_frame, text="PROCESSES THAT CAN COMPLETE",
                      foreground=TEXT_DIM, font=("Consolas", 9, "bold")).pack(anchor="w", pady=(0, 4))
            for s in res["steps"]:
                row = tk.Frame(self.det_steps_frame, bg=SURFACE)
                row.pack(fill="x", pady=2)
                tk.Label(row, text="P"+str(s["proc"]), bg=SURFACE, fg=TEXT,
                         font=("Consolas", 9, "bold"), width=4).pack(side="left", padx=(8, 4), pady=4)
                tk.Label(row, text="Request ≤ Work",   bg=SURFACE, fg=TEXT_DIM,
                         font=("Consolas", 8)).pack(side="left", padx=4)
                tk.Label(row, text=vec_str(s["before"]), bg=SURFACE, fg=COL_INFO_TXT,
                         font=("Consolas", 9)).pack(side="left", padx=4)
                tk.Label(row, text="→ releases →",    bg=SURFACE, fg=TEXT_DIM,
                         font=("Consolas", 8)).pack(side="left", padx=4)
                tk.Label(row, text=vec_str(s["after"]),  bg=SURFACE, fg=COL_SUCCESS_TXT,
                         font=("Consolas", 9)).pack(side="left", padx=4)

        if not self.det_badge.winfo_ismapped():
            self.det_badge.pack(fill="x", padx=12, pady=(6, 12))
        if res["dead"]:
            dead_str = ", ".join("P"+str(i) for i in res["dead"])
            self.det_badge.config(
                text=f"⚠ Deadlock detected — stuck processes: {dead_str}",
                bg=COL_DANGER_BG, fg=COL_DANGER_TXT)
        else:
            seq_str = " → ".join("P"+str(i) for i in res["seq"])
            self.det_badge.config(
                text=f"✓ No deadlock — completion order: {seq_str}",
                bg=COL_SUCCESS_BG, fg=COL_SUCCESS_TXT)

    def reset(self):
        self.alloc  = clone_matrix(DA)
        self.max_   = clone_matrix(DM)
        self.avail  = DAV[:]
        self.result = None

        for i in range(N):
            for j in range(3):
                self.alloc_vars[i][j].set(str(self.alloc[i][j]))
                self.max_vars[i][j].set(str(self.max_[i][j]))
        for j in range(3):
            self.avail_vars[j].set(str(self.avail[j]))

        self.req_proc_var.set("P1")
        for j, val in enumerate([1, 0, 2]):
            self.req_vec_vars[j].set(str(val))

        self.det_alloc = clone_matrix(DDA)
        self.det_req   = clone_matrix(DDR)
        self.det_avail = DDAV[:]
        for i in range(N):
            for j in range(3):
                self.det_alloc_vars[i][j].set(str(self.det_alloc[i][j]))
                self.det_req_vars[i][j].set(str(self.det_req[i][j]))
        for j in range(3):
            self.det_avail_vars[j].set(str(self.det_avail[j]))

        self.safety_badge.pack_forget()
        self.req_badge.pack_forget()
        self.det_badge.pack_forget()
        self.det_badge.config(text="", bg=SURFACE, fg=TEXT_DIM)
        for w in self.det_steps_frame.winfo_children():
            w.destroy()

        self.refresh_main_table()


# ════════════════════════════════════════════════════════════
#  RAG / Wait-For Graph Tab
# ════════════════════════════════════════════════════════════

class RagWfgTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.mode = "rag"
        self.processes    = []
        self.resources    = []
        self.edges        = []
        self.wfg_edges    = []
        self.deadlock_cycle = []

        self._build_tabs_row()
        self._build_panel()
        self._build_canvas()
        self._build_status()
        self._build_legend()

        self.rebuild_config()
        self.load_preset("deadlock")

    def _build_tabs_row(self):
        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=8, pady=(8, 6))
        self.btn_rag = ttk.Button(frm, text="Resource Allocation Graph",
                                  command=lambda: self.set_mode("rag"))
        self.btn_rag.pack(side="left", padx=(0, 6))
        self.btn_wfg = ttk.Button(frm, text="Wait-For Graph",
                                  command=lambda: self.set_mode("wfg"))
        self.btn_wfg.pack(side="left")
        self._update_tab_buttons()

    def _build_panel(self):
        panel = ttk.Frame(self)
        panel.pack(fill="x", padx=8, pady=(0, 8))

        # --- Edge card ---
        edge_card = ttk.LabelFrame(panel, text="Add Edge", padding=10)
        edge_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # RAG controls
        self.rag_controls = ttk.Frame(edge_card)
        self.rag_controls.pack(fill="x")

        r1 = ttk.Frame(self.rag_controls); r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="Type", width=10).pack(side="left")
        self.edge_type_var = tk.StringVar(value="req")
        self._type_combo = ttk.Combobox(r1, textvariable=self.edge_type_var, width=22,
                                         state="readonly", values=["Request (P→R)", "Assignment (R→P)"])
        self._type_combo.current(0)
        self._type_combo.pack(side="left")
        self._type_combo.bind("<<ComboboxSelected>>", lambda e: self.update_edge_ui())

        r2 = ttk.Frame(self.rag_controls); r2.pack(fill="x", pady=2)
        self.src_lbl = ttk.Label(r2, text="Process", width=10); self.src_lbl.pack(side="left")
        self.src_var = tk.StringVar()
        self.src_combo = ttk.Combobox(r2, textvariable=self.src_var, width=8, state="readonly")
        self.src_combo.pack(side="left")

        r3 = ttk.Frame(self.rag_controls); r3.pack(fill="x", pady=2)
        self.dst_lbl = ttk.Label(r3, text="Resource", width=10); self.dst_lbl.pack(side="left")
        self.dst_var = tk.StringVar()
        self.dst_combo = ttk.Combobox(r3, textvariable=self.dst_var, width=8, state="readonly")
        self.dst_combo.pack(side="left")

        r4 = ttk.Frame(self.rag_controls); r4.pack(fill="x", pady=(6, 0))
        ttk.Button(r4, text="Add Edge",  command=self.add_edge).pack(side="left", padx=(0, 6))
        ttk.Button(r4, text="Clear All", command=self.clear_all).pack(side="left")

        # WFG controls
        self.wfg_controls = ttk.Frame(edge_card)

        w1 = ttk.Frame(self.wfg_controls); w1.pack(fill="x", pady=2)
        ttk.Label(w1, text="From P", width=10).pack(side="left")
        self.wfg_src_var = tk.StringVar()
        self.wfg_src_combo = ttk.Combobox(w1, textvariable=self.wfg_src_var, width=8, state="readonly")
        self.wfg_src_combo.pack(side="left")

        w2 = ttk.Frame(self.wfg_controls); w2.pack(fill="x", pady=2)
        ttk.Label(w2, text="Waits for P", width=10).pack(side="left")
        self.wfg_dst_var = tk.StringVar()
        self.wfg_dst_combo = ttk.Combobox(w2, textvariable=self.wfg_dst_var, width=8, state="readonly")
        self.wfg_dst_combo.pack(side="left")

        w3 = ttk.Frame(self.wfg_controls); w3.pack(fill="x", pady=(6, 0))
        ttk.Button(w3, text="Add Edge",  command=self.add_wfg_edge).pack(side="left", padx=(0, 6))
        ttk.Button(w3, text="Clear All", command=self.clear_all).pack(side="left")

        ttk.Label(self.wfg_controls,
                  text="Derived by collapsing resources.\nDeadlock ↔ cycle in WFG.",
                  foreground=TEXT_DIM, font=("Consolas", 8), justify="left").pack(anchor="w", pady=(6, 0))

        # --- Config card ---
        config_card = ttk.LabelFrame(panel, text="Configuration", padding=10)
        config_card.pack(side="left", fill="both", expand=True)

        c1 = ttk.Frame(config_card); c1.pack(fill="x", pady=2)
        ttk.Label(c1, text="Processes", width=10).pack(side="left")
        self.num_p_var = tk.StringVar(value="3")
        e1 = ttk.Spinbox(c1, textvariable=self.num_p_var, width=5, justify="center",
                         from_=1, to=6, increment=1, wrap=True)
        e1.pack(side="left")
        e1.bind("<Return>",   lambda e: self.rebuild_config())
        e1.bind("<FocusOut>", lambda e: self.rebuild_config())

        c2 = ttk.Frame(config_card); c2.pack(fill="x", pady=2)
        ttk.Label(c2, text="Resources", width=10).pack(side="left")
        self.num_r_var = tk.StringVar(value="2")
        e2 = ttk.Spinbox(c2, textvariable=self.num_r_var, width=5, justify="center",
                         from_=1, to=5, increment=1, wrap=True)
        e2.pack(side="left")
        e2.bind("<Return>",   lambda e: self.rebuild_config())
        e2.bind("<FocusOut>", lambda e: self.rebuild_config())

        c3 = ttk.Frame(config_card); c3.pack(fill="x", pady=(6, 6))
        ttk.Button(c3, text="Deadlock preset", command=lambda: self.load_preset("deadlock")).pack(side="left", padx=(0, 6))
        ttk.Button(c3, text="Safe preset",     command=lambda: self.load_preset("safe")).pack(side="left")

        ttk.Label(config_card, text="EDGES", foreground=TEXT_DIM,
                  font=("Consolas", 8, "bold")).pack(anchor="w")

        self.edge_list_frame = ttk.Frame(config_card)
        self.edge_list_frame.pack(fill="x")

        self.update_edge_ui()

    def _build_canvas(self):
        wrap = ttk.Frame(self, relief="solid", borderwidth=1)
        wrap.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.canvas = tk.Canvas(wrap, bg=SURFACE, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())

    def _build_status(self):
        self.status_label = tk.Label(self, text="Add edges to begin.", anchor="w",
                                     padx=10, pady=6, bg=SURFACE, fg=TEXT_DIM,
                                     font=("Consolas", 10))
        self.status_label.pack(fill="x", padx=8, pady=(0, 4))

    def _build_legend(self):
        legend = ttk.Frame(self)
        legend.pack(fill="x", padx=8, pady=(0, 8))
        items = [
            (PROC_COLOR,   "circle", "Process"),
            (RES_COLOR,    "square", "Resource"),
            (REQ_COLOR,    "arrow",  "Request / Wait"),
            (ASSIGN_COLOR, "arrow",  "Assignment"),
            (CYCLE_COLOR,  "cycle",  "Cycle (deadlock)"),
        ]
        for color, shape, label in items:
            item = ttk.Frame(legend)
            item.pack(side="left", padx=(0, 16))
            c = tk.Canvas(item, width=14, height=14, bg=BG, highlightthickness=0)
            c.pack(side="left", padx=(0, 4))
            if shape == "circle":
                c.create_oval(2, 2, 12, 12, fill=color, outline=color)
            elif shape == "square":
                c.create_rectangle(2, 2, 12, 12, fill=color, outline=color)
            elif shape == "arrow":
                c.create_line(1, 7, 13, 7, fill=color, width=2, arrow="last")
            elif shape == "cycle":
                c.create_text(7, 7, text="⟳", fill=color, font=("Consolas", 11, "bold"))
            ttk.Label(item, text=label, foreground=TEXT_DIM, font=("Consolas", 9)).pack(side="left")

    # ---------- Mode switching ----------
    def set_mode(self, mode):
        self.mode = mode
        self._update_tab_buttons()
        if mode == "rag":
            self.wfg_controls.pack_forget()
            self.rag_controls.pack(fill="x")
        else:
            self.rag_controls.pack_forget()
            self.wfg_controls.pack(fill="x")
        self.update_edge_ui()
        self.render_edge_list()
        self.detect()
        self.draw()

    def _update_tab_buttons(self):
        self.btn_rag.state(["pressed" if self.mode == "rag" else "!pressed"])
        self.btn_wfg.state(["pressed" if self.mode == "wfg" else "!pressed"])

    # ---------- Configuration ----------
    def rebuild_config(self):
        try:    np_ = max(1, min(6, int(self.num_p_var.get())))
        except: np_ = 3
        try:    nr_ = max(1, min(5, int(self.num_r_var.get())))
        except: nr_ = 2
        self.num_p_var.set(str(np_))
        self.num_r_var.set(str(nr_))

        self.processes = [{"id": "P"+str(i+1), "x": 0, "y": 0} for i in range(np_)]
        self.resources = [{"id": "R"+str(i+1), "x": 0, "y": 0} for i in range(nr_)]

        p_ids   = {p["id"] for p in self.processes}
        r_ids   = {r["id"] for r in self.resources}
        all_ids = p_ids | r_ids

        self.edges     = [e for e in self.edges     if e["src"] in all_ids and e["dst"] in all_ids]
        self.wfg_edges = [e for e in self.wfg_edges if e["src"] in p_ids   and e["dst"] in p_ids]

        self.populate_selects()
        self.layout()
        self.detect()
        self.draw()
        self.render_edge_list()

    def populate_selects(self):
        p_ids = [p["id"] for p in self.processes]
        r_ids = [r["id"] for r in self.resources]
        et = self.edge_type_var.get()

        if et.startswith("Request"):
            self.src_combo["values"] = p_ids
            self.dst_combo["values"] = r_ids
        else:
            self.src_combo["values"] = r_ids
            self.dst_combo["values"] = p_ids

        if self.src_combo["values"] and self.src_var.get() not in self.src_combo["values"]:
            self.src_var.set(self.src_combo["values"][0])
        if self.dst_combo["values"] and self.dst_var.get() not in self.dst_combo["values"]:
            self.dst_var.set(self.dst_combo["values"][0])

        self.wfg_src_combo["values"] = p_ids
        self.wfg_dst_combo["values"] = p_ids
        if p_ids:
            if self.wfg_src_var.get() not in p_ids:
                self.wfg_src_var.set(p_ids[0])
            if self.wfg_dst_var.get() not in p_ids:
                self.wfg_dst_var.set(p_ids[-1] if len(p_ids) > 1 else p_ids[0])

    def update_edge_ui(self):
        et = self.edge_type_var.get()
        if et.startswith("Request"):
            self.src_lbl.config(text="Process")
            self.dst_lbl.config(text="Resource")
        else:
            self.src_lbl.config(text="Resource")
            self.dst_lbl.config(text="Process")
        self.populate_selects()

    # ---------- Layout ----------
    def layout(self):
        self.canvas.update_idletasks()
        w = self.canvas.winfo_width() or 600
        h = self.canvas.winfo_height() or 420
        cx, cy = w / 2, h / 2
        np_ = max(1, len(self.processes))
        nr_ = max(1, len(self.resources))

        node_margin = 28
        outer_radius = max(0, min(cx, cy) - 70)
        r_p = min(outer_radius, w / 2 - 70, h / 2 - 70)
        r_p = max(120, r_p)

        r_r = min(outer_radius * 0.65, r_p - 100)
        r_r = max(80, r_r)

        min_x = node_margin
        max_x = max(node_margin, w - node_margin)
        min_y = node_margin
        max_y = max(node_margin, h - node_margin)

        for i, p in enumerate(self.processes):
            a = (i / np_) * math.pi * 2 - math.pi / 2
            x = cx + math.cos(a) * r_p
            y = cy + math.sin(a) * r_p
            p["x"] = min(max_x, max(min_x, x))
            p["y"] = min(max_y, max(min_y, y))

        for i, r in enumerate(self.resources):
            a = (i / nr_) * math.pi * 2 - math.pi / 2 + math.pi / nr_
            x = cx + math.cos(a) * r_r
            y = cy + math.sin(a) * r_r
            r["x"] = min(max_x, max(min_x, x))
            r["y"] = min(max_y, max(min_y, y))

    # ---------- Edge management ----------
    def add_edge(self):
        et  = self.edge_type_var.get()
        src = self.src_var.get()
        dst = self.dst_var.get()
        if not src or not dst:
            return
        if any(e["src"] == src and e["dst"] == dst for e in self.edges):
            return
        edge_type = "request" if et.startswith("Request") else "assignment"
        self.edges.append({"src": src, "dst": dst, "type": edge_type})
        self.render_edge_list(); self.detect(); self.draw()

    def add_wfg_edge(self):
        src = self.wfg_src_var.get()
        dst = self.wfg_dst_var.get()
        if not src or not dst or src == dst:
            return
        if any(e["src"] == src and e["dst"] == dst for e in self.wfg_edges):
            return
        self.wfg_edges.append({"src": src, "dst": dst})
        self.render_edge_list(); self.detect(); self.draw()

    def remove_edge(self, idx):
        arr = self.edges if self.mode == "rag" else self.wfg_edges
        if 0 <= idx < len(arr):
            arr.pop(idx)
        self.render_edge_list(); self.detect(); self.draw()

    def clear_all(self):
        if self.mode == "rag":
            self.edges = []
        else:
            self.wfg_edges = []
        self.render_edge_list(); self.detect(); self.draw()

    def render_edge_list(self):
        for w in self.edge_list_frame.winfo_children():
            w.destroy()
        arr = self.edges if self.mode == "rag" else self.wfg_edges
        if not arr:
            ttk.Label(self.edge_list_frame, text="No edges yet.",
                      foreground=TEXT_DIM, font=("Consolas", 9)).pack(anchor="w", pady=2)
            return
        for i, e in enumerate(arr):
            row = ttk.Frame(self.edge_list_frame)
            row.pack(fill="x", pady=1)
            label = f'{e["src"]} → {e["dst"]}'
            if e.get("type"):
                label += f' ({e["type"]})'
            ttk.Label(row, text=label, font=("Consolas", 9)).pack(side="left")
            ttk.Button(row, text="×", width=2,
                       command=lambda idx=i: self.remove_edge(idx)).pack(side="right")

    # ---------- Deadlock detection ----------
    def detect(self):
        self.deadlock_cycle = []
        active_edges = self.edges if self.mode == "rag" else self.wfg_edges
        if not active_edges:
            self.set_status("safe", "No edges — no deadlock."); return

        graph = {}
        all_nodes = [p["id"] for p in self.processes]
        if self.mode == "rag":
            all_nodes += [r["id"] for r in self.resources]
        for n in all_nodes:
            graph[n] = []
        for e in active_edges:
            graph.setdefault(e["src"], []).append(e["dst"])

        cycle_nodes = detect_cycle(graph)

        if cycle_nodes:
            self.deadlock_cycle = cycle_nodes
            cycle_str = " → ".join(cycle_nodes) + " → " + cycle_nodes[0]
            self.set_status("deadlock", f"⚠ Deadlock detected! Cycle: {cycle_str}")
        else:
            self.set_status("safe", "✓ No deadlock — graph is acyclic.")

    def set_status(self, kind, msg):
        if kind == "deadlock":
            self.status_label.config(bg=COL_DANGER_BG, fg=COL_DANGER_TXT, text=msg)
        elif kind == "safe":
            self.status_label.config(bg=COL_SUCCESS_BG, fg=COL_SUCCESS_TXT, text=msg)
        else:
            self.status_label.config(bg=SURFACE, fg=TEXT_DIM, text=msg)

    # ---------- Drawing ----------
    def get_node(self, node_id):
        for p in self.processes:
            if p["id"] == node_id: return p
        for r in self.resources:
            if r["id"] == node_id: return r
        return None

    def is_in_cycle(self, nid):   return nid in self.deadlock_cycle
    def is_cycle_edge(self, s, d):
        if not self.deadlock_cycle: return False
        n = len(self.deadlock_cycle)
        return any(self.deadlock_cycle[i] == s and self.deadlock_cycle[(i+1)%n] == d
                   for i in range(n))

    def edge_points(self, sn, dn, sr, dr):
        dx, dy = dn["x"]-sn["x"], dn["y"]-sn["y"]
        L = math.hypot(dx, dy) or 1
        ux, uy = dx/L, dy/L
        return sn["x"]+ux*sr, sn["y"]+uy*sr, dn["x"]-ux*dr, dn["y"]-uy*dr

    def draw_arrow(self, x1, y1, x2, y2, color, dashed=False):
        if math.hypot(x2-x1, y2-y1) < 1: return
        dash = (5, 4) if dashed else None
        self.canvas.create_line(x1, y1, x2, y2, fill=color,
                                width=2 if dashed else 1.5,
                                dash=dash, arrow="last", arrowshape=(10, 12, 4))

    def draw(self):
        self.canvas.delete("all")
        self.layout()
        if self.mode == "rag": self.draw_rag()
        else:                  self.draw_wfg()

    def draw_rag(self):
        is_p = lambda nid: any(p["id"] == nid for p in self.processes)
        for e in self.edges:
            sn = self.get_node(e["src"]); dn = self.get_node(e["dst"])
            if not sn or not dn: continue
            sr = 22 if is_p(e["src"]) else 20
            dr = 22 if is_p(e["dst"]) else 20
            x1, y1, x2, y2 = self.edge_points(sn, dn, sr, dr)
            cycle_e = self.is_cycle_edge(e["src"], e["dst"])
            col = CYCLE_COLOR if cycle_e else (ASSIGN_COLOR if e["type"]=="assignment" else REQ_COLOR)
            self.draw_arrow(x1, y1, x2, y2, col, dashed=cycle_e)

        for r in self.resources:
            in_c = self.is_in_cycle(r["id"])
            s, col = 20, CYCLE_COLOR if in_c else RES_COLOR
            self.canvas.create_rectangle(r["x"]-s, r["y"]-s, r["x"]+s, r["y"]+s,
                                          outline=col, width=2.5 if in_c else 1.5, fill="#3a2c1a")
            self.canvas.create_text(r["x"], r["y"], text=r["id"], fill=col,
                                     font=("Consolas", 11, "bold"))

        for p in self.processes:
            in_c = self.is_in_cycle(p["id"])
            col = CYCLE_COLOR if in_c else PROC_COLOR
            self.canvas.create_oval(p["x"]-22, p["y"]-22, p["x"]+22, p["y"]+22,
                                     outline=col, width=2.5 if in_c else 1.5, fill="#1e3a5f")
            self.canvas.create_text(p["x"], p["y"], text=p["id"], fill=col,
                                     font=("Consolas", 11, "bold"))

    def draw_wfg(self):
        active = self.wfg_edges
        note = None
        if not active and self.edges:
            requests    = [e for e in self.edges if e["type"]=="request"]
            assignments = [e for e in self.edges if e["type"]=="assignment"]
            derived = []
            for req in requests:
                for asgn in assignments:
                    if asgn["src"]==req["dst"] and asgn["dst"]!=req["src"]:
                        if not any(d["src"]==req["src"] and d["dst"]==asgn["dst"] for d in derived):
                            derived.append({"src": req["src"], "dst": asgn["dst"]})
            active = derived
            note = "Auto-derived from RAG edges."

        for e in active:
            sn = next((p for p in self.processes if p["id"]==e["src"]), None)
            dn = next((p for p in self.processes if p["id"]==e["dst"]), None)
            if not sn or not dn: continue
            x1,y1,x2,y2 = self.edge_points(sn, dn, 22, 22)
            cycle_e = self.is_cycle_edge(e["src"], e["dst"])
            col = CYCLE_COLOR if cycle_e else WFG_COLOR
            self.draw_arrow(x1, y1, x2, y2, col, dashed=cycle_e)

        for p in self.processes:
            in_c = self.is_in_cycle(p["id"])
            col = CYCLE_COLOR if in_c else WFG_COLOR
            self.canvas.create_oval(p["x"]-22, p["y"]-22, p["x"]+22, p["y"]+22,
                                     outline=col, width=2.5 if in_c else 1.5, fill="#3a1e4f")
            self.canvas.create_text(p["x"], p["y"], text=p["id"], fill=col,
                                     font=("Consolas", 11, "bold"))

        if note:
            self.canvas.create_text(10, 14, text=note, fill=TEXT_DIM,
                                     font=("Consolas", 9), anchor="w")

    # ---------- Presets ----------
    def load_preset(self, kind):
        self.edges = []; self.wfg_edges = []
        self.num_p_var.set("3"); self.num_r_var.set("2")
        self.processes = [{"id":"P"+str(i+1),"x":0,"y":0} for i in range(3)]
        self.resources = [{"id":"R"+str(i+1),"x":0,"y":0} for i in range(2)]

        if kind == "deadlock":
            self.edges = [
                {"src":"R1","dst":"P1","type":"assignment"},
                {"src":"P1","dst":"R2","type":"request"},
                {"src":"R2","dst":"P2","type":"assignment"},
                {"src":"P2","dst":"R1","type":"request"},
            ]
            if self.mode == "wfg":
                self.wfg_edges = [{"src":"P1","dst":"P2"},{"src":"P2","dst":"P1"}]
        else:
            self.edges = [
                {"src":"R1","dst":"P1","type":"assignment"},
                {"src":"R2","dst":"P2","type":"assignment"},
                {"src":"P3","dst":"R1","type":"request"},
            ]

        self.populate_selects()
        self.layout(); self.detect(); self.draw(); self.render_edge_list()


# ════════════════════════════════════════════════════════════
#  Drop-in screen class
# ════════════════════════════════════════════════════════════

class DeadlockScreen:
    """
    Drop-in screen class — mirrors the structure of CPUScreen / MemoryScreen /
    StorageScreen / VirtualMemoryScreen.

    Pass the parent content frame from home.py:
        DeadlockScreen(self.content)
    """

    def __init__(self, parent_frame):
        self.parent = parent_frame
        self._build_ui()

    def _build_ui(self):
        self.parent.configure(bg=BG)
        self._style()

        # ── Title bar ─────────────────────────────────────────────────────
        title_bar = tk.Frame(self.parent, bg=SURFACE, pady=10)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="Deadlock Simulator",
                 font=("Consolas", 18, "bold"), fg=ACCENT, bg=SURFACE).pack()
        tk.Label(title_bar, text="Banker's Algorithm · Resource Allocation Graph · Wait-For Graph",
                 font=("Consolas", 10), fg=TEXT_DIM, bg=SURFACE).pack()

        # ── Notebook (tabs) ──────────────────────────────────────────────
        notebook = ttk.Notebook(self.parent)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        bankers_tab = BankersTab(notebook)
        rag_tab     = RagWfgTab(notebook)

        notebook.add(bankers_tab, text="  Banker's Algorithm  ")
        notebook.add(rag_tab,     text="  RAG / Wait-For Graph  ")

    def _style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".",                background=BG, foreground=TEXT, font=("Consolas", 10))
        style.configure("TFrame",           background=BG)
        style.configure("TLabel",           background=BG, foreground=TEXT)
        style.configure("TLabelframe",      background=BG, foreground=TEXT, bordercolor=BORDER)
        style.configure("TLabelframe.Label",background=BG, foreground=TEXT_DIM, font=("Consolas", 9, "bold"))
        style.configure("TButton",          background=SURFACE, foreground=TEXT, padding=6)
        style.map("TButton",
                  background=[("pressed", ACCENT), ("active", BORDER)],
                  foreground=[("pressed", BG)])
        style.configure("TEntry",           fieldbackground=SURFACE, foreground=TEXT,
                         insertcolor=TEXT, bordercolor=BORDER)
        style.configure("TSpinbox",         fieldbackground=SURFACE, foreground=TEXT,
                         insertcolor=TEXT, bordercolor=BORDER, arrowcolor=TEXT_DIM)
        style.configure("TCombobox",        fieldbackground=SURFACE, foreground=TEXT,
                         background=SURFACE, arrowcolor=TEXT_DIM, selectbackground=SURFACE)
        style.map("TCombobox",
                  fieldbackground=[("readonly", SURFACE), ("!readonly", SURFACE)],
                  background=[("readonly", SURFACE), ("!readonly", SURFACE)],
                  foreground=[("readonly", TEXT), ("!readonly", TEXT)],
                  arrowcolor=[("readonly", TEXT_DIM), ("!readonly", TEXT_DIM)])
        style.configure("TNotebook",        background=BG, bordercolor=BORDER)
        style.configure("TNotebook.Tab",    background=SURFACE, foreground=TEXT, padding=(14, 6))
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])
        style.configure("TSeparator",       background=BORDER)
        style.configure("TScrollbar",       background=SURFACE, troughcolor=BG,
                         arrowcolor=TEXT, bordercolor=BORDER)


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Deadlock Simulator")
    root.configure(bg=BG)
    root.geometry("1100x900")

    frame = tk.Frame(root, bg=BG)
    frame.pack(fill="both", expand=True)
    DeadlockScreen(frame)

    root.mainloop()
