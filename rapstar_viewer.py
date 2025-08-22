import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import math
import os

# --------------- Utility ---------------

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# --------------- Main App ---------------

class RapStarApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RAPSTAR — Lyrics Viewer (Bring Your Own Text)")
        self.geometry("980x640")
        self.minsize(860, 520)
        self.configure(bg="#0b0f14")

        # State
        self.theme = "dark"
        self.typewriter_running = False
        self.typewriter_paused = False
        self.typewriter_thread = None
        self.autoscroll = tk.BooleanVar(value=True)
        self.current_index = "1.0"
        self.full_text_cache = ""
        self.search_term = tk.StringVar()
        self.fps = 60
        self.particles = []
        self.wave_phase = 0.0

        # Styles
        self._make_styles()

        # Layout
        self._build_header()
        self._build_controls()
        self._build_editor()
        self._build_statusbar()

        # Particles background
        self._build_particles()
        self.after(int(1000 / self.fps), self._animate)

        # Keyboard bindings
        self.bind("<Control-Return>", lambda e: self.play_typewriter())
        self.bind("<Control-p>", lambda e: self.pause_typewriter())
        self.bind("<Control-s>", lambda e: self.stop_typewriter())
        self.bind("<Control-f>", lambda e: (self.search_entry.focus_set(), self.search_entry.select_range(0, tk.END)))
        self.bind("<Control-o>", lambda e: self.load_txt())
        self.bind("<Control-e>", lambda e: self.export_txt())
        self.bind("<Control-l>", lambda e: self.toggle_theme())

        # Demo placeholder (no copyrighted text)
        placeholder = (
            "Paste or load your lyrics/text here.\n\n"
            "Tips:\n"
            "• Press Ctrl+O to load a .txt file\n"
            "• Press Ctrl+Enter to start the typewriter\n"
            "• Use the speed slider for pace\n"
            "• Toggle Auto-Scroll for live scrolling\n"
            "• Ctrl+F to search\n"
            "• Ctrl+E to export\n"
        )
        self.text.insert("1.0", placeholder)
        self._update_counts()

    # ---------- UI construction ----------

    def _make_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        # Dark style defaults
        self.style.configure("TButton", padding=8, font=("Segoe UI", 10))
        self.style.configure("Accent.TButton", padding=8, font=("Segoe UI Semibold", 10))
        self.style.configure("TLabel", foreground="#cbd5e1", background="#0b0f14")
        self.style.configure("TCheckbutton", background="#0b0f14", foreground="#cbd5e1")
        self.style.configure("TScale", background="#0b0f14")
        self.style.configure("Header.TLabel", font=("Segoe UI Black", 20))
        self.style.configure("Mono.TLabel", font=("JetBrains Mono", 9))

    def _build_header(self):
        self.header = tk.Frame(self, bg="#0b0f14")
        self.header.pack(fill="x", padx=16, pady=(12, 4))

        # Neon animated title (drawn on canvas for glow)
        self.title_canvas = tk.Canvas(self.header, height=48, bg="#0b0f14", highlightthickness=0)
        self.title_canvas.pack(side="left", fill="x", expand=True)
        self.neon_text = "RAPSTAR"
        self.subtitle_text = "Bring your own lyrics — Typewriter & FX"
        self.neon_t = 0

        # Theme toggle
        self.theme_btn = ttk.Button(self.header, text="🌗 Theme (Ctrl+L)", command=self.toggle_theme)
        self.theme_btn.pack(side="right", padx=6)

    def _build_controls(self):
        controls = tk.Frame(self, bg="#0b0f14")
        controls.pack(fill="x", padx=16, pady=6)

        # File actions
        ttk.Button(controls, text="📂 Load .txt (Ctrl+O)", command=self.load_txt).pack(side="left", padx=4)
        ttk.Button(controls, text="💾 Export (Ctrl+E)", command=self.export_txt).pack(side="left", padx=4)
        ttk.Button(controls, text="🧹 Clear", command=self.clear_text).pack(side="left", padx=4)

        # Spacer
        tk.Frame(controls, width=16, bg="#0b0f14").pack(side="left")

        # Typewriter controls
        ttk.Button(controls, style="Accent.TButton", text="▶ Play (Ctrl+Enter)", command=self.play_typewriter).pack(side="left", padx=4)
        ttk.Button(controls, text="⏸ Pause (Ctrl+P)", command=self.pause_typewriter).pack(side="left", padx=4)
        ttk.Button(controls, text="⏹ Stop (Ctrl+S)", command=self.stop_typewriter).pack(side="left", padx=4)

        # Speed
        tk.Label(controls, text="Speed:", bg="#0b0f14", fg="#94a3b8").pack(side="left", padx=(16, 4))
        self.speed_var = tk.DoubleVar(value=1.0)  # chars per frame baseline
        self.speed_slider = ttk.Scale(controls, from_=0.2, to=5.0, variable=self.speed_var, length=140, command=lambda e: None)
        self.speed_slider.pack(side="left", padx=4)

        # Font size
        tk.Label(controls, text="Font:", bg="#0b0f14", fg="#94a3b8").pack(side="left", padx=(16, 4))
        self.font_var = tk.IntVar(value=14)
        self.font_slider = ttk.Scale(controls, from_=10, to=28, variable=self.font_var, length=140, command=self._apply_font)
        self.font_slider.pack(side="left", padx=4)

        # Autoscroll
        ttk.Checkbutton(controls, text="Auto-Scroll", variable=self.autoscroll).pack(side="left", padx=12)

        # Search
        tk.Label(controls, text="Find:", bg="#0b0f14", fg="#94a3b8").pack(side="left", padx=(16, 4))
        self.search_entry = ttk.Entry(controls, textvariable=self.search_term, width=18)
        self.search_entry.pack(side="left", padx=4)
        ttk.Button(controls, text="Next", command=self.search_next).pack(side="left", padx=2)
        ttk.Button(controls, text="Prev", command=self.search_prev).pack(side="left", padx=2)
        ttk.Button(controls, text="✖ Clear Highlights", command=self.clear_search_highlights).pack(side="left", padx=6)

    def _build_editor(self):
        editor_wrap = tk.Frame(self, bg="#0b0f14")
        editor_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Canvas background (stars) sits behind
        self.bg_canvas = tk.Canvas(editor_wrap, bg="#0b0f14", highlightthickness=0)
        self.bg_canvas.pack(fill="both", expand=True, side="left")
        self.bg_canvas.lower()

        # Scrollable text frame on top
        text_frame = tk.Frame(editor_wrap, bg="#0b0f14")
        text_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.98, relheight=0.96)

        self.text = tk.Text(
            text_frame, wrap="word", undo=True, padx=16, pady=16,
            bg="#0f172a", fg="#e2e8f0", insertbackground="#e2e8f0",
            relief="flat"
        )
        self.text.configure(font=("Segoe UI", 14))
        self.text.tag_configure("highlight", background="#fde68a", foreground="#1f2937")
        self.text.tag_configure("wave", underline=1)

        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True, side="left")

        self.text.bind("<<Modified>>", self._on_text_changed)

    def _build_statusbar(self):
        status = tk.Frame(self, bg="#0b0f14")
        status.pack(fill="x", padx=16, pady=(0, 10))
        self.counts_label = ttk.Label(status, text="0 chars • 0 words • 0 lines", style="Mono.TLabel")
        self.counts_label.pack(side="left")
        self.wave_label = ttk.Label(status, text="Wave FX: idle", style="Mono.TLabel")
        self.wave_label.pack(side="right")

    # ---------- Background Particles & Neon Title ----------

    def _build_particles(self):
        # Create a set of particles (stars)
        self.num_particles = 70
        self.particles = []
        w = max(self.winfo_width(), 980)
        h = max(self.winfo_height(), 640)
        for _ in range(self.num_particles):
            x = self._rand(0, w)
            y = self._rand(0, h)
            r = self._rand(1, 3)
            vx = self._rand(-0.4, 0.4)
            vy = self._rand(-0.25, 0.25)
            alpha = self._rand(0.3, 1.0)
            pid = self.bg_canvas.create_oval(x-r, y-r, x+r, y+r, fill=self._rgba("#7dd3fc", alpha), outline="")
            self.particles.append({"id": pid, "x": x, "y": y, "r": r, "vx": vx, "vy": vy, "a": alpha})

        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        # Keep particles within bounds
        pass

    def _animate(self):
        # Animate particles
        w = max(self.bg_canvas.winfo_width(), 100)
        h = max(self.bg_canvas.winfo_height(), 100)
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            # wrap
            if p["x"] < 0: p["x"] = w
            if p["x"] > w: p["x"] = 0
            if p["y"] < 0: p["y"] = h
            if p["y"] > h: p["y"] = 0
            self.bg_canvas.coords(p["id"], p["x"]-p["r"], p["y"]-p["r"], p["x"]+p["r"], p["y"]+p["r"])

        # Animate neon title
        self._draw_neon_title()

        # Animate wave underline for a subtle “music” vibe
        self.wave_phase += 0.12
        self.wave_label.config(text=f"Wave FX: phase {self.wave_phase:.2f}")

        self.after(int(1000 / self.fps), self._animate)

    def _draw_neon_title(self):
        cw = self.title_canvas.winfo_width()
        ch = self.title_canvas.winfo_height()
        self.title_canvas.delete("all")

        # Rainbow gradient over time
        self.neon_t += 0.02
        hue = (math.sin(self.neon_t) + 1) / 2  # 0..1
        color = self._hsl_to_hex(hue, 0.75, 0.6)

        # Shadow/glow layers
        self.title_canvas.create_text(cw//2, ch//2, text=self.neon_text, font=("Segoe UI Black", 28), fill="#000000", tags="t", offset="1")
        for spread in (2, 4, 6, 8):
            self.title_canvas.create_text(cw//2, ch//2, text=self.neon_text, font=("Segoe UI Black", 28),
                                          fill=self._fade(color, 0.08), tags="t")
        self.title_canvas.create_text(cw//2, ch//2, text=self.neon_text, font=("Segoe UI Black", 28), fill=color, tags="t")

        self.title_canvas.create_text(cw//2, ch//2+22, text=self.subtitle_text, font=("Segoe UI", 10),
                                      fill="#94a3b8")

    # ---------- Text utilities ----------

    def _on_text_changed(self, event=None):
        if self.text.edit_modified():
            self._update_counts()
            self.text.edit_modified(False)

    def _update_counts(self):
        content = self.text.get("1.0", "end-1c")
        chars = len(content)
        words = len(content.split())
        lines = int(self.text.index("end-1c").split(".")[0])
        self.counts_label.config(text=f"{chars} chars • {words} words • {lines} lines")

    def _apply_font(self, *_):
        size = int(self.font_var.get())
        self.text.configure(font=("Segoe UI", size))

    # ---------- File actions ----------

    def load_txt(self):
        path = filedialog.askopenfilename(title="Load a .txt file", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            self.stop_typewriter()
            self.text.delete("1.0", "end")
            self.text.insert("1.0", data)
            self.current_index = "1.0"
            self._update_counts()
            messagebox.showinfo("Loaded", f"Loaded: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def export_txt(self):
        data = self.text.get("1.0", "end-1c")
        if not data.strip():
            messagebox.showwarning("Empty", "Nothing to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text Files", "*.txt")],
                                            title="Export text")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            messagebox.showinfo("Exported", f"Saved to: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    def clear_text(self):
        self.stop_typewriter()
        self.text.delete("1.0", "end")
        self.current_index = "1.0"
        self._update_counts()

    # ---------- Typewriter ----------

    def play_typewriter(self):
        if self.typewriter_running and self.typewriter_paused:
            self.typewriter_paused = False
            return
        if self.typewriter_running:
            return
        self.typewriter_running = True
        self.typewriter_paused = False
        self.full_text_cache = self.text.get("1.0", "end-1c")
        # Clear and start from top
        self.text.delete("1.0", "end")
        self.current_index = "1.0"

        def run():
            i = 0
            L = len(self.full_text_cache)
            last_scroll_time = time.time()
            while self.typewriter_running and i < L:
                if self.typewriter_paused:
                    time.sleep(0.05)
                    continue
                # Characters per tick depends on slider
                cps = clamp(self.speed_var.get(), 0.2, 5.0) * 3.0
                step = max(1, int(cps))
                chunk = self.full_text_cache[i:i+step]
                self.text.insert("end", chunk)
                i += step

                # Wave underline on current line (faint)
                self._underline_wave()

                # Auto-scroll occasionally
                if self.autoscroll.get() and (time.time() - last_scroll_time) > 0.03:
                    self.text.see("end")
                    last_scroll_time = time.time()

                time.sleep(1 / self.fps)

            self.typewriter_running = False
            self.typewriter_paused = False

        self.typewriter_thread = threading.Thread(target=run, daemon=True)
        self.typewriter_thread.start()

    def pause_typewriter(self):
        if self.typewriter_running:
            self.typewriter_paused = True

    def stop_typewriter(self):
        self.typewriter_running = False
        self.typewriter_paused = False

    def _underline_wave(self):
        # Apply a moving underline to the current line
        self.text.tag_remove("wave", "1.0", "end")
        try:
            line_index = self.text.index("insert").split(".")[0]
        except Exception:
            return
        start = f"{line_index}.0"
        end = f"{line_index}.end"
        self.text.tag_add("wave", start, end)

    # ---------- Search & Highlights ----------

    def clear_search_highlights(self):
        self.text.tag_remove("highlight", "1.0", "end")

    def _search(self, term, backwards=False):
        self.clear_search_highlights()
        if not term:
            return
        idx = self.text.index("insert")
        start = "1.0" if not backwards else idx
        count = tk.IntVar()
        pos = self.text.search(term, start, stopindex="end", count=count, nocase=True, backwards=backwards)
        if pos:
            end = f"{pos}+{count.get()}c"
            self.text.tag_add("highlight", pos, end)
            self.text.mark_set("insert", end)
            self.text.see(pos)

    def search_next(self):
        self._search(self.search_term.get(), backwards=False)

    def search_prev(self):
        self._search(self.search_term.get(), backwards=True)

    # ---------- Theme ----------

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        if self.theme == "dark":
            bg = "#0b0f14"; pane = "#0f172a"; fg = "#e2e8f0"; insert = "#e2e8f0"
            self.style.configure("TLabel", foreground="#cbd5e1", background=bg)
            self.style.configure("TCheckbutton", background=bg, foreground="#cbd5e1")
        else:
            bg = "#f8fafc"; pane = "#ffffff"; fg = "#0f172a"; insert = "#0f172a"
            self.style.configure("TLabel", foreground="#0f172a", background=bg)
            self.style.configure("TCheckbutton", background=bg, foreground="#0f172a")

        self.configure(bg=bg); self.header.configure(bg=bg)
        self.title_canvas.configure(bg=bg)
        self.theme_btn.configure(text="🌗 Theme (Ctrl+L)")
        self.text.configure(bg=pane, fg=fg, insertbackground=insert)
        self.bg_canvas.configure(bg=bg)

    # ---------- Color helpers ----------

    def _fade(self, hex_color, alpha):
        r = int(hex_color[1:3], 16); g = int(hex_color[3:5], 16); b = int(hex_color[5:7], 16)
        return f"#{int(r*alpha):02x}{int(g*alpha):02x}{int(b*alpha):02x}"

    def _rgba(self, hex_color, alpha):
        # Tkinter doesn't support real RGBA fills; we approximate by brightness scaling
        return self._fade(hex_color, alpha)

    def _hsl_to_hex(self, h, s, l):
        # h,s,l in 0..1
        def hue2rgb(p, q, t):
            if t < 0: t += 1
            if t > 1: t -= 1
            if t < 1/6: return p + (q - p) * 6 * t
            if t < 1/2: return q
            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
            return p
        if s == 0:
            r = g = b = l
        else:
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue2rgb(p, q, h + 1/3)
            g = hue2rgb(p, q, h)
            b = hue2rgb(p, q, h - 1/3)
        return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))

    def _rand(self, a, b):
        # simple deterministic-ish random without numpy
        return a + (b - a) * (hash((time.time_ns(), id(self))) % 1000) / 1000.0

# --------------- Run ---------------

if __name__ == "__main__":
    app = RapStarApp()
    app.mainloop()
