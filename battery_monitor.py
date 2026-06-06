"""
Smart Battery Monitor
- Monitors laptop battery and controls Tuya smart plugs automatically.
- Runs in the system tray (minimizes to tray icon on close).
- Polls every 30 seconds.
"""

import sys
import os
import threading
import time
import json
import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import tinytuya
from PIL import Image, ImageDraw, ImageFont
import pystray

# ── Config file path ──────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".battery_monitor_config.json")

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "api_key":    "YOUR_CLIENT_ID",
    "api_secret": "YOUR_CLIENT_SECRET",
    "api_region": "eu",
    "devices": [
        {"id": "YOUR_DEVICE_ID_1", "name": "Plug 1"},
        {"id": "YOUR_DEVICE_ID_2",   "name": "Plug 2"},
    ],
    "active_device_index": 0,
    "min_level": 20,
    "max_level": 80,
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get_cloud(cfg):
    return tinytuya.Cloud(
        apiRegion=cfg["api_region"],
        apiKey=cfg["api_key"],
        apiSecret=cfg["api_secret"],
    )


def send_command(cfg, value: bool):
    """Send on/off to the active device using the direct API endpoint."""
    cloud  = get_cloud(cfg)
    dev_id = cfg["devices"][cfg["active_device_index"]]["id"]
    for code in ("switch_1", "switch"):
        r = cloud.cloudrequest(
            f"/v1.0/iot-03/devices/{dev_id}/commands",
            post={"commands": [{"code": code, "value": value}]}
        )
        if r.get("success"):
            return True
    return False


def get_plug_state(cfg):
    """Return True if plug is on, False if off, None on error."""
    try:
        cloud  = get_cloud(cfg)
        dev_id = cfg["devices"][cfg["active_device_index"]]["id"]
        r      = cloud.getstatus(dev_id)
        for item in r.get("result", []):
            if item["code"] in ("switch_1", "switch"):
                return item["value"]
    except Exception:
        pass
    return None


# ── Tray icon image generator ─────────────────────────────────────────────────
def make_tray_icon(pct: int, charging: bool) -> Image.Image:
    """Create a small icon showing battery percentage."""
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    color = (34, 197, 94) if charging else (245, 158, 11) if pct > 20 else (239, 68, 68)
    draw.ellipse([2, 2, size - 2, size - 2], fill=color)

    # Percentage text
    text = str(pct)
    font_size = 22 if len(text) < 3 else 18
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw   = bbox[2] - bbox[0]
    th   = bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - 2), text, fill="white", font=font)

    return img


# ── Autostart helpers ─────────────────────────────────────────────────────────
def get_script_path():
    return os.path.abspath(sys.argv[0])


def get_autostart_path():
    startup = os.path.join(
        os.environ.get("APPDATA", ""),
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
        "SmartBatteryMonitor.bat"
    )
    return startup


def is_autostart_enabled():
    return os.path.exists(get_autostart_path())


def enable_autostart():
    script = get_script_path()
    bat_path = get_autostart_path()
    bat_content = f'@echo off\npythonw "{script}"\n'
    try:
        os.makedirs(os.path.dirname(bat_path), exist_ok=True)
        with open(bat_path, "w") as f:
            f.write(bat_content)
        return True
    except Exception as e:
        messagebox.showerror("Fel", f"Kunde inte aktivera autostart:\n{e}")
        return False


def disable_autostart():
    bat_path = get_autostart_path()
    try:
        if os.path.exists(bat_path):
            os.remove(bat_path)
        return True
    except Exception as e:
        messagebox.showerror("Fel", f"Kunde inte inaktivera autostart:\n{e}")
        return False


# ── Main application ──────────────────────────────────────────────────────────
class BatteryMonitorApp:
    POLL_INTERVAL = 30  # seconds

    def __init__(self):
        self.cfg         = load_config()
        self.running     = True
        self.plug_is_on  = None
        self.last_action = ""
        self._last_pct   = 0
        self._window_visible = True

        self._build_ui()
        self._build_tray()
        self._start_monitor()

    # ── Tray ──────────────────────────────────────────────────────────────────
    def _build_tray(self):
        icon_img = make_tray_icon(0, False)

        menu = pystray.Menu(
            pystray.MenuItem("Visa fönster",    self._show_window, default=True),
            pystray.MenuItem("Uppdatera nu",    lambda: threading.Thread(target=self._poll, daemon=True).start()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Uttag PÅ",        lambda: threading.Thread(target=lambda: send_command(self.cfg, True),  daemon=True).start()),
            pystray.MenuItem("Uttag AV",        lambda: threading.Thread(target=lambda: send_command(self.cfg, False), daemon=True).start()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Avsluta",         self._quit_app),
        )

        self.tray = pystray.Icon("BatteryMonitor", icon_img, "Battery Monitor", menu)
        tray_thread = threading.Thread(target=self.tray.run, daemon=True)
        tray_thread.start()

    def _update_tray_icon(self, pct, charging):
        try:
            self.tray.icon    = make_tray_icon(pct, charging)
            plug_str          = "🟢 På" if self.plug_is_on else "🔴 Av" if self.plug_is_on is False else "?"
            self.tray.title   = f"Batteri: {pct}% {'⚡' if charging else '🔋'} | Uttag: {plug_str}"
        except Exception:
            pass

    def _show_window(self):
        self.root.after(0, self._do_show_window)

    def _do_show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._window_visible = True

    def _hide_window(self):
        self.root.withdraw()
        self._window_visible = False

    def _quit_app(self):
        self.running = False
        try:
            self.tray.stop()
        except Exception:
            pass
        self.root.after(0, self.root.destroy)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title("Smart Battery Monitor")
        self.root.resizable(False, False)
        # Hide to tray on close instead of quitting
        self.root.protocol("WM_DELETE_WINDOW", self._hide_window)

        BG   = "#1e1e2e"
        CARD = "#2a2a3e"
        ACC  = "#7c3aed"
        FG   = "#e2e8f0"
        DIM  = "#94a3b8"
        GRN  = "#22c55e"
        RED  = "#ef4444"
        YEL  = "#f59e0b"

        self.root.configure(bg=BG)
        self._colors = {"green": GRN, "red": RED, "yellow": YEL, "dim": DIM}

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Card.TFrame",   background=CARD)
        style.configure("BG.TFrame",     background=BG)
        style.configure("TLabel",        background=BG,   foreground=FG,  font=("Segoe UI", 10))
        style.configure("Card.TLabel",   background=CARD, foreground=FG,  font=("Segoe UI", 10))
        style.configure("Title.TLabel",  background=BG,   foreground=FG,  font=("Segoe UI", 14, "bold"))
        style.configure("Big.TLabel",    background=CARD, foreground=FG,  font=("Segoe UI", 28, "bold"))
        style.configure("Dim.TLabel",    background=CARD, foreground=DIM, font=("Segoe UI", 9))
        style.configure("BgDim.TLabel",  background=BG,   foreground=DIM, font=("Segoe UI", 9))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.map("Accent.TButton",
                  background=[("active", "#6d28d9"), ("!active", ACC)],
                  foreground=[("active", "white"),   ("!active", "white")])

        outer = ttk.Frame(self.root, style="BG.TFrame", padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="⚡ Smart Battery Monitor", style="Title.TLabel").pack(anchor="w", pady=(0, 12))

        # ── Battery card ──────────────────────────────────────────────────────
        bcard = ttk.Frame(outer, style="Card.TFrame", padding=14)
        bcard.pack(fill="x", pady=(0, 10))

        top = ttk.Frame(bcard, style="Card.TFrame")
        top.pack(fill="x")

        self.pct_label      = ttk.Label(top, text="–%",  style="Big.TLabel")
        self.pct_label.pack(side="left")

        info = ttk.Frame(top, style="Card.TFrame")
        info.pack(side="left", padx=(16, 0))
        self.charging_label = ttk.Label(info, text="",   style="Card.TLabel", foreground=GRN)
        self.charging_label.pack(anchor="w")
        self.time_label     = ttk.Label(info, text="",   style="Dim.TLabel")
        self.time_label.pack(anchor="w")
        self.action_label   = ttk.Label(info, text="",   style="Dim.TLabel")
        self.action_label.pack(anchor="w")

        self.bar_canvas = tk.Canvas(bcard, height=10, bg=CARD, highlightthickness=0)
        self.bar_canvas.pack(fill="x", pady=(10, 0))
        self.bar_bg  = self.bar_canvas.create_rectangle(0, 0, 0, 10, fill="#374151", outline="")
        self.bar_fg  = self.bar_canvas.create_rectangle(0, 0, 0, 10, fill=GRN,      outline="")
        self.bar_min = self.bar_canvas.create_line(0, 0, 0, 10, fill=YEL, width=2)
        self.bar_max = self.bar_canvas.create_line(0, 0, 0, 10, fill=RED, width=2)
        self.bar_canvas.bind("<Configure>", self._redraw_bar)

        # ── Plug card ─────────────────────────────────────────────────────────
        pcard = ttk.Frame(outer, style="Card.TFrame", padding=14)
        pcard.pack(fill="x", pady=(0, 10))

        ttk.Label(pcard, text="Aktivt uttag", style="Dim.TLabel", background=CARD).pack(anchor="w")

        self.device_var   = tk.StringVar()
        names             = [d["name"] for d in self.cfg["devices"]]
        self.device_combo = ttk.Combobox(pcard, textvariable=self.device_var,
                                         values=names, state="readonly", width=22)
        self.device_combo.current(self.cfg["active_device_index"])
        self.device_combo.pack(anchor="w", pady=(4, 8))
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_change)

        plug_row = ttk.Frame(pcard, style="Card.TFrame")
        plug_row.pack(fill="x")

        self.plug_status_label = ttk.Label(plug_row, text="Uttag: okänt",
                                           style="Card.TLabel", foreground=DIM)
        self.plug_status_label.pack(side="left")

        btn_frame = ttk.Frame(plug_row, style="Card.TFrame")
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="På",  style="Accent.TButton",
                   command=lambda: self._manual_plug(True)).pack(side="left", padx=(0, 4))
        ttk.Button(btn_frame, text="Av",  style="Accent.TButton",
                   command=lambda: self._manual_plug(False)).pack(side="left")

        # ── Settings card ─────────────────────────────────────────────────────
        scard = ttk.Frame(outer, style="Card.TFrame", padding=14)
        scard.pack(fill="x", pady=(0, 10))

        ttk.Label(scard, text="Laddningsgränser", style="Dim.TLabel", background=CARD).pack(anchor="w", pady=(0, 6))

        self.min_var = tk.DoubleVar(value=self.cfg["min_level"])
        self.max_var = tk.DoubleVar(value=self.cfg["max_level"])
        self.min_lbl = self._make_slider(scard, "Min (ladda på):", self.min_var, 5,  50, self._on_min_change)
        self.max_lbl = self._make_slider(scard, "Max (ladda av):", self.max_var, 50, 100, self._on_max_change)

        # ── Autostart row ─────────────────────────────────────────────────────
        acard = ttk.Frame(outer, style="Card.TFrame", padding=14)
        acard.pack(fill="x", pady=(0, 10))

        arow = ttk.Frame(acard, style="Card.TFrame")
        arow.pack(fill="x")

        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        ttk.Label(arow, text="Starta med Windows", style="Card.TLabel").pack(side="left")
        ttk.Checkbutton(arow, variable=self.autostart_var,
                        command=self._toggle_autostart,
                        style="TCheckbutton").pack(side="right")

        # ── Bottom row ────────────────────────────────────────────────────────
        bot = ttk.Frame(outer, style="BG.TFrame")
        bot.pack(fill="x", pady=(4, 0))

        self.status_label = ttk.Label(bot, text="Startar...", style="BgDim.TLabel")
        self.status_label.pack(side="left")

        ttk.Button(bot, text="Uppdatera nu", style="Accent.TButton",
                   command=self._force_poll).pack(side="right")

    def _make_slider(self, parent, label, var, from_, to, command):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, style="Card.TLabel", width=14).pack(side="left")
        ttk.Scale(row, from_=from_, to=to, orient="horizontal",
                  variable=var, command=command, length=160).pack(side="left", padx=(4, 8))
        lbl = ttk.Label(row, text=f"{int(var.get())}%", style="Card.TLabel", width=5)
        lbl.pack(side="left")
        return lbl

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _on_min_change(self, val):
        v = max(5, min(int(float(val)), int(self.max_var.get()) - 5))
        self.min_var.set(v)
        self.min_lbl.config(text=f"{v}%")
        self.cfg["min_level"] = v
        save_config(self.cfg)
        self._redraw_bar()

    def _on_max_change(self, val):
        v = max(int(self.min_var.get()) + 5, min(int(float(val)), 100))
        self.max_var.set(v)
        self.max_lbl.config(text=f"{v}%")
        self.cfg["max_level"] = v
        save_config(self.cfg)
        self._redraw_bar()

    def _on_device_change(self, _=None):
        self.cfg["active_device_index"] = self.device_combo.current()
        save_config(self.cfg)
        self.plug_status_label.config(text="Uttag: kontrollerar...")
        threading.Thread(target=self._update_plug_status, daemon=True).start()

    def _manual_plug(self, state: bool):
        self.plug_status_label.config(text="Uttag: skickar...")
        def do():
            ok = send_command(self.cfg, state)
            if ok:
                self.plug_is_on = state
            self.root.after(0, self._update_plug_label)
        threading.Thread(target=do, daemon=True).start()

    def _toggle_autostart(self):
        if self.autostart_var.get():
            ok = enable_autostart()
            if not ok:
                self.autostart_var.set(False)
        else:
            disable_autostart()

    def _force_poll(self):
        threading.Thread(target=self._poll, daemon=True).start()

    # ── Battery bar ───────────────────────────────────────────────────────────
    def _redraw_bar(self, _=None):
        self.bar_canvas.update_idletasks()
        w = self.bar_canvas.winfo_width()
        if w < 2:
            return
        pct = self._last_pct
        mn  = int(self.min_var.get())
        mx  = int(self.max_var.get())
        c   = self._colors

        color = c["red"] if pct <= mn else c["green"] if pct < mx else c["yellow"]
        self.bar_canvas.coords(self.bar_bg,  0, 0, w, 10)
        self.bar_canvas.coords(self.bar_fg,  0, 0, max(0, int(w * pct / 100)), 10)
        self.bar_canvas.itemconfig(self.bar_fg, fill=color)
        self.bar_canvas.coords(self.bar_min, int(w * mn / 100), 0, int(w * mn / 100), 10)
        self.bar_canvas.coords(self.bar_max, int(w * mx / 100), 0, int(w * mx / 100), 10)

    # ── Plug label ────────────────────────────────────────────────────────────
    def _update_plug_label(self):
        c = self._colors
        if self.plug_is_on is True:
            self.plug_status_label.config(text="Uttag: På 🟢",  foreground=c["green"])
        elif self.plug_is_on is False:
            self.plug_status_label.config(text="Uttag: Av 🔴",  foreground=c["red"])
        else:
            self.plug_status_label.config(text="Uttag: okänt",  foreground=c["dim"])

    def _update_plug_status(self):
        self.plug_is_on = get_plug_state(self.cfg)
        self.root.after(0, self._update_plug_label)

    # ── Monitor loop ──────────────────────────────────────────────────────────
    def _start_monitor(self):
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        while self.running:
            self._poll()
            for _ in range(self.POLL_INTERVAL * 10):
                if not self.running:
                    break
                time.sleep(0.1)

    def _poll(self):
        try:
            bat      = psutil.sensors_battery()
            pct      = int(bat.percent)
            charging = bat.power_plugged
            secs     = bat.secsleft

            mn = self.cfg["min_level"]
            mx = self.cfg["max_level"]

            action = ""
            if not charging and pct <= mn:
                ok     = send_command(self.cfg, True)
                action = f"Slog PÅ uttaget ({pct}% ≤ {mn}%)" if ok else "Fel: kunde inte slå på"
                if ok:
                    self.plug_is_on = True
            elif charging and pct >= mx:
                ok     = send_command(self.cfg, False)
                action = f"Slog AV uttaget ({pct}% ≥ {mx}%)" if ok else "Fel: kunde inte slå av"
                if ok:
                    self.plug_is_on = False
            else:
                self.plug_is_on = get_plug_state(self.cfg)

            if action:
                self.last_action = action

            if secs in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN) or secs < 0:
                time_str = "Laddar" if charging else "Okänd tid"
            else:
                h, m = divmod(secs // 60, 60)
                time_str = f"{h}t {m}m kvar" if h else f"{m}m kvar"

            self._last_pct = pct

            def update_ui():
                self.pct_label.config(text=f"{pct}%")
                self.charging_label.config(
                    text="🔌 Laddar" if charging else "🔋 Laddar ur",
                    foreground=self._colors["green"] if charging else self._colors["yellow"]
                )
                self.time_label.config(text=time_str)
                self.action_label.config(text=self.last_action)
                self.status_label.config(text=f"Senast uppdaterad: {time.strftime('%H:%M:%S')}")
                self._redraw_bar()
                self._update_plug_label()

            self.root.after(0, update_ui)
            self._update_tray_icon(pct, charging)

        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Fel: {e}"))

    # ── Run ───────────────────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = BatteryMonitorApp()
    app.run()
