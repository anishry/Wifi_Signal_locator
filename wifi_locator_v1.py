#!/usr/bin/env python3
"""
WiFi Signal Anlyzer & Locator Tool
==================================
Scans nearby WiFi access points using your laptop's wireless adapter,
then submits BSSID + signal data to Mozilla Location Services (MLS)
to triangulate your physical location — the same technique browsers
use for the HTML5 Geolocation API.

NO GPS required. NO API key required. Works offline-capable scan.

Created  by: ANISH R
Date: 2024-06-30
Version: 1.0
For any queries or suggestions, contact: anishry88@gmail.com ph: +91-9895 086 743
Developer: Anish R
Email:anishry88@gmail.com
Developer's Phone: +91-9895 086 743
Tool For CERT-K
-----------
Disclaimer:
-----------
This tool is intended for educational and ethical use only. The author is not responsible for any misuse
or damage caused by this software. Always obtain proper authorization before testing any website.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import platform
import re
import json
import urllib.request
import urllib.error
import time
import webbrowser
import math
from datetime import datetime

# ── Colour tokens ────────────────────────────────────────
BG        = "#080D14"
BG_PANEL  = "#0E1520"
BG_CARD   = "#111B2B"
BG_ROW    = "#0A1220"
BG_ROWALT = "#0D1828"
BG_HOVER  = "#162236"
BORDER    = "#1A2E48"
ACCENT    = "#00D4FF"    # cyan — signal / radar aesthetic
ACCENT2   = "#7C3AED"   # violet — secondary
SUCCESS   = "#00E676"
WARNING   = "#FFB300"
DANGER    = "#FF3D3D"
TEXT_PRI  = "#E0EAF4"
TEXT_SEC  = "#4A6785"
TEXT_MUT  = "#1E3352"
MONO      = ("Consolas", 10)

OS = platform.system()  # "Windows" | "Linux" | "Darwin"


# ════════════════════════════════════════════════════════
#  WiFi SCANNER  (cross-platform)
# ════════════════════════════════════════════════════════
class WiFiNetwork:
    __slots__ = ("ssid", "bssid", "signal_dbm", "channel", "security")

    def __init__(self, ssid="", bssid="", signal_dbm=-100,
                 channel=0, security=""):
        self.ssid = ssid
        self.bssid = bssid.upper()
        self.signal_dbm = signal_dbm
        self.channel = channel
        self.security = security

    @property
    def signal_pct(self):
        """Convert dBm (-30 excellent … -90 poor) to 0-100 %."""
        pct = 2 * (self.signal_dbm + 100)
        return max(0, min(100, pct))

    @property
    def bar_count(self):
        pct = self.signal_pct
        if pct >= 75: return 4
        if pct >= 50: return 3
        if pct >= 25: return 2
        return 1

    def __repr__(self):
        return f"<WiFi {self.bssid} '{self.ssid}' {self.signal_dbm}dBm>"


def _normalize_bssid(raw: str) -> str:
    raw = raw.strip().upper()
    # Sometimes colons are missing; try to reformat
    if len(raw) == 12 and ':' not in raw:
        raw = ':'.join(raw[i:i+2] for i in range(0, 12, 2))
    return raw


def scan_windows() -> list[WiFiNetwork]:
    out = subprocess.check_output(
        ["netsh", "wlan", "show", "networks", "mode=bssid"],
        encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    nets = []
    current = {}
    for line in out.splitlines():
        line = line.strip()
        m = re.match(r'SSID\s+\d+\s*:\s*(.*)', line)
        if m and 'BSSID' not in line:
            if current.get('bssid'):
                nets.append(_win_to_net(current))
            current = {'ssid': m.group(1).strip()}
            continue
        m = re.match(r'BSSID\s+\d+\s*:\s*([0-9a-fA-F:]+)', line)
        if m:
            current['bssid'] = _normalize_bssid(m.group(1))
            continue
        m = re.match(r'Signal\s*:\s*(\d+)%', line)
        if m:
            pct = int(m.group(1))
            current['signal_dbm'] = (pct // 2) - 100
            continue
        m = re.match(r'Channel\s*:\s*(\d+)', line)
        if m:
            current['channel'] = int(m.group(1))
            continue
        m = re.match(r'Authentication\s*:\s*(.*)', line)
        if m:
            current['security'] = m.group(1).strip()
    if current.get('bssid'):
        nets.append(_win_to_net(current))
    return nets


def _win_to_net(d: dict) -> WiFiNetwork:
    return WiFiNetwork(
        ssid=d.get('ssid', ''),
        bssid=d.get('bssid', ''),
        signal_dbm=d.get('signal_dbm', -90),
        channel=d.get('channel', 0),
        security=d.get('security', ''),
    )


def scan_linux_nmcli() -> list[WiFiNetwork]:
    out = subprocess.check_output(
        ["nmcli", "-t", "-f", "IN-USE,BSSID,SSID,CHAN,SIGNAL,SECURITY",
         "dev", "wifi"],
        encoding="utf-8", errors="replace"
    )
    nets = []
    for line in out.splitlines():
        parts = line.split(':')
        if len(parts) < 6:
            continue
        try:
            bssid = _normalize_bssid(parts[1].replace('\\:', ':'))
            ssid = parts[2]
            channel = int(parts[3]) if parts[3].isdigit() else 0
            pct = int(parts[4]) if parts[4].isdigit() else 0
            security = parts[5]
            dbm = (pct // 2) - 100
            nets.append(WiFiNetwork(ssid=ssid, bssid=bssid,
                                    signal_dbm=dbm, channel=channel,
                                    security=security))
        except (ValueError, IndexError):
            continue
    return nets


def scan_linux_iwlist() -> list[WiFiNetwork]:
    out = subprocess.check_output(
        ["iwlist", "scan"],
        encoding="utf-8", errors="replace",
        stderr=subprocess.DEVNULL
    )
    nets = []
    current = {}
    for line in out.splitlines():
        line = line.strip()
        m = re.search(r'Address:\s*([0-9A-Fa-f:]{17})', line)
        if m:
            if current.get('bssid'):
                nets.append(WiFiNetwork(**current))
            current = {'bssid': _normalize_bssid(m.group(1)),
                       'ssid': '', 'signal_dbm': -90, 'channel': 0, 'security': ''}
            continue
        m = re.search(r'ESSID:"([^"]*)"', line)
        if m:
            current['ssid'] = m.group(1)
            continue
        m = re.search(r'Signal level=(-?\d+)\s*dBm', line)
        if m:
            current['signal_dbm'] = int(m.group(1))
            continue
        m = re.search(r'Channel:(\d+)', line)
        if m:
            current['channel'] = int(m.group(1))
            continue
        if 'Encryption key:on' in line:
            current['security'] = 'WPA'
    if current.get('bssid'):
        nets.append(WiFiNetwork(**current))
    return nets


def scan_macos() -> list[WiFiNetwork]:
    airport = ("/System/Library/PrivateFrameworks/Apple80211.framework"
               "/Versions/Current/Resources/airport")
    out = subprocess.check_output(
        [airport, "-s"],
        encoding="utf-8", errors="replace"
    )
    nets = []
    for line in out.splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            bssid = _normalize_bssid(parts[-5])
            signal = int(parts[-4])
            channel = int(str(parts[-3]).split(',')[0])
            ssid = ' '.join(parts[:-5])
            nets.append(WiFiNetwork(ssid=ssid, bssid=bssid,
                                    signal_dbm=signal, channel=channel))
        except (ValueError, IndexError):
            continue
    return nets


def scan_wifi() -> tuple[list[WiFiNetwork], str]:
    """
    Returns (list_of_networks, method_used_string).
    Raises RuntimeError if no scanner is available.
    """
    if OS == "Windows":
        return scan_windows(), "netsh wlan"
    if OS == "Darwin":
        return scan_macos(), "airport -s"
    # Linux: try nmcli first, then iwlist
    for fn, label in [(scan_linux_nmcli, "nmcli"), (scan_linux_iwlist, "iwlist")]:
        try:
            nets = fn()
            if nets:
                return nets, label
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    raise RuntimeError(
        "No WiFi scanner available.\n"
        "Install network-manager (nmcli) or wireless-tools (iwlist)."
    )


# ════════════════════════════════════════════════════════
#  GEOLOCATION  (Mozilla Location Services)
# ════════════════════════════════════════════════════════
MLS_URL = "https://location.services.mozilla.com/v1/geolocate?key=test"


def geolocate_wifi(networks: list[WiFiNetwork]) -> dict:
    """
    Submit WiFi access-point data to Mozilla Location Services.
    Returns dict with keys: lat, lng, accuracy (metres).
    """
    payload = {
        "wifiAccessPoints": [
            {
                "macAddress": n.bssid,
                "signalStrength": n.signal_dbm,
                "channel": n.channel,
            }
            for n in networks if n.bssid
        ]
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        MLS_URL,
        data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "WiFiLocatorTool/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    return {
        "lat": data["location"]["lat"],
        "lng": data["location"]["lng"],
        "accuracy": data.get("accuracy", 0),
    }


def geolocate_ip_fallback() -> dict:
    """IP-based fallback when WiFi geolocation fails."""
    url = "http://ip-api.com/json/?fields=lat,lon,city,country,query"
    with urllib.request.urlopen(url, timeout=8) as resp:
        d = json.loads(resp.read().decode())
    return {
        "lat": d["lat"], "lng": d["lon"],
        "accuracy": 5000,
        "note": f"IP fallback — {d.get('city')}, {d.get('country')} ({d.get('query')})",
    }


# ════════════════════════════════════════════════════════
#  GUI  COMPONENTS
# ════════════════════════════════════════════════════════
class RadarCanvas(tk.Canvas):
    """Animated radar sweep that plays while scanning."""

    def __init__(self, parent, size=140, **kw):
        super().__init__(parent, width=size, height=size,
                         bg=BG_CARD, highlightthickness=0, **kw)
        self.s = size
        self.cx = self.cy = size // 2
        self.r = size // 2 - 8
        self._angle = 0
        self._running = False
        self._dots: list[tuple] = []
        self._draw_static()

    def _draw_static(self):
        cx, cy, r = self.cx, self.cy, self.r
        self.delete("static")
        # Rings
        for i in range(1, 5):
            rr = r * i // 4
            self.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                             outline=BORDER, width=1, tags="static")
        # Cross-hairs
        self.create_line(cx - r, cy, cx + r, cy, fill=BORDER, tags="static")
        self.create_line(cx, cy - r, cx, cy + r, fill=BORDER, tags="static")
        # Centre dot
        self.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                         fill=ACCENT, outline="", tags="static")

    def _draw_sweep(self):
        self.delete("sweep")
        cx, cy, r = self.cx, self.cy, self.r
        ang_rad = math.radians(self._angle)
        # Sweep wedge (trailing gradient via overlapping arcs)
        for i in range(20):
            a = self._angle - i * 4
            alpha_hex = format(max(0, 80 - i * 5), '02x')
            try:
                self.create_arc(
                    cx - r, cy - r, cx + r, cy + r,
                    start=a, extent=4,
                    fill=f"#{alpha_hex}d4ff",   # fading cyan
                    outline="", style="pie", tags="sweep"
                )
            except tk.TclError:
                pass
        # Leading edge line
        ex = cx + r * math.cos(ang_rad)
        ey = cy - r * math.sin(ang_rad)
        self.create_line(cx, cy, ex, ey, fill=ACCENT, width=2, tags="sweep")

    def _draw_dots(self):
        self.delete("dot")
        for x, y, age in self._dots:
            alpha = max(0, 1 - age / 60)
            size = 4
            self.create_oval(x - size, y - size, x + size, y + size,
                             fill=SUCCESS, outline="", tags="dot")

    def _tick(self):
        if not self._running:
            return
        self._angle = (self._angle + 3) % 360
        ang_rad = math.radians(self._angle)
        # Randomly sprout blips on the sweep edge
        if self._angle % 20 == 0:
            r = self.r * (0.3 + 0.6 * (len(self._dots) % 7) / 7)
            x = self.cx + r * math.cos(ang_rad)
            y = self.cy - r * math.sin(ang_rad)
            self._dots.append((x, y, 0))
        self._dots = [(x, y, age + 1) for x, y, age in self._dots if age < 60]
        self._draw_static()
        self._draw_sweep()
        self._draw_dots()
        self.after(30, self._tick)

    def start(self):
        self._running = True
        self._dots = []
        self._tick()

    def stop(self):
        self._running = False
        self.delete("sweep")
        self._draw_static()


class SignalBar(tk.Canvas):
    """Four-segment vertical signal bar indicator."""

    def __init__(self, parent, count=0, **kw):
        super().__init__(parent, width=22, height=16,
                         bg=BG_ROW, highlightthickness=0, **kw)
        self.draw(count)

    def draw(self, count):
        self.delete("all")
        colors = {0: TEXT_MUT, 1: DANGER, 2: WARNING, 3: WARNING, 4: SUCCESS}
        color = colors.get(count, TEXT_MUT)
        for i in range(4):
            h = 4 + i * 3
            x1 = 2 + i * 5
            y1 = 16 - h
            fill = color if i < count else TEXT_MUT
            self.create_rectangle(x1, y1, x1 + 3, 15, fill=fill, outline="")


# ════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ════════════════════════════════════════════════════════
class WiFiLocatorApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("WiFi Signal Locator")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(780, 620)

        w, h = 860, 720
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._networks: list[WiFiNetwork] = []
        self._location: dict | None = None
        self._scan_method = ""
        self._history: list[dict] = []

        self._build_ui()

    # ── BUILD ───────────────────────────────────────────
    def _build_ui(self):
        # Title bar
        title_bar = tk.Frame(self, bg=BG, pady=14)
        title_bar.pack(fill="x", padx=24)

        tk.Label(title_bar, text="◈", bg=BG, fg=ACCENT,
                 font=("Consolas", 20, "bold")).pack(side="left")
        tk.Label(title_bar, text="  WiFi Signal Locator",
                 bg=BG, fg=TEXT_PRI,
                 font=("Segoe UI", 16, "bold")).pack(side="left")

        self._status_var = tk.StringVar(value="Ready — click Scan to begin")
        tk.Label(title_bar, textvariable=self._status_var,
                 bg=BG, fg=TEXT_SEC,
                 font=("Segoe UI", 9)).pack(side="right", padx=4)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Main split layout
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=16, pady=12)

        # ── Left panel (radar + controls + location) ─────
        left = tk.Frame(main, bg=BG, width=240)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        self._build_left(left)

        # ── Right panel (network table) ───────────────────
        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_right(right)

    def _build_left(self, parent):
        # Radar card
        radar_card = tk.Frame(parent, bg=BG_CARD, padx=12, pady=14)
        radar_card.pack(fill="x")

        self._radar = RadarCanvas(radar_card, size=140)
        self._radar.pack()

        tk.Label(radar_card, text="SIGNAL SCAN", bg=BG_CARD, fg=TEXT_SEC,
                 font=("Consolas", 8, "bold")).pack(pady=(6, 2))

        self._net_count_var = tk.StringVar(value="0 networks")
        tk.Label(radar_card, textvariable=self._net_count_var,
                 bg=BG_CARD, fg=ACCENT,
                 font=("Consolas", 11, "bold")).pack()

        # Buttons
        btn_frame = tk.Frame(parent, bg=BG, pady=8)
        btn_frame.pack(fill="x")

        self._scan_btn = tk.Button(
            btn_frame, text="⟳  Scan WiFi Networks",
            bg=ACCENT, fg=BG,
            activebackground="#00AACF", activeforeground=BG,
            relief="flat", font=("Segoe UI", 10, "bold"),
            cursor="hand2", pady=9,
            command=self._start_scan
        )
        self._scan_btn.pack(fill="x", pady=(0, 6))

        self._locate_btn = tk.Button(
            btn_frame, text="⊕  Locate Me",
            bg=BG_CARD, fg=ACCENT2,
            activebackground=BG_HOVER, activeforeground=ACCENT2,
            relief="flat", font=("Segoe UI", 10, "bold"),
            cursor="hand2", pady=9,
            state="disabled",
            command=self._start_locate
        )
        self._locate_btn.pack(fill="x")

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=8)

        # Location result card
        loc_card = tk.Frame(parent, bg=BG_CARD, padx=14, pady=14)
        loc_card.pack(fill="x")

        tk.Label(loc_card, text="LOCATION RESULT", bg=BG_CARD, fg=TEXT_SEC,
                 font=("Consolas", 8, "bold")).pack(anchor="w")
        tk.Frame(loc_card, bg=BORDER, height=1).pack(fill="x", pady=(4, 8))

        self._lat_var = tk.StringVar(value="—")
        self._lng_var = tk.StringVar(value="—")
        self._acc_var = tk.StringVar(value="—")
        self._ts_var  = tk.StringVar(value="—")

        for label, var in [
            ("Latitude",  self._lat_var),
            ("Longitude", self._lng_var),
            ("Accuracy",  self._acc_var),
            ("Timestamp", self._ts_var),
        ]:
            row = tk.Frame(loc_card, bg=BG_CARD)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, bg=BG_CARD, fg=TEXT_SEC,
                     font=("Segoe UI", 8), width=9, anchor="w").pack(side="left")
            tk.Label(row, textvariable=var, bg=BG_CARD, fg=TEXT_PRI,
                     font=("Consolas", 10), anchor="w").pack(side="left")

        tk.Frame(loc_card, bg=BORDER, height=1).pack(fill="x", pady=8)

        self._note_var = tk.StringVar(value="")
        tk.Label(loc_card, textvariable=self._note_var, bg=BG_CARD,
                 fg=WARNING, font=("Segoe UI", 8),
                 wraplength=200, justify="left").pack(anchor="w")

        self._map_btn = tk.Button(
            loc_card, text="🗺  Open in Google Maps",
            bg=BG, fg=ACCENT2,
            activebackground=BG_HOVER, activeforeground=ACCENT2,
            relief="flat", font=("Segoe UI", 9),
            cursor="hand2", pady=6,
            state="disabled",
            command=self._open_map
        )
        self._map_btn.pack(fill="x", pady=(6, 0))

        self._copy_btn = tk.Button(
            loc_card, text="⎘  Copy coordinates",
            bg=BG, fg=TEXT_SEC,
            activebackground=BG_HOVER, activeforeground=TEXT_PRI,
            relief="flat", font=("Segoe UI", 9),
            cursor="hand2", pady=6,
            state="disabled",
            command=self._copy_coords
        )
        self._copy_btn.pack(fill="x", pady=(4, 0))

        # Platform note
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(12, 4))
        note = {
            "Windows": "Uses: netsh wlan",
            "Linux":   "Uses: nmcli or iwlist",
            "Darwin":  "Uses: airport -s",
        }.get(OS, OS)
        tk.Label(parent, text=f"Platform: {OS}  ·  {note}",
                 bg=BG, fg=TEXT_MUT, font=("Segoe UI", 7),
                 wraplength=220, justify="center").pack()

    def _build_right(self, parent):
        # Header row
        hdr = tk.Frame(parent, bg=BG)
        hdr.pack(fill="x", pady=(0, 8))

        tk.Label(hdr, text="Detected WiFi Networks", bg=BG, fg=TEXT_PRI,
                 font=("Segoe UI", 12, "bold")).pack(side="left")

        self._method_var = tk.StringVar(value="")
        tk.Label(hdr, textvariable=self._method_var, bg=BG, fg=TEXT_MUT,
                 font=("Segoe UI", 8)).pack(side="right", padx=4)

        # Search filter
        search_bar = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        search_bar.pack(fill="x", pady=(0, 8))
        search_inner = tk.Frame(search_bar, bg=BG_CARD)
        search_inner.pack(fill="x")

        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        tk.Label(search_inner, text="⌕", bg=BG_CARD, fg=TEXT_SEC,
                 font=("Segoe UI", 12)).pack(side="left", padx=(10, 4))
        tk.Entry(search_inner, textvariable=self._filter_var,
                 bg=BG_CARD, fg=TEXT_PRI, insertbackground=ACCENT,
                 relief="flat", font=("Segoe UI", 10),
                 ).pack(side="left", fill="x", expand=True, pady=8)

        # Table
        tbl_frame = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        tbl_frame.pack(fill="both", expand=True)
        tbl_inner = tk.Frame(tbl_frame, bg=BG_CARD)
        tbl_inner.pack(fill="both", expand=True)

        cols = ("signal_bar", "ssid", "bssid", "signal_dbm", "channel", "security")
        self._tree = ttk.Treeview(
            tbl_inner, columns=cols, show="headings",
            selectmode="extended"
        )
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=BG_ROW, fieldbackground=BG_ROW,
                        foreground=TEXT_PRI, rowheight=30,
                        font=("Consolas", 10))
        style.configure("Treeview.Heading",
                        background=BG_CARD, foreground=TEXT_SEC,
                        relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Treeview",
                  background=[("selected", BG_HOVER)],
                  foreground=[("selected", ACCENT)])

        cols_cfg = [
            ("signal_bar", "Sig",    50,  "center"),
            ("ssid",       "SSID",   200, "w"),
            ("bssid",      "BSSID",  140, "center"),
            ("signal_dbm", "dBm",    60,  "center"),
            ("channel",    "Chan",   55,  "center"),
            ("security",   "Security",110,"center"),
        ]
        for col, heading, width, anchor in cols_cfg:
            self._tree.heading(col, text=heading,
                               command=lambda c=col: self._sort_by(c))
            self._tree.column(col, width=width, anchor=anchor, minwidth=40)

        vsb = tk.Scrollbar(tbl_inner, orient="vertical",
                           command=self._tree.yview, bg=BG_CARD)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)
        self._tree.tag_configure("excellent", foreground=SUCCESS)
        self._tree.tag_configure("good",      foreground=ACCENT)
        self._tree.tag_configure("fair",      foreground=WARNING)
        self._tree.tag_configure("poor",      foreground=DANGER)

        # Stats bar
        stats = tk.Frame(parent, bg=BG_PANEL, pady=6)
        stats.pack(fill="x", pady=(6, 0))

        self._stats_var = tk.StringVar(value="No scan yet")
        tk.Label(stats, textvariable=self._stats_var, bg=BG_PANEL,
                 fg=TEXT_SEC, font=("Segoe UI", 8)).pack(side="left", padx=10)

        self._elapsed_var = tk.StringVar(value="")
        tk.Label(stats, textvariable=self._elapsed_var, bg=BG_PANEL,
                 fg=TEXT_MUT, font=("Segoe UI", 8)).pack(side="right", padx=10)

    # ── SCAN ────────────────────────────────────────────
    def _start_scan(self):
        self._set_busy(True, "Scanning WiFi networks…")
        self._radar.start()
        self._networks = []
        self._tree.delete(*self._tree.get_children())
        self._net_count_var.set("Scanning…")
        self._stats_var.set("Scanning…")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        t0 = time.perf_counter()
        try:
            nets, method = scan_wifi()
            elapsed = time.perf_counter() - t0
            self.after(0, lambda: self._on_scan_done(nets, method, elapsed))
        except Exception as e:
            self.after(0, lambda: self._on_scan_error(str(e)))

    def _on_scan_done(self, nets: list[WiFiNetwork], method: str, elapsed: float):
        self._radar.stop()
        self._networks = sorted(nets, key=lambda n: n.signal_dbm, reverse=True)
        self._scan_method = method
        self._method_var.set(f"via {method}")
        self._populate_table(self._networks)
        self._net_count_var.set(f"{len(nets)} networks")
        self._stats_var.set(
            f"{len(nets)} networks found  ·  strongest: "
            f"{nets[0].signal_dbm} dBm  ({nets[0].ssid or 'hidden'})"
            if nets else "No networks found"
        )
        self._elapsed_var.set(f"scan took {elapsed*1000:.0f} ms")
        self._set_busy(False, f"Scan complete — {len(nets)} networks found")
        if nets:
            self._locate_btn.config(state="normal")

    def _on_scan_error(self, msg: str):
        self._radar.stop()
        self._set_busy(False, f"Scan error: {msg}")
        self._net_count_var.set("Error")
        messagebox.showerror("Scan Failed",
            f"Could not scan WiFi networks:\n\n{msg}\n\n"
            "On Linux: install network-manager (nmcli) or wireless-tools (iwlist).\n"
            "On Linux with iwlist: you may need to run with sudo.")

    def _populate_table(self, nets: list[WiFiNetwork]):
        self._tree.delete(*self._tree.get_children())
        for n in nets:
            bars = "▂▄▆█"[:n.bar_count].ljust(4, "░")
            if n.signal_dbm >= -50:
                tag = "excellent"
            elif n.signal_dbm >= -65:
                tag = "good"
            elif n.signal_dbm >= -75:
                tag = "fair"
            else:
                tag = "poor"
            self._tree.insert("", "end", tags=(tag,), values=(
                bars,
                n.ssid or "<hidden>",
                n.bssid,
                f"{n.signal_dbm} dBm",
                n.channel or "—",
                n.security or "Open",
            ))

    def _apply_filter(self):
        q = self._filter_var.get().lower()
        if not q:
            self._populate_table(self._networks)
            return
        filtered = [
            n for n in self._networks
            if q in n.ssid.lower() or q in n.bssid.lower()
               or q in str(n.channel) or q in (n.security or "").lower()
        ]
        self._populate_table(filtered)
        self._stats_var.set(
            f"Showing {len(filtered)} of {len(self._networks)} networks")

    def _sort_by(self, col):
        items = [
            (self._tree.set(k, col), k)
            for k in self._tree.get_children("")
        ]
        items.sort(key=lambda t: t[0])
        for i, (_, k) in enumerate(items):
            self._tree.move(k, "", i)

    # ── LOCATE ──────────────────────────────────────────
    def _start_locate(self):
        if not self._networks:
            messagebox.showwarning("No data", "Scan WiFi networks first.")
            return
        self._set_busy(True, "Submitting WiFi data to MLS…")
        threading.Thread(target=self._locate_worker, daemon=True).start()

    def _locate_worker(self):
        t0 = time.perf_counter()
        try:
            loc = geolocate_wifi(self._networks)
            elapsed = time.perf_counter() - t0
            self.after(0, lambda: self._on_locate_done(loc, elapsed))
        except Exception as e:
            # Fallback to IP geolocation
            try:
                loc = geolocate_ip_fallback()
                elapsed = time.perf_counter() - t0
                self.after(0, lambda: self._on_locate_done(loc, elapsed, fallback=True))
            except Exception as e2:
                self.after(0, lambda: self._on_locate_error(f"{e} | fallback: {e2}"))

    def _on_locate_done(self, loc: dict, elapsed: float, fallback: bool = False):
        self._location = loc
        ts = datetime.now().strftime("%H:%M:%S")
        self._lat_var.set(f"{loc['lat']:.6f}")
        self._lng_var.set(f"{loc['lng']:.6f}")
        acc = loc.get("accuracy", 0)
        self._acc_var.set(f"± {acc:.0f} m")
        self._ts_var.set(ts)
        note = loc.get("note", "")
        if fallback:
            note = "⚠ WiFi geolocation unavailable — used IP fallback"
        self._note_var.set(note)
        self._map_btn.config(state="normal")
        self._copy_btn.config(state="normal")

        # Save to history
        self._history.append({
            "time": ts, "lat": loc["lat"], "lng": loc["lng"],
            "accuracy_m": acc, "networks": len(self._networks),
            "method": "ip-fallback" if fallback else "wifi-mls",
        })

        method_lbl = "IP fallback" if fallback else "Mozilla Location Services"
        self._set_busy(False,
            f"Located via {method_lbl}  ·  ±{acc:.0f} m  ·  {elapsed*1000:.0f} ms")

    def _on_locate_error(self, msg: str):
        self._set_busy(False, f"Location failed: {msg}")
        messagebox.showerror("Location Failed",
            f"Could not determine location:\n\n{msg}")

    # ── ACTIONS ─────────────────────────────────────────
    def _open_map(self):
        if self._location:
            lat, lng = self._location["lat"], self._location["lng"]
            url = f"https://www.google.com/maps?q={lat},{lng}&z=16"
            webbrowser.open(url)

    def _copy_coords(self):
        if self._location:
            self.clipboard_clear()
            coords = f"{self._location['lat']:.6f}, {self._location['lng']:.6f}"
            self.clipboard_append(coords)
            orig = self._copy_btn.cget("text")
            self._copy_btn.config(text="✓ Copied!", fg=SUCCESS)
            self.after(1800, lambda: self._copy_btn.config(text=orig, fg=TEXT_SEC))

    def _set_busy(self, busy: bool, status: str = ""):
        if status:
            self._status_var.set(status)
        color = WARNING if busy else SUCCESS if "complete" in status.lower() or "located" in status.lower() else TEXT_SEC
        state = "disabled" if busy else "normal"
        self._scan_btn.config(state=state)
        if not busy and self._networks:
            self._locate_btn.config(state="normal")
        elif busy:
            self._locate_btn.config(state="disabled")


# ════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = WiFiLocatorApp()
    app.mainloop()
