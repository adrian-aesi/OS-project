import tkinter as tk
from tkinter import ttk

from gui.cpu_screen import CPUScreen

BG      = "#1e1e2e"
SURFACE = "#2a2a3e"
ACCENT  = "#7c6af7"
ACCENT2 = "#56cfb2"
TEXT    = "#e0e0f0"
TEXT_DIM= "#888899"
BORDER  = "#3a3a55"


class HomeScreen:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OS Simulator")
        self.root.geometry("1200x1080")
        self.root.configure(bg=BG)
        self.root.minsize(1000, 1000)

        self._active_btn = None
        self._build_layout()
        self._active_label = "🏠  Home"
        self._nav_buttons["🏠  Home"].configure(fg=BG, bg=ACCENT)
        self.show_welcome()

    # ══════════════════════════════════════════
    #  LAYOUT
    # ══════════════════════════════════════════

    def _build_layout(self):
        # ── Sidebar ────────────────────────────
        self.sidebar = tk.Frame(self.root, width=220, bg=SURFACE)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo / title area
        logo_frame = tk.Frame(self.sidebar, bg=ACCENT, pady=18)
        logo_frame.pack(fill="x")

        tk.Label(
            logo_frame,
            text="OS",
            font=("Consolas", 28, "bold"),
            fg=BG, bg=ACCENT
        ).pack()

        tk.Label(
            logo_frame,
            text="SIMULATOR",
            font=("Consolas", 9, "bold"),
            fg=BG, bg=ACCENT
        ).pack()

        # Nav buttons
        nav_frame = tk.Frame(self.sidebar, bg=SURFACE)
        nav_frame.pack(fill="both", expand=True, pady=20)

        nav_items = [
            ("🏠  Home",             self.show_welcome),
            ("⚙️  CPU Scheduling",   self.show_cpu),
            ("🧠  Memory Mgmt",      self.show_memory),
            ("💾  Virtual Memory",   self.show_virtual),
            ("📀  Mass Storage",     self.show_storage),
        ]

        # Store commands by label so card buttons can look them up
        self._nav_commands = {label: cmd for label, cmd in nav_items}
        self._active_label = None

        self._nav_buttons = {}
        for label, cmd in nav_items:
            btn = tk.Button(
                nav_frame,
                text=label,
                font=("Consolas", 11),
                fg=TEXT_DIM,
                bg=SURFACE,
                activebackground=ACCENT,
                activeforeground=BG,
                relief="flat",
                anchor="w",
                padx=20,
                pady=10,
                cursor="hand2",
                command=lambda c=cmd, b=label: self._nav_click(c, b)
            )
            btn.pack(fill="x")
            self._nav_buttons[label] = btn

        # Version tag at bottom
        tk.Label(
            self.sidebar,
            text="v1.0  |  OS Project",
            font=("Consolas", 8),
            fg=TEXT_DIM, bg=SURFACE
        ).pack(side="bottom", pady=10)

        # ── Content area (scrollable) ──────────
        content_outer = tk.Frame(self.root, bg=BG)
        content_outer.pack(side="right", fill="both", expand=True)

        # Scrollable canvas wrapper
        self._canvas = tk.Canvas(content_outer, bg=BG, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(content_outer, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self._canvas, bg=BG)
        self._canvas_window = self._canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_resize)
        self._canvas.bind("<Configure>", self._on_canvas_resize)

        # Mouse wheel scroll
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1 * (e.delta // 120), "units"))

    def _on_content_resize(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _nav_click(self, command, label):
        # Don't reset if already on this screen
        if self._active_label == label:
            return
        self._active_label = label
        # Reset all buttons
        for lbl, btn in self._nav_buttons.items():
            btn.configure(fg=TEXT_DIM, bg=SURFACE)
        # Highlight active
        self._nav_buttons[label].configure(fg=BG, bg=ACCENT)
        command()

    # ══════════════════════════════════════════
    #  CLEAR CONTENT
    # ══════════════════════════════════════════

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()
        # Reset scroll position
        self._canvas.yview_moveto(0)

    # ══════════════════════════════════════════
    #  SCREENS
    # ══════════════════════════════════════════

    def show_welcome(self):
        self.clear_content()

        wrapper = tk.Frame(self.content, bg=BG)
        wrapper.pack(expand=True, pady=80)

        tk.Label(
            wrapper,
            text="Operating Systems Simulator",
            font=("Consolas", 26, "bold"),
            fg=ACCENT, bg=BG
        ).pack(pady=(0, 10))

        tk.Label(
            wrapper,
            text="Select a module from the left sidebar to begin.",
            font=("Consolas", 13),
            fg=TEXT_DIM, bg=BG
        ).pack(pady=(0, 40))

        modules = [
            ("⚙️  CPU Scheduling",  "FCFS · SJF · SRTF · Priority · Round Robin",   "⚙️  CPU Scheduling"),
            ("🧠  Memory Mgmt",     "With / without compaction",                      "🧠  Memory Mgmt"),
            ("💾  Virtual Memory",  "SSTF disk scheduling & track count",             "💾  Virtual Memory"),
            ("📀  Mass Storage",    "Mass storage management",                        "📀  Mass Storage"),
        ]

        cards_frame = tk.Frame(wrapper, bg=BG)
        cards_frame.pack()

        for i, (title, desc, nav_label) in enumerate(modules):
            card = tk.Frame(cards_frame, bg=SURFACE, bd=0, relief="flat", padx=20, pady=18, cursor="hand2")
            card.grid(row=i // 2, column=i % 2, padx=10, pady=10, sticky="nsew")

            tk.Label(card, text=title, font=("Consolas", 13, "bold"), fg=ACCENT2, bg=SURFACE).pack(anchor="w")
            tk.Label(card, text=desc,  font=("Consolas", 10),         fg=TEXT_DIM, bg=SURFACE).pack(anchor="w", pady=(4, 8))

            tk.Button(
                card, text="Open →",
                command=lambda l=nav_label: self._nav_click(self._nav_commands[l], l),
                font=("Consolas", 10, "bold"),
                bg=ACCENT, fg=BG,
                relief="flat", cursor="hand2", padx=10, pady=4
            ).pack(anchor="w")

    def show_cpu(self):
        self.clear_content()
        CPUScreen(self.content)

    def show_memory(self):
        self.clear_content()
        self._placeholder("Memory Management", "🧠", "Coming soon — memory allocation with/without compaction.")

    def show_virtual(self):
        self.clear_content()
        self._placeholder("Virtual Memory", "💾", "Coming soon — SSTF disk scheduling & track count diagram.")

    def show_storage(self):
        self.clear_content()
        self._placeholder("Mass Storage Management", "📀", "Coming soon — mass storage management module.")

    def _placeholder(self, title, icon, msg):
        f = tk.Frame(self.content, bg=BG)
        f.pack(expand=True, pady=100)

        tk.Label(f, text=icon,  font=("Consolas", 40), fg=ACCENT,   bg=BG).pack()
        tk.Label(f, text=title, font=("Consolas", 20, "bold"), fg=TEXT, bg=BG).pack(pady=(10, 6))
        tk.Label(f, text=msg,   font=("Consolas", 12), fg=TEXT_DIM, bg=BG).pack()

    def run(self):
        self.root.mainloop()