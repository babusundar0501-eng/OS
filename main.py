#!/usr/bin/env python3
"""
Windows 12 (Python Edition) — multi-OS
-------------------------------------
A Windows 12-style desktop shell that runs as a normal app.
Fluent / Mica / acrylic look, floating centered taskbar, Start menu,
draggable windows, and a Universal Store with real working apps.
Switch the whole desktop between Windows 12 / macOS / Ubuntu / Android styles
(Settings -> Personalization, or right-click the desktop -> Switch OS).

    pip install PySide6
    python sf.py

Keys:  F11 fullscreen  |  Esc leave fullscreen  |  Win/Meta key = Start
"""
import sys, os, json, ast, operator, platform, getpass, webbrowser
import shutil, subprocess, shlex, io, code, contextlib, zipfile
import math, random, secrets, base64, traceback
from urllib.parse import quote
from pathlib import Path

from PySide6.QtCore import (Qt, QPoint, QPointF, QRect, QRectF, QTimer, QUrl, QEvent,
                            QPropertyAnimation, QEasingCurve, QDateTime, QCoreApplication,
                            QRegularExpression)
from PySide6.QtGui import (QPainter, QPainterPath, QColor, QPen, QPixmap, QImage,
                           QLinearGradient, QRadialGradient, QFont, QCursor, QDesktopServices,
                           QFontMetrics, QIcon, QSyntaxHighlighter, QTextCharFormat,
                           QPolygonF, QPdfWriter, QPageSize)
from PySide6.QtWidgets import (QApplication, QWidget, QFrame, QLabel, QPushButton, QHBoxLayout,
                               QVBoxLayout, QGridLayout, QLineEdit, QTextEdit, QPlainTextEdit,
                               QTextBrowser, QListWidget, QListWidgetItem, QScrollArea, QComboBox,
                               QMenu, QStackedWidget, QFileDialog, QGraphicsDropShadowEffect,
                               QSlider, QSplitter, QColorDialog, QInputDialog)

HAVE_WEB = False
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAVE_WEB = True
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
except Exception:
    pass

HAVE_MEDIA = False
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAVE_MEDIA = True
except Exception:
    pass

# ───────────────────────────── state & theme ─────────────────────────────
DATA_DIR = Path.home() / ".windows12_py"
STATE_FILE = DATA_DIR / "state.json"
TITLE_H = 40
TASK_RES = 76   # space reserved for taskbar when maximizing


class S:  # global settings
    theme = "dark"
    accent = "#4cc2ff"
    wallpaper = 0
    installed = {}   # app name -> store it was installed from
    skin = "win12"   # win12 | macos | ubuntu | android


def load_state():
    try:
        d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        S.theme = d.get("theme", S.theme)
        S.accent = d.get("accent", S.accent)
        S.wallpaper = d.get("wallpaper", S.wallpaper)
        S.installed = d.get("installed", {})
        S.skin = d.get("skin", S.skin)
    except Exception:
        pass


def save_state():
    try:
        DATA_DIR.mkdir(exist_ok=True)
        STATE_FILE.write_text(json.dumps(dict(theme=S.theme, accent=S.accent,
                                              wallpaper=S.wallpaper, installed=S.installed,
                                              skin=S.skin)), encoding="utf-8")
    except Exception:
        pass


THEMES = {
    "dark": dict(text="#f3f5f9", sub="#aab0bd", field="rgba(255,255,255,0.07)", fieldb="rgba(255,255,255,0.12)",
                 card="rgba(255,255,255,0.06)", cardh="rgba(255,255,255,0.11)", menu="#2b2d36",
                 solid=(30, 32, 40), tint=(24, 27, 38, 175), border=(255, 255, 255, 42), hover=(255, 255, 255, 30)),
    "light": dict(text="#14171c", sub="#5a606c", field="rgba(0,0,0,0.05)", fieldb="rgba(0,0,0,0.12)",
                  card="rgba(255,255,255,0.7)", cardh="rgba(255,255,255,0.98)", menu="#fbfbfd",
                  solid=(245, 246, 250), tint=(246, 248, 253, 185), border=(0, 0, 0, 38), hover=(0, 0, 0, 22)),
}


def T():
    return THEMES[S.theme]


def rgba(hexcolor, a):
    c = QColor(hexcolor)
    return f"rgba({c.red()},{c.green()},{c.blue()},{a})"


def build_qss():
    t, a = T(), S.accent
    return f"""
    * {{ font-family:{SKINS[S.skin]['font']},'Segoe UI','Ubuntu','Noto Sans','DejaVu Sans',sans-serif;
         font-size:13px; color:{t['text']}; }}
    QLabel {{ background:transparent; }}
    QLabel[sub="true"] {{ color:{t['sub']}; }}
    QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser, QComboBox, QListWidget {{
        background:{t['field']}; border:1px solid {t['fieldb']}; border-radius:8px; padding:6px 8px;
        selection-background-color:{a}; selection-color:#000; }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border:1px solid {a}; }}
    QListWidget {{ outline:0; }}
    QListWidget::item {{ padding:7px 8px; border-radius:6px; }}
    QListWidget::item:hover {{ background:{t['cardh']}; }}
    QListWidget::item:selected {{ background:{rgba(a, 0.35)}; color:{t['text']}; }}
    QPushButton {{ background:{t['card']}; border:1px solid {t['fieldb']}; border-radius:6px; padding:6px 14px; }}
    QPushButton:hover {{ background:{t['cardh']}; }}
    QPushButton:disabled {{ color:{t['sub']}; }}
    QPushButton[kind="accent"], QPushButton[kind="eq"] {{ background:{a}; color:#000; border:none; font-weight:600; }}
    QPushButton[kind="accent"]:hover, QPushButton[kind="eq"]:hover {{ background:{rgba(a, 0.85)}; }}
    QPushButton[kind="key"] {{ border-radius:8px; min-height:46px; font-size:17px; }}
    QPushButton[kind="flat"] {{ background:transparent; border:none; }}
    QPushButton[kind="flat"]:hover {{ background:{t['cardh']}; }}
    QFrame#card {{ background:{t['card']}; border:1px solid {t['fieldb']}; border-radius:12px; }}
    QFrame#card:hover {{ background:{t['cardh']}; }}
    QComboBox::drop-down {{ border:none; width:22px; }}
    QComboBox QAbstractItemView {{ background:{t['menu']}; border:1px solid {t['fieldb']};
        selection-background-color:{a}; selection-color:#000; padding:4px; }}
    QMenu {{ background:{t['menu']}; border:1px solid {t['fieldb']}; border-radius:10px; padding:6px; }}
    QMenu::item {{ padding:7px 26px 7px 14px; border-radius:6px; }}
    QMenu::item:selected {{ background:{rgba(a, 0.4)}; }}
    QMenu::separator {{ height:1px; background:{t['fieldb']}; margin:5px 8px; }}
    QScrollBar:vertical {{ background:transparent; width:10px; margin:2px; }}
    QScrollBar::handle:vertical {{ background:{t['fieldb']}; border-radius:3px; min-height:30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height:0; width:0; }}
    QScrollBar:horizontal {{ height:0; }}
    QScrollArea {{ background:transparent; border:none; }}
    QScrollArea > QWidget > QWidget {{ background:transparent; }}
    QToolTip {{ background:{t['menu']}; color:{t['text']}; border:1px solid {t['fieldb']}; padding:4px; }}
    QSplitter::handle {{ background:{t['fieldb']}; width:2px; height:2px; }}
    """


# ───────────────────────────── graphics helpers ─────────────────────────────
def make_wallpaper(w, h, idx):
    pm = QPixmap(max(w, 1), max(h, 1))
    p = QPainter(pm)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    pal = [("#050a24", "#17348a", ["#2f6bff", "#6a8dff", "#9d6bff", "#3ad1ff"]),
           ("#14061f", "#8a2d6b", ["#ff7a59", "#ff4f81", "#ffb36b", "#a04bff"]),
           ("#03140f", "#0b6a5a", ["#2fe0b0", "#38a9ff", "#7cf08a", "#1aa68c"]),
           ("#1b1240", "#ff7e5f", ["#7f5af0", "#ff6ec7", "#ffb26b", "#5ce1e6"], "waves"),     # macOS
           ("#2c001e", "#e95420", ["#77216f", "#e95420", "#ff8a50", "#5e2750"], "waves"),     # Ubuntu
           ("#0b132b", "#1c7c9c", ["#3a86ff", "#06d6a0", "#8338ec", "#4cc9f0"], "waves")][idx % 6]  # Android
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0, QColor(pal[0])); g.setColorAt(1, QColor(pal[1]))
    p.fillRect(0, 0, w, h, g)
    p.setPen(Qt.NoPen)
    if len(pal) > 3:
        for i in range(7):
            p.save()
            p.translate(w * 0.5, h * 0.5); p.rotate(-24 + i * 8)
            c1 = QColor(pal[2][i % 4]); c1.setAlpha(150)
            c2 = QColor(c1); c2.setAlpha(0)
            g2 = QLinearGradient(-w, 0, w, 0)
            g2.setColorAt(0, c2); g2.setColorAt(0.5, c1); g2.setColorAt(1, c2)
            p.setBrush(g2)
            p.drawEllipse(QPointF(0, (i - 3) * h * 0.1), w * 0.8, h * 0.15)
            p.restore()
    else:
        r = min(w, h) * 0.58
        p.translate(w * 0.5, h * 0.52)
        for layer, (n, scale, alpha) in enumerate([(8, 1.0, 215), (8, 0.62, 190)]):
            for i in range(n):
                p.save()
                p.rotate(i * 360 / n + (14 if layer == 0 else 31))
                c1 = QColor(pal[2][(i + layer) % 4]); c1.setAlpha(alpha)
                c2 = QColor(c1); c2.setAlpha(0)
                rg = QRadialGradient(0, -r * 0.45 * scale, r * 0.5 * scale)
                rg.setColorAt(0, c1); rg.setColorAt(1, c2)
                p.setBrush(rg)
                p.drawEllipse(QPointF(0, -r * 0.45 * scale), r * 0.27 * scale, r * 0.5 * scale)
                p.restore()
        glow = QRadialGradient(0, 0, r * 0.35)
        glow.setColorAt(0, QColor(255, 255, 255, 120)); glow.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(glow); p.drawEllipse(QPointF(0, 0), r * 0.35, r * 0.35)
    p.end()
    return pm


_tile_cache = {}


def tile(emoji, color, size=40):
    key = (emoji, color, size)
    if key in _tile_cache:
        return _tile_cache[key]
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
    c = QColor(color)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, c.lighter(125)); g.setColorAt(1, c.darker(125))
    p.setBrush(g); p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.26, size * 0.26)
    f = QFont(); f.setPixelSize(int(size * 0.5)); p.setFont(f); p.setPen(QColor("white"))
    p.drawText(QRect(0, 0, size, size), Qt.AlignCenter, emoji)
    p.end()
    _tile_cache[key] = pm
    return pm


def draw_logo(p, r):
    gap = 2
    s = (r.width() - gap) / 2
    p.setPen(Qt.NoPen)
    for i in range(2):
        for j in range(2):
            col = QColor(S.accent)
            col = col.lighter(110 + (i + j) * 8)
            p.setBrush(col)
            p.drawRoundedRect(QRectF(r.x() + i * (s + gap), r.y() + j * (s + gap), s, s), 2.5, 2.5)


def paint_blur(p, widget, rect):
    """Fake acrylic: blurred wallpaper under the widget + theme tint."""
    desk = widget.window()
    blur = getattr(desk, "blur", None)
    if blur is not None and desk.width() > 0:
        tl = widget.mapTo(desk, rect.topLeft())
        sx, sy = blur.width() / desk.width(), blur.height() / desk.height()
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(QRectF(rect), blur, QRectF(tl.x() * sx, tl.y() * sy, rect.width() * sx, rect.height() * sy))
    p.fillRect(rect, QColor(*T()["tint"]))


class Acrylic(QFrame):
    def __init__(self, parent, radius=14):
        super().__init__(parent)
        self.r = radius

    def contextMenuEvent(self, e):
        e.accept()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), self.r, self.r)
        p.setClipPath(path)
        paint_blur(p, self, self.rect())
        p.setClipping(False)
        p.setPen(QPen(QColor(*T()["border"]), 1)); p.setBrush(Qt.NoBrush)
        p.drawPath(path)


# ───────────────────────────── store catalog ─────────────────────────────
SOURCES = {
    "MS": "Microsoft Store", "WG": "winget", "GP": "Google Play", "AZ": "Amazon Appstore",
    "FD": "F-Droid", "GX": "Galaxy Store", "AS": "Apple App Store", "MA": "Mac App Store",
    "HB": "Homebrew", "FH": "Flathub", "SN": "Snap Store", "ST": "Steam", "EG": "Epic Games Store",
    "GG": "GOG", "IT": "itch.io", "CW": "Chrome Web Store",
}


def _c(name, dev, cat, emoji, color, desc, src, rating):
    return dict(name=name, dev=dev, cat=cat, emoji=emoji, color=color, desc=desc,
                sources=[SOURCES[s] for s in src.split()], rating=rating)


CATALOG = [
    _c("Spotify", "Spotify AB", "Music", "🎧", "#1db954", "Music and podcasts for everyone.", "MS GP AS MA FH SN HB", 4.6),
    _c("VLC", "VideoLAN", "Video", "🔶", "#ff8800", "Plays almost any video or audio format.", "MS WG GP MA FH SN HB FD", 4.7),
    _c("Visual Studio Code", "Microsoft", "Developer", "💻", "#2f7fd1", "Lightweight, powerful code editor.", "WG SN FH HB", 4.8),
    _c("Firefox", "Mozilla", "Browsers", "🦊", "#ff7139", "Fast, private, open-source browser.", "MS WG GP AS HB FH SN FD", 4.5),
    _c("Discord", "Discord Inc.", "Social", "💬", "#5865f2", "Voice, video and text for communities.", "WG GP AS FH SN HB", 4.4),
    _c("Telegram", "Telegram FZ-LLC", "Social", "✈️", "#2aabee", "Fast, secure cloud messaging.", "MS GP AS MA FH SN HB", 4.6),
    _c("WhatsApp", "Meta", "Social", "📞", "#25d366", "Simple, reliable private messaging.", "MS GP AS MA", 4.4),
    _c("Signal", "Signal Foundation", "Social", "🔒", "#3a76f0", "Privacy-first messenger.", "WG GP AS FH SN HB", 4.7),
    _c("OBS Studio", "OBS Project", "Video", "🔴", "#302e31", "Capture desktop and screen snapshots.", "WG FH SN HB", 4.7),
    _c("GIMP", "GIMP Team", "Creative", "🎨", "#8f6c3b", "Free advanced image editor.", "MS WG FH SN HB", 4.4),
    _c("Blender", "Blender Foundation", "Creative", "🌀", "#ea7600", "Interactive 3D modeling viewport.", "MS ST WG FH SN HB", 4.9),
    _c("Krita", "KDE", "Creative", "🖌️", "#3babff", "Digital painting for artists.", "MS ST WG FH SN HB", 4.8),
    _c("Inkscape", "Inkscape Project", "Creative", "✒️", "#2a2a2a", "Shapes, drawing and graphics studio.", "MS WG FH SN HB", 4.5),
    _c("LibreOffice", "The Document Foundation", "Productivity", "📄", "#18a303", "Rich word processor with PDF export.", "MS WG FH SN HB", 4.5),
    _c("Notion", "Notion Labs", "Productivity", "🗒️", "#3a3a3a", "Notes, docs and wikis in one place.", "MS GP AS MA WG HB", 4.5),
    _c("Obsidian", "Dynalist Inc.", "Productivity", "🔮", "#7c3aed", "Private, linked-note Markdown vault.", "WG FH SN HB GP AS", 4.8),
    _c("Bitwarden", "Bitwarden Inc.", "Security", "🔑", "#175ddc", "Password vault and generator.", "MS WG GP AS MA FH SN HB FD CW", 4.7),
    _c("uBlock Origin", "Raymond Hill", "Security", "🛡️", "#800000", "Efficient wide-spectrum content blocker.", "CW", 4.8),
    _c("Zoom", "Zoom Video", "Business", "📹", "#2d8cff", "Video meetings and chat.", "MS WG GP AS MA FH SN HB", 4.3),
    _c("Slack", "Salesforce", "Business", "🧵", "#611f69", "Team messaging and collaboration.", "MS WG GP AS MA FH SN HB", 4.3),
    _c("7-Zip", "Igor Pavlov", "Utilities", "🗜️", "#2c3e50", "File archiver with ZIP extract & compress.", "MS WG", 4.8),
    _c("Audacity", "Muse Group", "Music", "🎙️", "#0000cc", "Audio player and track preview.", "MS WG FH SN HB", 4.5),
    _c("Thunderbird", "Mozilla", "Productivity", "📧", "#0a84ff", "Free email client.", "MS WG FH SN HB FD", 4.4),
    _c("Python 3", "Python Software Foundation", "Developer", "🐍", "#3776ab", "Interactive Python interpreter.", "MS WG HB SN", 4.9),
    _c("Git", "Git Project", "Developer", "🌿", "#f05033", "Distributed version control terminal.", "WG HB SN", 4.8),
    _c("Docker Desktop", "Docker Inc.", "Developer", "🐳", "#2496ed", "Build and run containers.", "WG HB", 4.4),
    _c("Neovim", "Neovim Team", "Developer", "📝", "#57a143", "Code editor with syntax highlighting.", "WG HB SN FH", 4.7),
    _c("Kindle", "Amazon", "Books", "📚", "#232f3e", "Read eBooks on any device.", "MS GP AS MA AZ", 4.5),
    _c("Netflix", "Netflix", "Video", "🎬", "#e50914", "Movies and shows on demand.", "MS GP AS GX", 4.4),
    _c("Duolingo", "Duolingo", "Education", "🦉", "#58cc02", "Learn languages in short lessons.", "GP AS AZ", 4.7),
    _c("Wikipedia", "Wikimedia", "Education", "🌐", "#444444", "The free encyclopedia.", "GP AS FD", 4.6),
    _c("Stardew Valley", "ConcernedApe", "Games", "🌾", "#6aa84f", "Plant, water, grow and harvest crops.", "ST GG GP AS MS", 4.9),
    _c("Terraria", "Re-Logic", "Games", "⛏️", "#3b8a2e", "Till, grow and build your plot.", "ST GG GP AS EG", 4.8),
    _c("Hades", "Supergiant Games", "Games", "🔥", "#b0302c", "Real-time arena slasher.", "ST EG GG MS", 4.9),
    _c("Celeste", "Maddy Makes Games", "Games", "🏔️", "#e0517f", "Climb the mountain & grab strawberries.", "ST EG GG IT", 4.9),
    _c("Among Us", "InnerSloth", "Games", "🧑‍🚀", "#c51111", "Survive the arena waves.", "ST EG GP AS", 4.2),
    _c("Roblox", "Roblox Corp.", "Games", "🧱", "#e2231a", "Action arena sandbox.", "MS GP AS AZ", 4.3),
    _c("Steam", "Valve", "Games", "🎮", "#1b2838", "The PC gaming platform.", "WG HB FH SN", 4.5),
]
CATEGORIES = sorted({i["cat"] for i in CATALOG})
BY_NAME = {i["name"]: i for i in CATALOG}

# ───────────────────────────── built-in app info ─────────────────────────────
INFO = {
    "files": ("File Explorer", "📁", "#f0a30a"),
    "edge": ("Edge", "🌐", "#0fb5ae"),
    "store": ("Microsoft Store", "🛍️", "#0a84ff"),
    "notepad": ("Notepad", "📝", "#3aa0ff"),
    "calc": ("Calculator", "🧮", "#6a5cff"),
    "terminal": ("Terminal", "⌨️", "#3b3b44"),
    "settings": ("Settings", "⚙️", "#7b8190"),
}
SIZES = {"files": (900, 560), "edge": (1000, 640), "store": (1000, 660), "notepad": (700, 480),
         "calc": (340, 540), "terminal": (760, 440), "settings": (880, 580), "app": (760, 500)}
BUILTIN_ORDER = ["files", "edge", "store", "notepad", "calc", "terminal", "settings"]
PINNED = ["files", "edge", "store", "settings", "terminal"]

# ── OS skins: same shell + same Universal Store, different desktop personality ──
SKINS = {
    "win12":   dict(label="Windows 12", font="'Segoe UI Variable','Segoe UI'", wall=0, ins=(0, 0, 76),
                    title_h=40, win_r=10, tb_r=16, tb_gap=12, btn=46),
    "macos":   dict(label="macOS", font="'SF Pro Text','Helvetica Neue','Inter'", wall=3, ins=(28, 0, 86),
                    title_h=38, win_r=12, tb_r=22, tb_gap=8, btn=58),
    "ubuntu":  dict(label="Ubuntu", font="'Ubuntu','Cantarell'", wall=4, ins=(30, 64, 0),
                    title_h=42, win_r=12, tb_r=0, tb_gap=0, btn=52),
    "android": dict(label="Android", font="'Roboto','Google Sans'", wall=5, ins=(28, 0, 92),
                    title_h=48, win_r=0, tb_r=26, tb_gap=26, btn=54),
}
OS_LIST = ["win12", "macos", "ubuntu", "android"]
SKIN_APP = {
    "macos": {"files": ("Finder", "🗂️", "#2f9bff"), "edge": ("Safari", "🧭", "#1f8ef1"),
              "store": ("App Store", "🅰️", "#0a84ff"), "notepad": ("TextEdit", "📝", "#8e8e93"),
              "settings": ("System Settings", "⚙️", "#8e8e93"), "calc": ("Calculator", "🧮", "#ff9f0a"),
              "terminal": ("Terminal", "⌨️", "#1c1c1e")},
    "ubuntu": {"files": ("Files", "🗂️", "#e95420"), "edge": ("Firefox", "🦊", "#ff7139"),
               "store": ("Ubuntu Software", "🛍️", "#e95420"), "notepad": ("Text Editor", "📝", "#4a90d9"),
               "settings": ("Settings", "⚙️", "#6d6d6d"), "terminal": ("Terminal", "⌨️", "#300a24")},
    "android": {"files": ("Files", "🗂️", "#1a73e8"), "edge": ("Chrome", "🌐", "#4285f4"),
                "store": ("Play Store", "▶️", "#01875f"), "notepad": ("Keep Notes", "📝", "#fbbc04"),
                "settings": ("Settings", "⚙️", "#5f6368"), "calc": ("Calculator", "🧮", "#34a853"),
                "terminal": ("Termux", "⌨️", "#202124")},
}
PINNED_BY = {"win12": PINNED, "macos": list(BUILTIN_ORDER),
             "ubuntu": ["edge", "files", "store", "terminal", "settings"],
             "android": ["files", "edge", "store", "settings"]}


def info(key):
    return SKIN_APP.get(S.skin, {}).get(key, INFO[key])


def title_h():
    return SKINS[S.skin]["title_h"]


# ───────────────────────────── window manager ─────────────────────────────
class CapButton(QPushButton):
    def __init__(self, sym, danger=False):
        super().__init__(sym)
        self.setFixedSize(46, TITLE_H)
        self.setCursor(Qt.ArrowCursor)
        hov = "#e81123" if danger else "rgba(128,128,128,0.28)"
        self.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:0;font-size:12px;padding:0;}}"
                           f"QPushButton:hover{{background:{hov};color:{'white' if danger else 'inherit'};}}")


class Dot(QPushButton):   # macOS traffic light
    def __init__(self, color):
        super().__init__()
        self.setFixedSize(13, 13)
        self.setStyleSheet(f"QPushButton{{background:{color};border:none;border-radius:6px;padding:0;}}"
                           f"QPushButton:hover{{background:{QColor(color).lighter(115).name()};}}")


class GCap(QPushButton):  # GNOME headerbar button
    def __init__(self, sym):
        super().__init__(sym)
        self.setFixedSize(26, 26)
        self.setStyleSheet("QPushButton{background:rgba(128,128,128,0.22);border:none;border-radius:13px;"
                           "padding:0;font-size:11px;}QPushButton:hover{background:rgba(128,128,128,0.4);}")


class TitleBar(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win, self.drag = win, None
        self.lay = QHBoxLayout(self)
        self.build()

    def build(self):
        lay, win, sk = self.lay, self.win, S.skin
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().setParent(None); it.widget().deleteLater()
        self.setFixedHeight(title_h())
        lay.setSpacing(8)
        if sk == "macos":
            lay.setContentsMargins(14, 0, 14, 0)
            for col, fn in (("#ff5f57", win.close_win), ("#febc2e", win.minimize), ("#28c840", win.toggle_max)):
                b = Dot(col); b.clicked.connect(fn); lay.addWidget(b)
            lay.addStretch()
            self.title = QLabel(f"<b>{win.title_text}</b>"); lay.addWidget(self.title)
            lay.addStretch(); lay.addSpacing(55)
        elif sk == "ubuntu":
            lay.setContentsMargins(12, 0, 10, 0)
            lay.addSpacing(86); lay.addStretch()
            self.title = QLabel(f"<b>{win.title_text}</b>"); lay.addWidget(self.title)
            lay.addStretch()
            for sym, fn in (("—", win.minimize), ("▢", win.toggle_max), ("✕", win.close_win)):
                b = GCap(sym); b.clicked.connect(fn); lay.addWidget(b)
        elif sk == "android":
            lay.setContentsMargins(6, 0, 12, 0)
            b = QPushButton("←"); b.setProperty("kind", "flat"); b.setFixedSize(40, 40)
            b.setStyleSheet("font-size:20px;"); b.clicked.connect(win.close_win); lay.addWidget(b)
            self.title = QLabel(f"<span style='font-size:17px'>{win.title_text}</span>"); lay.addWidget(self.title)
            lay.addStretch()
        else:
            lay.setContentsMargins(12, 0, 0, 0)
            ic = QLabel(); ic.setPixmap(tile(win.emoji, win.color, 20)); lay.addWidget(ic)
            self.title = QLabel(win.title_text); lay.addWidget(self.title); lay.addStretch()
            for sym, fn, danger in (("—", win.minimize, False), ("▢", win.toggle_max, False), ("✕", win.close_win, True)):
                b = CapButton(sym, danger); b.clicked.connect(fn); lay.addWidget(b)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.win.maxed:
            self.drag = e.globalPosition().toPoint() - self.win.pos()

    def mouseMoveEvent(self, e):
        if self.drag is not None:
            n = e.globalPosition().toPoint() - self.drag
            top, left, _ = SKINS[S.skin]["ins"]
            self.win.move(max(left, n.x()), max(top, n.y()))

    def mouseReleaseEvent(self, e):
        self.drag = None

    def mouseDoubleClickEvent(self, e):
        self.win.toggle_max()


class Grip(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win, self.p = win, None
        self.setFixedSize(16, 16); self.setCursor(Qt.SizeFDiagCursor)

    def mousePressEvent(self, e):
        self.p, self.sz = e.globalPosition().toPoint(), self.win.size()

    def mouseMoveEvent(self, e):
        if self.p is not None:
            d = e.globalPosition().toPoint() - self.p
            self.win.resize(max(self.win.minimumWidth(), self.sz.width() + d.x()),
                            max(self.win.minimumHeight(), self.sz.height() + d.y()))

    def mouseReleaseEvent(self, e):
        self.p = None


class OSWindow(QFrame):
    def __init__(self, desk, key, title, emoji, color, content, size, shadow=True):
        super().__init__(desk)
        self.desk, self.key, self.title_text, self.emoji, self.color = desk, key, title, emoji, color
        self.maxed, self.normal = False, None
        self.setMinimumSize(320, 220); self.resize(*size)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(1, 0, 1, 1); lay.setSpacing(0)
        self.bar = TitleBar(self)
        lay.addWidget(self.bar); lay.addWidget(content, 1)
        self.content = content
        self.grip = Grip(self)
        if shadow:
            eff = QGraphicsDropShadowEffect(self)
            eff.setBlurRadius(42); eff.setOffset(0, 10); eff.setColor(QColor(0, 0, 0, 130))
            self.setGraphicsEffect(eff)

    def contextMenuEvent(self, e):
        e.accept()

    def resizeEvent(self, e):
        self.grip.move(self.width() - 16, self.height() - 16); self.grip.raise_()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = 0 if self.maxed else SKINS[S.skin]["win_r"]
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), r, r)
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor(*T()["solid"]))
        paint_blur(p, self, QRect(0, 0, self.width(), title_h()))
        p.setClipping(False)
        p.setPen(QPen(QColor(*T()["border"]), 1)); p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    def minimize(self):
        self.hide(); self.desk.after_change()

    def toggle_max(self):
        if self.maxed:
            self.setGeometry(self.normal); self.maxed = False; self.grip.show()
        else:
            self.normal = self.geometry(); self.maxed = True; self.grip.hide()
            self.setGeometry(self.desk.work_rect())
        self.update()

    def close_win(self):
        if hasattr(self.content, "cleanup"):
            try:
                self.content.cleanup()
            except Exception:
                pass
        self.desk.close_window(self)

    def apply_skin(self):
        if self.key in INFO:
            self.title_text, self.emoji, self.color = info(self.key)
        self.bar.build()
        top, left, _ = SKINS[S.skin]["ins"]
        if S.skin == "android" and not self.maxed:
            self.toggle_max()
        elif self.maxed:
            self.setGeometry(self.desk.work_rect())
        else:
            self.move(max(left, self.x()), max(top, self.y()))
        self.update()


# ───────────────────────────── taskbar / tray ─────────────────────────────
def draw_dots(p, rect, color):
    p.setPen(Qt.NoPen); p.setBrush(color)
    cx, cy = rect.center().x(), rect.center().y()
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            p.drawEllipse(QPointF(cx + i * 7, cy + j * 7), 2.2, 2.2)


class TBButton(QWidget):
    def __init__(self, kind, emoji="", color="", cb=None, tip=""):
        super().__init__()
        self.kind, self.emoji, self.color, self.cb = kind, emoji, color, cb
        self.hover = self.down = self.running = self.active = False
        sz = SKINS[S.skin]["btn"]
        self.setFixedSize(sz, sz); self.setMouseTracking(True); self.setToolTip(tip)

    def enterEvent(self, e): self.hover = True; self.update()
    def leaveEvent(self, e): self.hover = self.down = False; self.update()
    def mousePressEvent(self, e): self.down = True; self.update()

    def mouseReleaseEvent(self, e):
        was = self.down; self.down = False; self.update()
        if was and self.rect().contains(e.position().toPoint()) and self.cb:
            self.cb()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        sk, s = S.skin, self.width()
        hov = QColor(*T()["hover"])
        if sk == "macos":
            sz = 52 if self.hover else 44
            pm = tile("🚀", "#6e7bf2", sz) if self.kind == "start" else tile(self.emoji, self.color, sz)
            p.drawPixmap((s - sz) // 2, s - sz - 7, pm)
            if self.running:
                p.setPen(Qt.NoPen); p.setBrush(QColor(150, 155, 165)); p.drawEllipse(QPointF(s / 2, s - 3), 2, 2)
            return
        if sk == "ubuntu":
            if self.hover or self.active:
                p.setPen(Qt.NoPen); p.setBrush(hov)
                p.drawRoundedRect(QRectF(self.rect()).adjusted(3, 2, -3, -2), 9, 9)
            if self.kind == "start":
                draw_dots(p, self.rect(), QColor(T()["text"]))
            else:
                p.drawPixmap((s - 38) // 2, (s - 38) // 2, tile(self.emoji, self.color, 38))
            if self.running:
                p.setPen(Qt.NoPen); p.setBrush(QColor(S.accent) if self.active else QColor(150, 155, 165))
                p.drawRoundedRect(QRectF(0, s / 2 - 7, 3, 14), 1.5, 1.5)
            return
        if sk == "android":
            if self.kind == "start":
                p.setPen(Qt.NoPen); p.setBrush(QColor(255, 255, 255, 40 if not self.hover else 70))
                p.drawEllipse(QRectF(self.rect()).adjusted(5, 5, -5, -5))
                draw_dots(p, self.rect(), QColor(T()["text"]))
            else:
                sz = 44 if self.hover else 40
                p.drawPixmap((s - sz) // 2, (s - sz) // 2, tile(self.emoji, self.color, sz))
            return
        # Windows 12
        if self.hover or self.active:
            p.setPen(Qt.NoPen); p.setBrush(hov)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 8, 8)
        if self.kind == "start":
            draw_logo(p, QRect(11, 10, 24, 24))
        elif self.kind == "search":
            f = QFont(); f.setPixelSize(20); p.setFont(f); p.setPen(QColor(T()["text"]))
            p.drawText(self.rect().adjusted(0, -3, 0, -3), Qt.AlignCenter, "🔍")
        else:
            p.drawPixmap(9, 7, tile(self.emoji, self.color, 28))
        if self.running:
            w = 16 if self.active else 6
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(S.accent) if self.active else QColor(150, 155, 165))
            p.drawRoundedRect(QRectF((46 - w) / 2, 41, w, 3), 1.5, 1.5)


class Taskbar(Acrylic):
    """Windows: floating taskbar · macOS: dock · Ubuntu: left dock · Android: hotseat."""
    MARG = {"win12": (10, 6, 4, 58), "macos": (12, 7, 6, 72), "ubuntu": (6, 8, 4, 0), "android": (14, 6, 10, 66)}

    def __init__(self, desk):
        sk = S.skin
        super().__init__(desk, SKINS[sk]["tb_r"])
        self.desk, self.btn_start = desk, None
        ml, mt, sp, h = self.MARG[sk]
        self.lay = QVBoxLayout(self) if sk == "ubuntu" else QHBoxLayout(self)
        self.lay.setContentsMargins(ml, mt, ml, mt); self.lay.setSpacing(sp)
        if sk == "ubuntu": self.setFixedWidth(64)
        else: self.setFixedHeight(h)

    def refresh(self):
        while self.lay.count():
            w = self.lay.takeAt(0).widget()
            if w:
                w.setParent(None); w.deleteLater()
        d, sk = self.desk, S.skin
        self.btn_start = TBButton("start", cb=d.toggle_start, tip="Start" if sk == "win12" else "Apps")
        keys = list(PINNED_BY[sk])
        extra = []
        for w in d.wins:
            if w.key not in keys and w.key not in [x[0] for x in extra]:
                extra.append((w.key, w.emoji, w.color, w.title_text))
        entries = [(k, info(k)[1], info(k)[2], info(k)[0]) for k in keys] + extra
        btns = []
        for key, emoji, color, title in entries:
            b = TBButton("app", emoji, color, cb=lambda k=key: d.tb_click(k), tip=title)
            b.running = any(w.key == key for w in d.wins)
            b.active = bool(d.active and d.active.key == key and d.active.isVisible())
            btns.append(b)
        if sk == "win12": seq = [self.btn_start, TBButton("search", cb=lambda: d.toggle_start(True), tip="Search")] + btns
        elif sk == "macos": seq = [self.btn_start] + btns
        elif sk == "android": seq = btns[:len(btns) // 2] + [self.btn_start] + btns[len(btns) // 2:]
        else: seq = btns
        for b in seq:
            self.lay.addWidget(b)
        if sk == "ubuntu":
            self.lay.addStretch(); self.lay.addWidget(self.btn_start); seq = seq + [self.btn_start]
        else:
            ml, mt, sp, h = self.MARG[sk]
            n = len(seq)
            self.setFixedWidth(2 * ml + n * SKINS[sk]["btn"] + (n - 1) * sp)
        for b in seq:
            b.show()
        if d.chrome_ready:
            d.layout_chrome(); d.update_topbar()


class TopBar(Acrylic):
    """macOS menu bar · Ubuntu top panel · Android status bar."""
    def __init__(self, desk):
        super().__init__(desk, 0)
        self.desk, self.act_btn, self.app_lbl, self.clock, self.right = desk, None, None, None, None
        sk = self.sk = S.skin
        self.setFixedHeight(SKINS[sk]["ins"][0])
        lay = QHBoxLayout(self); lay.setContentsMargins(12, 0, 12, 0); lay.setSpacing(14)
        light = "color:white;font-size:12px;" if sk in ("ubuntu", "android") else ""

        def lab(t=""):
            l = QLabel(t)
            if light: l.setStyleSheet(light)
            return l

        def flat(t):
            b = QPushButton(t); b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(("QPushButton{background:transparent;border:none;padding:0 10px;color:%s;font-size:12px;}"
                             "QPushButton:hover{background:rgba(255,255,255,0.16);border-radius:12px;}")
                            % ("white" if light else T()["text"]))
            return b

        if sk == "macos":
            ap = flat("🍎"); m = QMenu(self); desk.fill_power_menu(m)
            ap.clicked.connect(lambda: m.exec(ap.mapToGlobal(QPoint(0, ap.height()))))
            lay.addWidget(ap)
            self.app_lbl = QLabel("<b>Finder</b>"); lay.addWidget(self.app_lbl)
            for t in ("File", "Edit", "View", "Go", "Window", "Help"):
                lay.addWidget(lab(t))
            lay.addStretch(); self.right = lab(); lay.addWidget(self.right)
        elif sk == "ubuntu":
            self.act_btn = flat("Activities"); self.act_btn.clicked.connect(desk.toggle_start); lay.addWidget(self.act_btn)
            lay.addStretch(); self.clock = lab(); lay.addWidget(self.clock); lay.addStretch()
            lay.addWidget(lab("🛜  🔊  🔋"))
            pw = flat("⏻"); m = QMenu(self); desk.fill_power_menu(m)
            pw.clicked.connect(lambda: m.exec(pw.mapToGlobal(QPoint(0, pw.height())))); lay.addWidget(pw)
        else:
            self.clock = lab(); lay.addWidget(self.clock); lay.addStretch(); lay.addWidget(lab("📶  🛜  🔋"))
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(1000)
        self.tick()

    def set_app(self, name):
        if self.app_lbl: self.app_lbl.setText(f"<b>{name}</b>")

    def tick(self):
        n = QDateTime.currentDateTime()
        if self.right: self.right.setText("🛜  🔊  🔋     " + n.toString("ddd MMM d   h:mm AP"))
        if self.clock is None: return
        if self.sk == "ubuntu": self.clock.setText(n.toString("MMM d   h:mm AP"))
        elif self.sk == "android": self.clock.setText(n.toString("h:mm"))

    def paintEvent(self, e):
        p = QPainter(self)
        if self.sk == "ubuntu":
            p.fillRect(self.rect(), QColor(8, 8, 8, 225))
        elif self.sk == "macos":
            paint_blur(p, self, self.rect())
            p.setPen(QColor(*T()["border"])); p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


class HomePill(QWidget):
    """Android gesture-navigation pill: tap to go home."""
    def __init__(self, desk):
        super().__init__(desk)
        self.desk = desk
        self.setFixedSize(150, 14); self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen); p.setBrush(QColor(255, 255, 255, 210))
        p.drawRoundedRect(QRectF(25, 4, 100, 5), 2.5, 2.5)

    def mouseReleaseEvent(self, e):
        self.desk.go_home()


class Tray(Acrylic):
    def __init__(self, desk):
        super().__init__(desk, 16)
        self.setFixedHeight(58)
        lay = QHBoxLayout(self); lay.setContentsMargins(16, 4, 16, 4); lay.setSpacing(12)
        self.icons = QLabel("🛜  🔊  🔋")
        self.clock = QLabel(); self.clock.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.icons); lay.addWidget(self.clock)
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(1000)
        self.tick()

    def tick(self):
        n = QDateTime.currentDateTime()
        self.clock.setText(n.toString("h:mm AP") + "\n" + n.toString("M/d/yyyy"))
        self.adjustSize()


# ───────────────────────────── start menu ─────────────────────────────
class AppTile(QWidget):
    def __init__(self, ent, cb):
        super().__init__()
        self.ent, self.cb, self.hover = ent, cb, False
        self.setFixedSize(88, 86); self.setMouseTracking(True)

    def enterEvent(self, e): self.hover = True; self.update()
    def leaveEvent(self, e): self.hover = False; self.update()

    def mouseReleaseEvent(self, e):
        if self.rect().contains(e.position().toPoint()):
            self.cb(self.ent)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        if self.hover:
            p.setPen(Qt.NoPen); p.setBrush(QColor(*T()["hover"]))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 8, 8)
        p.drawPixmap((88 - 38) // 2, 8, tile(self.ent["emoji"], self.ent["color"], 38))
        p.setPen(QColor(T()["text"]))
        fm = QFontMetrics(p.font())
        p.drawText(QRect(2, 52, 84, 28), Qt.AlignHCenter | Qt.AlignTop,
                   fm.elidedText(self.ent["title"], Qt.ElideRight, 82))


class StartMenu(Acrylic):
    """Windows: Start menu · others: full-screen launcher (Launchpad / Activities / app drawer)."""
    W, H = 640, 690

    def __init__(self, desk):
        self.full = S.skin != "win12"
        super().__init__(desk, 0 if self.full else 18)
        self.desk, self.cols, self.ents = desk, 6, []
        full = self.full
        if not full: self.setFixedSize(self.W, self.H)
        v = QVBoxLayout(self)
        v.setContentsMargins(*((60, 30, 60, 24) if full else (26, 24, 26, 16))); v.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search" if full else "🔍  Search for apps, settings, and documents")
        self.search.setMinimumHeight(38)
        self.search.textChanged.connect(self.refresh_apps)
        self.search.returnPressed.connect(self.enter)
        if full:
            self.search.setFixedWidth(480); v.addWidget(self.search, 0, Qt.AlignHCenter)
        else:
            v.addWidget(self.search)
        self.pin_title = QLabel("<b>Pinned</b>"); v.addWidget(self.pin_title)
        self.grid_w = QWidget(); self.grid = QGridLayout(self.grid_w)
        self.grid.setContentsMargins(0, 0, 0, 0); self.grid.setSpacing(2)
        self.grid.setAlignment(Qt.AlignTop | (Qt.AlignHCenter if full else Qt.AlignLeft))
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(self.grid_w); sc.setMinimumHeight(250)
        v.addWidget(sc, 1)
        self.rec_title = QLabel("<b>Recommended</b>"); v.addWidget(self.rec_title)
        self.rec = QLabel(); self.rec.setProperty("sub", True); self.rec.setWordWrap(True)
        self.rec.setMinimumHeight(110); self.rec.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        v.addWidget(self.rec)
        self.foot_w = QWidget(); foot = QHBoxLayout(self.foot_w); foot.setContentsMargins(0, 0, 0, 0)
        av = QLabel(); av.setPixmap(tile("🙂", "#6a5cff", 30)); foot.addWidget(av)
        foot.addWidget(QLabel(getpass.getuser().title())); foot.addStretch()
        pw = QPushButton("⏻"); pw.setProperty("kind", "flat"); pw.setFixedSize(38, 34)
        m = QMenu(self); desk.fill_power_menu(m)
        pw.clicked.connect(lambda: m.exec(pw.mapToGlobal(QPoint(0, -m.sizeHint().height()))))
        foot.addWidget(pw)
        v.addWidget(self.foot_w)
        if full:
            for x in (self.pin_title, self.rec_title, self.rec, self.foot_w):
                x.hide()
        self.hide()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape: self.hide()
        else: super().keyPressEvent(e)

    def fit(self):
        d = self.desk
        if self.full:
            top, left, _ = SKINS[S.skin]["ins"]
            self.setGeometry(left, top, d.width() - left, d.height() - top)
            self.cols = max(4, (self.width() - 160) // 100)
        else:
            self.setFixedSize(self.W, self.H)

    def refresh_apps(self, q=""):
        q = (q or "").strip()
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.setParent(None); w.deleteLater()
        ents = [e for e in self.desk.entries() if q.lower() in e["title"].lower()]
        if q:
            ents.append(dict(title="Search Store", emoji=info("store")[1], color=info("store")[2],
                             launch=lambda: self.desk.launch("store", q)))
        self.ents = ents
        if not self.full:
            self.pin_title.setText("<b>Best match</b>" if q else "<b>Pinned</b>")
            self.rec_title.setVisible(not q); self.rec.setVisible(not q)
            r = self.desk.recent[-4:][::-1]
            self.rec.setText("<br>".join(f"🕘  {x}" for x in r) if r else "Apps you open will show up here.")
        for i, e in enumerate(ents if self.full else ents[:30]):
            self.grid.addWidget(AppTile(e, self.activate), i // self.cols, i % self.cols)

    def enter(self):
        if self.ents:
            self.activate(self.ents[0])

    def activate(self, ent):
        self.hide()
        ent["launch"]()

    def popup(self, focus_search=False):
        d = self.desk
        self.fit(); self.refresh_apps(); self.search.clear()
        if self.full:
            x, y = self.x(), self.y()
        else:
            x, y = (d.width() - self.W) // 2, d.height() - self.H - 82
        self.move(x, y + 36); self.show(); self.raise_(); d.layout_chrome()
        self.anim = QPropertyAnimation(self, b"pos", self)
        self.anim.setDuration(170); self.anim.setStartValue(QPoint(x, y + 36)); self.anim.setEndValue(QPoint(x, y))
        self.anim.setEasingCurve(QEasingCurve.OutCubic); self.anim.start()
        self.search.setFocus()


# ───────────────────────────── core built-in apps ─────────────────────────────
class Files(QWidget):
    def __init__(self, desk, arg=None):
        super().__init__()
        self.desk = desk
        self.cwd = Path(arg) if arg else Path.home()
        self.hist = []
        outer = QHBoxLayout(self); outer.setContentsMargins(10, 6, 10, 10); outer.setSpacing(10)
        nav = QListWidget(); nav.setFixedWidth(170)
        home = Path.home()
        self.places = [("🏠  Home", home)] + [(f"{ic}  {n}", home / n) for ic, n in
                                              (("🖥️", "Desktop"), ("📄", "Documents"), ("⬇️", "Downloads"),
                                               ("🖼️", "Pictures"), ("🎵", "Music"), ("🎞️", "Videos"))
                                              if (home / n).exists()]
        for t, pth in self.places:
            nav.addItem(t)
        nav.currentRowChanged.connect(lambda i: self.go(self.places[i][1]) if i >= 0 else None)
        outer.addWidget(nav)
        right = QVBoxLayout(); right.setSpacing(8); outer.addLayout(right, 1)
        bar = QHBoxLayout()
        for sym, fn in (("←", self.back), ("↑", self.up)):
            b = QPushButton(sym); b.setFixedWidth(40); b.clicked.connect(fn); bar.addWidget(b)
        self.path = QLineEdit(); self.path.returnPressed.connect(lambda: self.go(Path(self.path.text())))
        bar.addWidget(self.path, 1)
        right.addLayout(bar)
        self.list = QListWidget(); self.list.itemDoubleClicked.connect(self.open_item)
        right.addWidget(self.list, 1)
        self.status = QLabel(); self.status.setProperty("sub", True); right.addWidget(self.status)
        self.go(self.cwd, push=False)

    def go(self, pth, push=True):
        pth = Path(pth).expanduser()
        try:
            entries = sorted((x for x in pth.iterdir() if not x.name.startswith(".")),
                             key=lambda x: (not x.is_dir(), x.name.lower()))[:2000]
        except Exception as ex:
            self.status.setText(f"Can't open: {ex}"); return
        if push:
            self.hist.append(self.cwd)
        self.cwd = pth
        self.path.setText(str(pth)); self.list.clear()
        for x in entries:
            it = QListWidgetItem(("📁  " if x.is_dir() else "📄  ") + x.name)
            it.setData(Qt.UserRole, str(x)); self.list.addItem(it)
        self.status.setText(f"{len(entries)} items")

    def back(self):
        if self.hist:
            self.go(self.hist.pop(), push=False)

    def up(self):
        self.go(self.cwd.parent)

    def open_item(self, it):
        pth = Path(it.data(Qt.UserRole))
        ext = pth.suffix.lower()
        if pth.is_dir():
            self.go(pth)
        elif ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
            self.desk.open_tool("GIMP", str(pth))
        elif ext in {".mp4", ".mkv", ".mov", ".avi", ".mp3", ".wav", ".ogg", ".flac", ".m4a"}:
            self.desk.open_tool("VLC", str(pth))
        elif ext == ".zip":
            self.desk.open_tool("7-Zip", str(pth))
        elif ext == ".py":
            self.desk.open_tool("Visual Studio Code", str(pth))
        elif ext in {".txt", ".md", ".json", ".log", ".csv", ".ini", ".cfg", ".html", ".js", ".css"}:
            self.desk.launch("notepad", str(pth))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(pth)))


class Notepad(QWidget):
    def __init__(self, desk, arg=None):
        super().__init__()
        self.file = None
        v = QVBoxLayout(self); v.setContentsMargins(10, 6, 10, 10); v.setSpacing(8)
        bar = QHBoxLayout()
        for t, fn in (("Open", self.open), ("Save", self.save), ("Save as", self.save_as)):
            b = QPushButton(t); b.clicked.connect(fn); bar.addWidget(b)
        bar.addStretch(); self.info = QLabel("Untitled"); self.info.setProperty("sub", True); bar.addWidget(self.info)
        v.addLayout(bar)
        self.ed = QTextEdit(); self.ed.setFont(QFont("Consolas", 12)); v.addWidget(self.ed, 1)
        if arg:
            self.load(arg)

    def load(self, f):
        try:
            self.ed.setPlainText(Path(f).read_text(encoding="utf-8", errors="replace"))
            self.file = f; self.info.setText(Path(f).name)
        except Exception as ex:
            self.info.setText(str(ex))

    def open(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open")
        if f: self.load(f)

    def save(self):
        if not self.file: return self.save_as()
        try:
            Path(self.file).write_text(self.ed.toPlainText(), encoding="utf-8")
            self.info.setText(Path(self.file).name + " — saved")
        except Exception as ex:
            self.info.setText(f"Save error: {ex}")

    def save_as(self):
        f, _ = QFileDialog.getSaveFileName(self, "Save as")
        if f: self.file = f; self.save()


def safe_eval(expr):
    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}

    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in ops: return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        raise ValueError("bad expression")
    return ev(ast.parse(expr, mode="eval"))


class Calculator(QWidget):
    def __init__(self, desk, arg=None):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        v = QVBoxLayout(self); v.setContentsMargins(12, 6, 12, 12); v.setSpacing(6)
        self.hist = QLabel(""); self.hist.setProperty("sub", True); self.hist.setAlignment(Qt.AlignRight)
        self.disp = QLabel("0"); self.disp.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f = self.disp.font(); f.setPixelSize(40); f.setBold(True); self.disp.setFont(f)
        self.disp.setMinimumHeight(70)
        v.addWidget(self.hist); v.addWidget(self.disp)
        g = QGridLayout(); g.setSpacing(5); v.addLayout(g)
        keys = ["C", "(", ")", "÷", "7", "8", "9", "×", "4", "5", "6", "−", "1", "2", "3", "+", "⌫", "0", ".", "="]
        for i, k in enumerate(keys):
            b = QPushButton(k); b.setProperty("kind", "eq" if k == "=" else "key")
            b.clicked.connect(lambda _, k=k: self.press(k)); g.addWidget(b, i // 4, i % 4)
        self.text = ""

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter): self.press("=")
        elif e.key() == Qt.Key_Backspace: self.press("⌫")
        elif e.key() == Qt.Key_Escape: self.press("C")
        elif e.text() in "0123456789.+-*/()":
            mp = {"/": "÷", "*": "×", "-": "−"}
            self.press(mp.get(e.text(), e.text()))

    def press(self, k):
        if k == "C": self.text = ""; self.hist.setText("")
        elif k == "⌫": self.text = self.text[:-1]
        elif k == "=":
            try:
                r = safe_eval(self.text.replace("÷", "/").replace("×", "*").replace("−", "-"))
                self.hist.setText(self.text + " =")
                self.text = str(round(r, 10)).rstrip("0").rstrip(".") if isinstance(r, float) else str(r)
            except Exception:
                self.hist.setText("Invalid input"); self.text = ""
        else: self.text += k
        self.disp.setText(self.text or "0")


class Terminal(QPlainTextEdit):
    BANNER = "Windows 12 [Version 12.0.26100.1 · Python Edition]\nBuilt-in commands: type 'help'. Anything else runs as a real program (git, python, ...).\n"

    def ptext(self):
        return f"{self.cwd}> "

    def __init__(self, desk, arg=None):
        super().__init__()
        self.desk, self.cwd = desk, Path.home()
        self.setStyleSheet("QPlainTextEdit{background:rgba(0,0,0,0.4);color:#e6e6e6;border-radius:0;border:none;"
                           "font-family:'Cascadia Mono',Consolas,'DejaVu Sans Mono',monospace;font-size:13px;}")
        self.appendPlainText(self.BANNER)
        self.prompt()

    def prompt(self):
        self.moveCursor(self.textCursor().MoveOperation.End)
        self.insertPlainText(self.ptext())
        self.start = len(self.toPlainText())
        self.moveCursor(self.textCursor().MoveOperation.End)

    def keyPressEvent(self, e):
        c = self.textCursor()
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            line = self.toPlainText()[self.start:]
            self.moveCursor(c.MoveOperation.End); self.insertPlainText("\n")
            out = self.run(line)
            if out == "\f": self.setPlainText("")
            elif out: self.insertPlainText(out + "\n")
            self.prompt(); return
        if e.key() in (Qt.Key_Backspace, Qt.Key_Left) and c.position() <= self.start: return
        if e.key() == Qt.Key_Home:
            c.setPosition(self.start); self.setTextCursor(c); return
        if c.position() < self.start: self.moveCursor(c.MoveOperation.End)
        super().keyPressEvent(e)

    def run(self, line):
        line = line.strip()
        if not line: return ""
        cmd, *a = line.split(maxsplit=1); a = a[0] if a else ""
        cmd = cmd.lower()
        if cmd == "help":
            return "help  dir/ls  cd  cat/type  echo  cls/clear  date  whoami  ver  neofetch  store  python  (other commands run for real)"
        if cmd in ("cls", "clear"): return "\f"
        if cmd == "echo": return a
        if cmd == "date": return QDateTime.currentDateTime().toString()
        if cmd == "whoami": return getpass.getuser()
        if cmd == "ver": return "Windows 12 [Version 12.0.26100.1]"
        if cmd == "python": return sys.version
        if cmd in ("dir", "ls"):
            try: return "\n".join(("<DIR>  " if x.is_dir() else "       ") + x.name for x in sorted(self.cwd.iterdir()))
            except Exception as ex: return str(ex)
        if cmd == "cd":
            t = (self.cwd / a).expanduser().resolve() if a else Path.home()
            if t.is_dir(): self.cwd = t; return ""
            return "The system cannot find the path specified."
        if cmd in ("cat", "type"):
            try: return (self.cwd / a).read_text(encoding="utf-8", errors="replace")[:4000]
            except Exception as ex: return str(ex)
        if cmd == "store":
            return "\n".join(f"{n}  ({s})" for n, s in S.installed.items()) or "No Store apps installed."
        if cmd == "neofetch":
            return (f"{getpass.getuser()}@windows12\nOS: Windows 12 (Python Edition)\nHost OS: {platform.system()} {platform.release()}\n"
                    f"Python: {platform.python_version()}\nShell: sf.py\nStore apps: {len(S.installed)}/{len(CATALOG)}")
        try:
            r = subprocess.run(shlex.split(line, posix=(os.name != "nt")), cwd=self.cwd,
                               capture_output=True, text=True, timeout=15)
            return (r.stdout + r.stderr).rstrip()
        except FileNotFoundError:
            return f"'{cmd}' is not recognized as an internal or external command."
        except subprocess.TimeoutExpired:
            return "Command timed out after 15 seconds."
        except Exception as ex:
            return str(ex)


class Browser(QWidget):
    def __init__(self, desk, arg=None):
        super().__init__()
        v = QVBoxLayout(self); v.setContentsMargins(8, 4, 8, 8); v.setSpacing(6)
        bar = QHBoxLayout()
        self.url = QLineEdit(); self.url.setPlaceholderText("Search or enter web address")
        bar.addWidget(self.url, 1); v.addLayout(bar)
        if HAVE_WEB:
            self.view = QWebEngineView()
            for sym, fn in (("←", self.view.back), ("→", self.view.forward), ("⟳", self.view.reload)):
                b = QPushButton(sym); b.setFixedWidth(38); b.clicked.connect(fn); bar.insertWidget(bar.count() - 1, b)
            self.view.urlChanged.connect(lambda u: self.url.setText(u.toString()))
            self.view.setUrl(QUrl(arg or "https://www.bing.com"))
            v.addWidget(self.view, 1)
        else:
            note = QLabel("Embedded browser engine not available.\nAddresses typed here open in your default browser.")
            note.setProperty("sub", True); note.setAlignment(Qt.AlignCenter); v.addWidget(note, 1)
        self.url.returnPressed.connect(self.go)
        if arg and not HAVE_WEB: webbrowser.open(arg)

    def go(self):
        t = self.url.text().strip()
        u = ("https://www.bing.com/search?q=" + QUrl.toPercentEncoding(t).data().decode()
             if (" " in t or "." not in t) else (t if "://" in t else "https://" + t))
        if HAVE_WEB: self.view.setUrl(QUrl(u))
        else: webbrowser.open(u)


# ───────────────────────────── real working Store apps ─────────────────────────────
class PyConsole(Terminal):
    """Working Python REPL (Python 3)."""
    BANNER = f"Python {platform.python_version()} — built-in console (close the window to exit)\n"
    more = False

    def ptext(self):
        return "... " if self.more else ">>> "

    def __init__(self, desk, arg=None):
        super().__init__(desk, arg)
        outer = self
        self._buf = []

        class C(code.InteractiveConsole):
            def write(self, data): outer._buf.append(data)
        self.con = C({"__name__": "__console__"})

    def run(self, line):
        self._buf = []; out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                self.more = self.con.push(line.rstrip())
        except SystemExit:
            self.more = False; return "Close the window to exit."
        return (out.getvalue() + "".join(self._buf)).rstrip("\n")


class ZipTool(QWidget):
    """Working ZIP archive tool (7-Zip)."""
    def __init__(self, desk, arg=None):
        super().__init__()
        self.path = None
        v = QVBoxLayout(self); v.setContentsMargins(10, 6, 10, 10); v.setSpacing(8)
        bar = QHBoxLayout()
        for t, fn in (("Open archive", self.open), ("Extract all", self.extract), ("New archive from folder", self.create)):
            b = QPushButton(t); b.clicked.connect(fn); bar.addWidget(b)
        bar.addStretch(); v.addLayout(bar)
        self.lst = QListWidget(); v.addWidget(self.lst, 1)
        self.st = QLabel("Open a .zip archive, or compress a folder into one."); self.st.setProperty("sub", True)
        v.addWidget(self.st)
        if arg:
            self.load_zip(arg)

    def load_zip(self, f):
        try:
            with zipfile.ZipFile(f) as z:
                names = z.namelist()
            self.path = f; self.lst.clear(); self.lst.addItems(names[:3000])
            self.st.setText(f"{Path(f).name}: {len(names)} entries")
        except Exception as ex:
            self.st.setText(f"Can't open: {ex}")

    def open(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open archive", "", "Zip archives (*.zip)")
        if f: self.load_zip(f)

    def extract(self):
        if not self.path: self.st.setText("Open an archive first."); return
        d = QFileDialog.getExistingDirectory(self, "Extract to")
        if not d: return
        try:
            with zipfile.ZipFile(self.path) as z: z.extractall(d)
            self.st.setText(f"Extracted to {d}")
        except Exception as ex:
            self.st.setText(f"Extract failed: {ex}")

    def create(self):
        d = QFileDialog.getExistingDirectory(self, "Folder to compress")
        if not d: return
        out, _ = QFileDialog.getSaveFileName(self, "Save archive", "archive.zip", "Zip archives (*.zip)")
        if not out: return
        try:
            n = 0
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                for root, _, files in os.walk(d):
                    for f in files:
                        p = os.path.join(root, f)
                        if os.path.abspath(p) != os.path.abspath(out): z.write(p, os.path.relpath(p, d)); n += 1
            self.st.setText(f"Created {Path(out).name} with {n} files")
        except Exception as ex:
            self.st.setText(f"Failed: {ex}")


class PyHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for CodeEditorApp."""
    def __init__(self, doc):
        super().__init__(doc)
        self.rules = []
        kw_fmt = QTextCharFormat(); kw_fmt.setForeground(QColor("#c678dd")); kw_fmt.setFontWeight(QFont.Bold)
        kws = ("and|as|assert|break|class|continue|def|del|elif|else|except|False|finally|for|from|global|"
               "if|import|in|is|lambda|None|nonlocal|not|or|pass|raise|return|True|try|while|with|yield")
        self.rules.append((QRegularExpression(rf"\b({kws})\b"), kw_fmt))
        fn_fmt = QTextCharFormat(); fn_fmt.setForeground(QColor("#61afef"))
        self.rules.append((QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\()"), fn_fmt))
        num_fmt = QTextCharFormat(); num_fmt.setForeground(QColor("#d19a66"))
        self.rules.append((QRegularExpression(r"\b[0-9]+(\.[0-9]+)?\b"), num_fmt))
        str_fmt = QTextCharFormat(); str_fmt.setForeground(QColor("#98c379"))
        self.rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'|\"[^\"\\]*(\\.[^\"\\]*)*\""), str_fmt))
        cm_fmt = QTextCharFormat(); cm_fmt.setForeground(QColor("#7f848e")); cm_fmt.setFontItalic(True)
        self.rules.append((QRegularExpression(r"#.*"), cm_fmt))

    def highlightBlock(self, text):
        for rx, fmt in self.rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


class CodeEditorApp(QWidget):
    """Working IDE (Visual Studio Code / Neovim): file explorer, syntax highlighting, live Python runner."""
    SAMPLE = "# Welcome to Code Studio!\ndef greet(name):\n    return f'Hello, {name}!'\n\nfor i in range(1, 4):\n    print(i, greet('Windows 12'))\n"

    def __init__(self, desk, arg=None):
        super().__init__()
        self.desk = desk
        self.folder = Path(arg).parent if arg and Path(arg).is_file() else Path.home()
        self.file = None
        v = QVBoxLayout(self); v.setContentsMargins(8, 6, 8, 8); v.setSpacing(6)
        bar = QHBoxLayout()
        for t, fn in (("Folder", self.pick_folder), ("New", self.new_file), ("Save", self.save)):
            b = QPushButton(t); b.clicked.connect(fn); bar.addWidget(b)
        run_b = QPushButton("▶ Run Python"); run_b.setProperty("kind", "accent")
        run_b.clicked.connect(self.run_code); bar.addWidget(run_b)
        bar.addStretch()
        self.lbl = QLabel("scratch.py"); self.lbl.setProperty("sub", True); bar.addWidget(self.lbl)
        v.addLayout(bar)
        sp = QSplitter(Qt.Horizontal); v.addWidget(sp, 1)
        self.tree = QListWidget(); self.tree.setMinimumWidth(160)
        self.tree.itemClicked.connect(self.open_from_list)
        sp.addWidget(self.tree)
        right = QSplitter(Qt.Vertical); sp.addWidget(right)
        self.ed = QPlainTextEdit()
        self.ed.setStyleSheet("QPlainTextEdit{font-family:'Cascadia Mono',Consolas,'DejaVu Sans Mono',monospace;font-size:13px;}")
        self.hl = PyHighlighter(self.ed.document())
        right.addWidget(self.ed)
        self.out = QPlainTextEdit(); self.out.setReadOnly(True)
        self.out.setPlaceholderText("Program output appears here...")
        self.out.setStyleSheet("QPlainTextEdit{background:rgba(0,0,0,0.35);color:#c8facc;font-family:monospace;font-size:12px;}")
        right.addWidget(self.out)
        sp.setSizes([190, 740]); right.setSizes([420, 150])
        self.load_folder(self.folder)
        if arg and Path(arg).is_file():
            self.load_file(Path(arg))
        else:
            self.ed.setPlainText(self.SAMPLE)

    def load_folder(self, pth):
        self.folder = Path(pth); self.tree.clear()
        try:
            items = sorted((x for x in self.folder.iterdir() if x.is_file() and not x.name.startswith(".")),
                           key=lambda x: x.name.lower())[:250]
            for x in items:
                it = QListWidgetItem("📄 " + x.name); it.setData(Qt.UserRole, str(x)); self.tree.addItem(it)
        except Exception as ex:
            self.out.setPlainText(str(ex))

    def pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Open Folder", str(self.folder))
        if d: self.load_folder(d)

    def open_from_list(self, it):
        self.load_file(Path(it.data(Qt.UserRole)))

    def load_file(self, pth):
        try:
            self.ed.setPlainText(pth.read_text(encoding="utf-8", errors="replace"))
            self.file = pth; self.lbl.setText(pth.name)
        except Exception as ex:
            self.out.setPlainText(f"Could not open file: {ex}")

    def new_file(self):
        self.file = None; self.ed.clear(); self.lbl.setText("untitled.py")

    def save(self):
        if not self.file:
            f, _ = QFileDialog.getSaveFileName(self, "Save File", str(self.folder / "script.py"))
            if not f: return
            self.file = Path(f)
        try:
            self.file.write_text(self.ed.toPlainText(), encoding="utf-8")
            self.lbl.setText(self.file.name + " — saved")
            self.load_folder(self.file.parent)
        except Exception as ex:
            self.out.setPlainText(f"Save failed: {ex}")

    def run_code(self):
        self.out.setPlainText("Running...\n")
        QApplication.processEvents()
        try:
            r = subprocess.run([sys.executable, "-c", self.ed.toPlainText()],
                               cwd=str(self.folder), capture_output=True, text=True, timeout=10)
            res = (r.stdout + r.stderr).strip()
            self.out.setPlainText(res or "(Finished with no output)")
        except subprocess.TimeoutExpired:
            self.out.setPlainText("Timed out after 10 seconds.")
        except Exception as ex:
            self.out.setPlainText(f"Error: {ex}")


class PaintCanvas(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.img = QImage(900, 560, QImage.Format_ARGB32)
        self.img.fill(QColor("white"))
        self.undo_stack = []
        self.drawing = False
        self.start = self.last = QPoint()
        self.setMinimumSize(400, 300)

    def push_undo(self):
        self.undo_stack.append(self.img.copy())
        if len(self.undo_stack) > 15:
            self.undo_stack.pop(0)

    def undo(self):
        if self.undo_stack:
            self.img = self.undo_stack.pop()
            self.update()

    def clear(self):
        self.push_undo(); self.img.fill(QColor("white")); self.update()

    def load_image(self, path):
        loaded = QImage(path)
        if not loaded.isNull():
            self.push_undo()
            self.img = loaded.convertToFormat(QImage.Format_ARGB32)
            self.update()

    def _to_img(self, pt):
        if self.width() <= 0 or self.height() <= 0:
            return QPoint()
        return QPoint(int(pt.x() * self.img.width() / self.width()),
                      int(pt.y() * self.img.height() / self.height()))

    def _pen(self):
        col = QColor("white") if self.app.tool == "Eraser" else self.app.color
        return QPen(col, self.app.size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.push_undo()
            self.drawing = True
            self.start = self.last = self._to_img(e.position().toPoint())
            if self.app.tool in ("Brush", "Eraser"):
                p = QPainter(self.img); p.setRenderHint(QPainter.Antialiasing); p.setPen(self._pen())
                p.drawPoint(self.start); p.end(); self.update()

    def mouseMoveEvent(self, e):
        if not self.drawing: return
        cur = self._to_img(e.position().toPoint())
        if self.app.tool in ("Brush", "Eraser"):
            p = QPainter(self.img); p.setRenderHint(QPainter.Antialiasing); p.setPen(self._pen())
            p.drawLine(self.last, cur); p.end()
        self.last = cur
        self.update()

    def mouseReleaseEvent(self, e):
        if not self.drawing: return
        cur = self._to_img(e.position().toPoint())
        if self.app.tool in ("Line", "Rect", "Circle"):
            p = QPainter(self.img); p.setRenderHint(QPainter.Antialiasing); p.setPen(self._pen())
            if self.app.tool == "Line": p.drawLine(self.start, cur)
            elif self.app.tool == "Rect": p.drawRect(QRect(self.start, cur).normalized())
            elif self.app.tool == "Circle": p.drawEllipse(QRect(self.start, cur).normalized())
            p.end()
        self.drawing = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(self.rect(), self.img)
        if self.drawing and self.app.tool in ("Line", "Rect", "Circle"):
            sx, sy = self.width() / max(1, self.img.width()), self.height() / max(1, self.img.height())
            p1 = QPoint(int(self.start.x() * sx), int(self.start.y() * sy))
            p2 = QPoint(int(self.last.x() * sx), int(self.last.y() * sy))
            p.setPen(self._pen())
            if self.app.tool == "Line": p.drawLine(p1, p2)
            elif self.app.tool == "Rect": p.drawRect(QRect(p1, p2).normalized())
            elif self.app.tool == "Circle": p.drawEllipse(QRect(p1, p2).normalized())


class PaintApp(QWidget):
    """Working image editor (GIMP / Krita / Inkscape)."""
    def __init__(self, desk, arg=None):
        super().__init__()
        self.tool = "Brush"
        self.color = QColor("#1e88e5")
        self.size = 6
        v = QVBoxLayout(self); v.setContentsMargins(8, 6, 8, 8); v.setSpacing(6)
        bar = QHBoxLayout()
        self.tool_box = QComboBox(); self.tool_box.addItems(["Brush", "Eraser", "Line", "Rect", "Circle"])
        self.tool_box.currentTextChanged.connect(lambda t: setattr(self, "tool", t))
        bar.addWidget(self.tool_box)
        for hexcol in ("#111111", "#e53935", "#1e88e5", "#43a047", "#fdd835", "#8e24aa", "#fb8c00"):
            b = QPushButton(); b.setFixedSize(24, 24)
            b.setStyleSheet(f"QPushButton{{background:{hexcol};border-radius:12px;border:1px solid #888;padding:0;}}")
            b.clicked.connect(lambda _, c=hexcol: setattr(self, "color", QColor(c))); bar.addWidget(b)
        pick = QPushButton("Color..."); pick.clicked.connect(self.pick_color); bar.addWidget(pick)
        bar.addWidget(QLabel("Size:"))
        sl = QSlider(Qt.Horizontal); sl.setRange(2, 40); sl.setValue(6); sl.setFixedWidth(90)
        sl.valueChanged.connect(lambda val: setattr(self, "size", val)); bar.addWidget(sl)
        bar.addStretch()
        self.canvas = PaintCanvas(self)
        for t, fn in (("Undo", self.canvas.undo), ("Clear", self.canvas.clear), ("Open", self.open_img), ("Save", self.save_img)):
            b = QPushButton(t); b.clicked.connect(fn); bar.addWidget(b)
        v.addLayout(bar)
        v.addWidget(self.canvas, 1)
        if arg and Path(arg).is_file():
            self.canvas.load_image(arg)

    def pick_color(self):
        c = QColorDialog.getColor(self.color, self)
        if c.isValid(): self.color = c

    def open_img(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if f: self.canvas.load_image(f)

    def save_img(self):
        f, _ = QFileDialog.getSaveFileName(self, "Save Image", "artwork.png", "PNG (*.png);;JPEG (*.jpg)")
        if f: self.canvas.img.save(f)


class MediaPlayerApp(QWidget):
    """Working video & audio player (VLC / Audacity)."""
    def __init__(self, desk, arg=None):
        super().__init__()
        self.files = []
        v = QVBoxLayout(self); v.setContentsMargins(10, 6, 10, 10); v.setSpacing(8)
        if not HAVE_MEDIA:
            lbl = QLabel("QtMultimedia is not installed in this Python environment.")
            lbl.setAlignment(Qt.AlignCenter); v.addWidget(lbl, 1); return
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.75)
        sp = QSplitter(Qt.Horizontal); v.addWidget(sp, 1)
        self.video = QVideoWidget(); self.video.setStyleSheet("background:#0b0c10;border-radius:8px;")
        self.player.setVideoOutput(self.video)
        sp.addWidget(self.video)
        self.playlist = QListWidget(); self.playlist.setMaximumWidth(230)
        self.playlist.itemDoubleClicked.connect(self.play_item)
        sp.addWidget(self.playlist)
        sp.setSizes([600, 210])
        self.seek = QSlider(Qt.Horizontal); self.seek.setRange(0, 0)
        self.seek.sliderMoved.connect(self.player.setPosition)
        v.addWidget(self.seek)
        ctrl = QHBoxLayout()
        add_b = QPushButton("Open Media"); add_b.clicked.connect(self.add_media); ctrl.addWidget(add_b)
        self.btn_play = QPushButton("▶ Play"); self.btn_play.setProperty("kind", "accent")
        self.btn_play.clicked.connect(self.toggle); ctrl.addWidget(self.btn_play)
        stop_b = QPushButton("⏹ Stop"); stop_b.clicked.connect(self.player.stop); ctrl.addWidget(stop_b)
        self.time_lbl = QLabel("00:00 / 00:00"); self.time_lbl.setProperty("sub", True); ctrl.addWidget(self.time_lbl)
        ctrl.addStretch(); ctrl.addWidget(QLabel("🔊"))
        vol = QSlider(Qt.Horizontal); vol.setRange(0, 100); vol.setValue(75); vol.setFixedWidth(90)
        vol.valueChanged.connect(lambda val: self.audio.setVolume(val / 100.0)); ctrl.addWidget(vol)
        v.addLayout(ctrl)
        self.player.positionChanged.connect(self.on_pos)
        self.player.durationChanged.connect(self.on_dur)
        if arg and Path(arg).is_file():
            self.enqueue_and_play(arg)

    def _fmt(self, ms):
        s = max(0, ms // 1000)
        return f"{s // 60:02d}:{s % 60:02d}"

    def on_dur(self, dur):
        self.seek.setRange(0, dur)
        self.time_lbl.setText(f"{self._fmt(self.player.position())} / {self._fmt(dur)}")

    def on_pos(self, pos):
        if not self.seek.isSliderDown():
            self.seek.setValue(pos)
        self.time_lbl.setText(f"{self._fmt(pos)} / {self._fmt(self.player.duration())}")

    def enqueue_and_play(self, path):
        it = QListWidgetItem("🎵 " + Path(path).name); it.setData(Qt.UserRole, path)
        self.playlist.addItem(it); self.playlist.setCurrentItem(it)
        self.player.setSource(QUrl.fromLocalFile(path)); self.player.play()
        self.btn_play.setText("⏸ Pause")

    def add_media(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "Open Audio/Video", "", "Media (*.mp4 *.mkv *.mov *.avi *.mp3 *.wav *.ogg *.flac *.m4a);;All (*.*)")
        for i, f in enumerate(fs):
            if i == 0: self.enqueue_and_play(f)
            else:
                it = QListWidgetItem("🎵 " + Path(f).name); it.setData(Qt.UserRole, f); self.playlist.addItem(it)

    def play_item(self, it):
        self.player.setSource(QUrl.fromLocalFile(it.data(Qt.UserRole))); self.player.play()
        self.btn_play.setText("⏸ Pause")

    def toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause(); self.btn_play.setText("▶ Play")
        else:
            self.player.play(); self.btn_play.setText("⏸ Pause")

    def cleanup(self):
        if HAVE_MEDIA and hasattr(self, "player"):
            self.player.stop()


class MarkdownNotesApp(QWidget):
    """Working persistent Markdown vault (Obsidian / Notion)."""
    def __init__(self, desk, arg=None):
        super().__init__()
        self.notes_dir = DATA_DIR / "notes"
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        starter = self.notes_dir / "Welcome.md"
        if not list(self.notes_dir.glob("*.md")):
            starter.write_text("# Welcome to your Vault\n\nWrite **Markdown** on the left and see it render live on the right.\n\n- Saved automatically to `~/.windows12_py/notes/`\n- Create new notes or search them anytime.\n", encoding="utf-8")
        self.current = None
        v = QVBoxLayout(self); v.setContentsMargins(8, 6, 8, 8); v.setSpacing(6)
        bar = QHBoxLayout()
        self.q = QLineEdit(); self.q.setPlaceholderText("🔍 Filter notes..."); self.q.textChanged.connect(self.refresh_list)
        bar.addWidget(self.q, 1)
        nb = QPushButton("+ New Note"); nb.setProperty("kind", "accent"); nb.clicked.connect(self.new_note); bar.addWidget(nb)
        db = QPushButton("Delete"); db.clicked.connect(self.del_note); bar.addWidget(db)
        v.addLayout(bar)
        sp = QSplitter(Qt.Horizontal); v.addWidget(sp, 1)
        self.lst = QListWidget(); self.lst.currentItemChanged.connect(self.select_note); sp.addWidget(self.lst)
        self.ed = QPlainTextEdit(); self.ed.textChanged.connect(self.on_edit); sp.addWidget(self.ed)
        self.prev = QTextBrowser(); sp.addWidget(self.prev)
        sp.setSizes([180, 360, 360])
        self.refresh_list()
        if self.lst.count(): self.lst.setCurrentRow(0)

    def refresh_list(self):
        filt = self.q.text().lower().strip()
        self.lst.clear()
        for p in sorted(self.notes_dir.glob("*.md"), key=lambda x: x.name.lower()):
            if not filt or filt in p.stem.lower():
                it = QListWidgetItem("📝 " + p.stem); it.setData(Qt.UserRole, str(p)); self.lst.addItem(it)

    def select_note(self, cur, _prev=None):
        if not cur: return
        self.current = Path(cur.data(Qt.UserRole))
        txt = self.current.read_text(encoding="utf-8", errors="replace")
        self.ed.blockSignals(True); self.ed.setPlainText(txt); self.ed.blockSignals(False)
        self.prev.setMarkdown(txt)

    def on_edit(self):
        txt = self.ed.toPlainText()
        self.prev.setMarkdown(txt)
        if self.current:
            try: self.current.write_text(txt, encoding="utf-8")
            except Exception: pass

    def new_note(self):
        name, ok = QInputDialog.getText(self, "New Note", "Note title:")
        if ok and name.strip():
            clean = "".join(c for c in name.strip() if c.isalnum() or c in " -_")
            if not clean: return
            p = self.notes_dir / f"{clean}.md"
            if not p.exists(): p.write_text(f"# {clean}\n\n", encoding="utf-8")
            self.refresh_list()
            for i in range(self.lst.count()):
                if self.lst.item(i).data(Qt.UserRole) == str(p):
                    self.lst.setCurrentRow(i); break

    def del_note(self):
        if self.current and self.current.exists():
            self.current.unlink(); self.current = None; self.ed.clear(); self.prev.clear(); self.refresh_list()


class WordProcessorApp(QWidget):
    """Working rich-text word processor with PDF export (LibreOffice)."""
    def __init__(self, desk, arg=None):
        super().__init__()
        self.file = None
        v = QVBoxLayout(self); v.setContentsMargins(8, 6, 8, 8); v.setSpacing(6)
        bar = QHBoxLayout()
        for t, fn in (("Open", self.open_doc), ("Save", self.save_doc), ("Export PDF", self.export_pdf)):
            b = QPushButton(t); b.clicked.connect(fn); bar.addWidget(b)
        b_bold = QPushButton("B"); b_bold.setFixedWidth(34); b_bold.clicked.connect(self.toggle_bold); bar.addWidget(b_bold)
        b_it = QPushButton("I"); b_it.setFixedWidth(34); b_it.clicked.connect(lambda: self.ed.setFontItalic(not self.ed.fontItalic())); bar.addWidget(b_it)
        b_ul = QPushButton("U"); b_ul.setFixedWidth(34); b_ul.clicked.connect(lambda: self.ed.setFontUnderline(not self.ed.fontUnderline())); bar.addWidget(b_ul)
        sz = QComboBox(); sz.addItems(["11", "13", "16", "20", "26", "32"]); sz.setCurrentText("13")
        sz.currentTextChanged.connect(lambda s: self.ed.setFontPointSize(float(s))); bar.addWidget(sz)
        col = QPushButton("Color"); col.clicked.connect(self.pick_color); bar.addWidget(col)
        for sym, al in (("⬅", Qt.AlignLeft), ("⬌", Qt.AlignCenter), ("➡", Qt.AlignRight)):
            b = QPushButton(sym); b.setFixedWidth(34); b.clicked.connect(lambda _, a=al: self.ed.setAlignment(a)); bar.addWidget(b)
        bar.addStretch(); self.st = QLabel("Document 1"); self.st.setProperty("sub", True); bar.addWidget(self.st)
        v.addLayout(bar)
        self.ed = QTextEdit(); self.ed.setFontPointSize(13)
        self.ed.setHtml("<h2>Untitled Document</h2><p>Start typing your formatted document here, then save as HTML or export directly to PDF.</p>")
        v.addWidget(self.ed, 1)

    def toggle_bold(self):
        w = QFont.Normal if self.ed.fontWeight() >= QFont.Bold else QFont.Bold
        self.ed.setFontWeight(w)

    def pick_color(self):
        c = QColorDialog.getColor(self.ed.textColor(), self)
        if c.isValid(): self.ed.setTextColor(c)

    def open_doc(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open Document", "", "Documents (*.html *.htm *.txt);;All (*.*)")
        if not f: return
        txt = Path(f).read_text(encoding="utf-8", errors="replace")
        if f.lower().endswith((".html", ".htm")): self.ed.setHtml(txt)
        else: self.ed.setPlainText(txt)
        self.file = f; self.st.setText(Path(f).name)

    def save_doc(self):
        f, _ = QFileDialog.getSaveFileName(self, "Save Document", self.file or "document.html", "HTML (*.html);;Text (*.txt)")
        if not f: return
        Path(f).write_text(self.ed.toPlainText() if f.lower().endswith(".txt") else self.ed.toHtml(), encoding="utf-8")
        self.file = f; self.st.setText(Path(f).name + " — saved")

    def export_pdf(self):
        f, _ = QFileDialog.getSaveFileName(self, "Export PDF", "document.pdf", "PDF (*.pdf)")
        if not f: return
        try:
            writer = QPdfWriter(f)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            doc = self.ed.document()
            fn = getattr(doc, "print_", getattr(doc, "print", None))
            if fn: fn(writer)
            self.st.setText(f"Exported {Path(f).name}")
        except Exception as ex:
            self.st.setText(f"PDF export failed: {ex}")


class Studio3DApp(QWidget):
    """Interactive 3D wireframe & shaded mesh studio (Blender)."""
    SHAPES = {
        "Cube": (
            [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)],
            [(0,1,2,3),(4,5,6,7),(0,1,5,4),(2,3,7,6),(1,2,6,5),(0,3,7,4)]
        ),
        "Pyramid": (
            [(0,-1.3,0),(-1,1,-1),(1,1,-1),(1,1,1),(-1,1,1)],
            [(1,2,3,4),(0,1,2),(0,2,3),(0,3,4),(0,4,1)]
        ),
        "Octahedron": (
            [(0,-1.4,0),(0,1.4,0),(-1.1,0,0),(1.1,0,0),(0,0,-1.1),(0,0,1.1)],
            [(0,2,4),(0,4,3),(0,3,5),(0,5,2),(1,4,2),(1,3,4),(1,5,3),(1,2,5)]
        ),
    }

    def __init__(self, desk, arg=None):
        super().__init__()
        self.shape = "Cube"; self.rx = 0.5; self.ry = 0.6; self.zoom = 1.0
        self.wireframe = False; self.spin = True; self.drag = None
        v = QVBoxLayout(self); v.setContentsMargins(8, 6, 8, 8); v.setSpacing(6)
        bar = QHBoxLayout()
        cb = QComboBox(); cb.addItems(list(self.SHAPES.keys()))
        cb.currentTextChanged.connect(lambda s: (setattr(self, "shape", s), self.update()))
        bar.addWidget(QLabel("Mesh:")); bar.addWidget(cb)
        wf = QPushButton("Wireframe / Solid"); wf.clicked.connect(lambda: (setattr(self, "wireframe", not self.wireframe), self.update())); bar.addWidget(wf)
        sp = QPushButton("Toggle Spin"); sp.clicked.connect(lambda: setattr(self, "spin", not self.spin)); bar.addWidget(sp)
        bar.addWidget(QLabel("Zoom:"))
        sl = QSlider(Qt.Horizontal); sl.setRange(5, 22); sl.setValue(10); sl.setFixedWidth(100)
        sl.valueChanged.connect(lambda z: (setattr(self, "zoom", z / 10.0), self.update())); bar.addWidget(sl)
        bar.addStretch(); bar.addWidget(QLabel("Drag viewport to orbit"))
        v.addLayout(bar)
        self.view = QWidget(); self.view.setMinimumHeight(420); v.addWidget(self.view, 1)
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(25)

    def tick(self):
        if self.spin and self.drag is None:
            self.ry += 0.025; self.rx += 0.008; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.drag = e.position()

    def mouseMoveEvent(self, e):
        if self.drag is not None:
            d = e.position() - self.drag; self.drag = e.position()
            self.ry += d.x() * 0.012; self.rx += d.y() * 0.012; self.update()

    def mouseReleaseEvent(self, e):
        self.drag = None

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.view.geometry()
        p.fillRect(r, QColor("#141720"))
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        for i in range(-6, 7):
            x = r.center().x() + i * 32
            p.drawLine(x, r.top() + 20, x, r.bottom() - 20)
        verts, faces = self.SHAPES[self.shape]
        cx, cy = r.center().x(), r.center().y()
        scale = min(r.width(), r.height()) * 0.34 * self.zoom
        cosy, siny = math.cos(self.ry), math.sin(self.ry)
        cosx, sinx = math.cos(self.rx), math.sin(self.rx)
        tr = []
        for x, y, z in verts:
            x1, z1 = x * cosy - z * siny, x * siny + z * cosy
            y2, z2 = y * cosx - z1 * sinx, y * sinx + z1 * cosx
            tr.append((x1, y2, z2))
        proj = [(cx + x * scale / (z + 4.5), cy + y * scale / (z + 4.5)) for x, y, z in tr]
        ordered = sorted(faces, key=lambda f: sum(tr[i][2] for i in f) / len(f), reverse=True)
        base = QColor(S.accent)
        for f in ordered:
            poly = QPolygonF([QPointF(*proj[i]) for i in f])
            v0, v1, v2 = tr[f[0]], tr[f[1]], tr[f[2]]
            ax, ay, az = v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2]
            bx, by, bz = v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2]
            nx, ny, nz = ay*bz - az*by, az*bx - ax*bz, ax*by - ay*bx
            ln = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
            shade = int(95 + 145 * abs(nz / ln))
            if self.wireframe:
                p.setBrush(Qt.NoBrush); p.setPen(QPen(base, 2))
            else:
                col = QColor(min(255, base.red() * shade // 220),
                             min(255, base.green() * shade // 220),
                             min(255, base.blue() * shade // 220), 220)
                p.setBrush(col); p.setPen(QPen(QColor(255, 255, 255, 110), 1.3))
            p.drawPolygon(poly)

    def cleanup(self):
        self.timer.stop()


class SnapshotApp(QWidget):
    """Working desktop & screen capture studio (OBS Studio)."""
    def __init__(self, desk, arg=None):
        super().__init__()
        self.desk = desk; self.pm = None
        v = QVBoxLayout(self); v.setContentsMargins(10, 6, 10, 10); v.setSpacing(8)
        bar = QHBoxLayout()
        b1 = QPushButton("📸 Capture Shell"); b1.setProperty("kind", "accent"); b1.clicked.connect(self.cap_shell); bar.addWidget(b1)
        b2 = QPushButton("🖥️ Capture Full Screen"); b2.clicked.connect(self.cap_screen); bar.addWidget(b2)
        b3 = QPushButton("⏱️ 3s Timer"); b3.clicked.connect(self.cap_delayed); bar.addWidget(b3)
        b4 = QPushButton("💾 Save PNG"); b4.clicked.connect(self.save_png); bar.addWidget(b4)
        bar.addStretch(); self.st = QLabel("Ready to capture"); self.st.setProperty("sub", True); bar.addWidget(self.st)
        v.addLayout(bar)
        self.prev = QLabel("Click a capture button above to take a real screenshot.")
        self.prev.setAlignment(Qt.AlignCenter)
        self.prev.setStyleSheet("background:rgba(0,0,0,0.3);border-radius:10px;")
        v.addWidget(self.prev, 1)

    def _show(self, pm, label):
        self.pm = pm
        sz = self.prev.size()
        if sz.width() > 20 and sz.height() > 20:
            self.prev.setPixmap(pm.scaled(sz, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.st.setText(f"{label} ({pm.width()}×{pm.height()})")

    def cap_shell(self):
        self._show(self.desk.grab(), "Captured shell")

    def cap_screen(self):
        scr = QApplication.primaryScreen()
        if scr: self._show(scr.grabWindow(0), "Captured monitor")

    def cap_delayed(self):
        self.st.setText("Capturing in 3 seconds...")
        QTimer.singleShot(3000, self.cap_shell)

    def save_png(self):
        if not self.pm: self.st.setText("Take a capture first."); return
        f, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "capture.png", "PNG (*.png)")
        if f: self.pm.save(f); self.st.setText(f"Saved {Path(f).name}")


class VaultApp(QWidget):
    """Working local password manager + generator (Bitwarden)."""
    def __init__(self, desk, arg=None):
        super().__init__()
        self.vfile = DATA_DIR / "vault.json"
        self.entries = self._load()
        self.reveal = False
        v = QVBoxLayout(self); v.setContentsMargins(10, 6, 10, 10); v.setSpacing(8)
        bar = QHBoxLayout()
        self.q = QLineEdit(); self.q.setPlaceholderText("🔍 Search vault..."); self.q.textChanged.connect(self.refresh)
        bar.addWidget(self.q, 1)
        gen = QPushButton("⚡ Generate Password"); gen.clicked.connect(self.gen_pw); bar.addWidget(gen)
        add = QPushButton("+ Add Login"); add.setProperty("kind", "accent"); add.clicked.connect(self.add_entry); bar.addWidget(add)
        v.addLayout(bar)
        self.lst = QListWidget(); v.addWidget(self.lst, 1)
        act = QHBoxLayout()
        for t, fn in (("Copy Password", self.copy_pw), ("Show / Hide", self.toggle_show), ("Delete", self.del_entry)):
            b = QPushButton(t); b.clicked.connect(fn); act.addWidget(b)
        act.addStretch(); self.st = QLabel("Stored locally in ~/.windows12_py/vault.json"); self.st.setProperty("sub", True); act.addWidget(self.st)
        v.addLayout(act)
        self.refresh()

    def _load(self):
        try:
            raw = base64.b64decode(self.vfile.read_text(encoding="utf-8").encode()).decode()
            return json.loads(raw)
        except Exception:
            return [{"site": "Example Account", "user": "you@example.com", "pw": "Demo-Pass-9421!"}]

    def _save(self):
        DATA_DIR.mkdir(exist_ok=True)
        enc = base64.b64encode(json.dumps(self.entries).encode()).decode()
        self.vfile.write_text(enc, encoding="utf-8")

    def refresh(self):
        filt = self.q.text().lower().strip()
        self.lst.clear()
        for idx, e in enumerate(self.entries):
            if not filt or filt in (e["site"] + " " + e["user"]).lower():
                pw = e["pw"] if self.reveal else "•" * min(12, max(6, len(e["pw"])))
                it = QListWidgetItem(f"🔑  {e['site']}   |   {e['user']}   |   {pw}")
                it.setData(Qt.UserRole, idx); self.lst.addItem(it)

    def add_entry(self):
        site, ok1 = QInputDialog.getText(self, "Add Login", "Site / App name:")
        if not ok1 or not site.strip(): return
        user, ok2 = QInputDialog.getText(self, "Add Login", "Username / Email:")
        if not ok2: return
        pw, ok3 = QInputDialog.getText(self, "Add Login", "Password (leave blank to auto-generate):")
        if not ok3: return
        if not pw: pw = self._make_pw()
        self.entries.append({"site": site.strip(), "user": user.strip(), "pw": pw})
        self._save(); self.refresh(); self.st.setText(f"Saved {site.strip()}")

    def _make_pw(self):
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%&*"
        return "".join(secrets.choice(chars) for _ in range(16))

    def gen_pw(self):
        pw = self._make_pw()
        QApplication.clipboard().setText(pw)
        self.st.setText(f"Copied generated password: {pw}")

    def copy_pw(self):
        it = self.lst.currentItem()
        if not it: return
        e = self.entries[it.data(Qt.UserRole)]
        QApplication.clipboard().setText(e["pw"])
        self.st.setText(f"Copied password for {e['site']}")

    def toggle_show(self):
        self.reveal = not self.reveal; self.refresh()

    def del_entry(self):
        it = self.lst.currentItem()
        if not it: return
        self.entries.pop(it.data(Qt.UserRole)); self._save(); self.refresh()


class FarmGame(QWidget):
    """Playable cozy farming game (Stardew Valley / Terraria)."""
    COLS, ROWS = 8, 5

    def __init__(self, desk, arg=None):
        super().__init__()
        self.gold = 60; self.day = 1; self.harvested = 0; self.tool = "Hoe"
        self.grid_data = [[[0, False] for _ in range(self.COLS)] for _ in range(self.ROWS)]
        v = QVBoxLayout(self); v.setContentsMargins(10, 6, 10, 10); v.setSpacing(8)
        bar = QHBoxLayout()
        self.tool_btns = {}
        for t in ("Hoe", "Seeds ($10)", "Water", "Harvest"):
            b = QPushButton(t); b.clicked.connect(lambda _, t=t: self.set_tool(t))
            self.tool_btns[t] = b; bar.addWidget(b)
        slp = QPushButton("🌙 Next Day"); slp.clicked.connect(self.next_day); bar.addWidget(slp)
        bar.addStretch()
        self.hud = QLabel(); bar.addWidget(self.hud)
        v.addLayout(bar)
        self.board = QWidget(); self.board.setMinimumHeight(380)
        self.board.mousePressEvent = self.click_plot
        v.addWidget(self.board, 1)
        self.set_tool("Hoe")
        self.timer = QTimer(self); self.timer.timeout.connect(self.grow_tick); self.timer.start(1400)
        self.update_hud()

    def set_tool(self, t):
        self.tool = t
        for k, b in self.tool_btns.items():
            b.setProperty("kind", "accent" if k == t else "flat")
            b.style().unpolish(b); b.style().polish(b)

    def update_hud(self):
        self.hud.setText(f"<b>Day {self.day}  ·  💰 ${self.gold}  ·  🌾 Harvested: {self.harvested}</b>")

    def click_plot(self, e):
        cw, ch = self.board.width() / self.COLS, self.board.height() / self.ROWS
        c, r = int(e.position().x() // cw), int(e.position().y() // ch)
        if not (0 <= r < self.ROWS and 0 <= c < self.COLS): return
        cell = self.grid_data[r][c]
        if self.tool == "Hoe" and cell[0] == 0:
            cell[0] = 1
        elif self.tool.startswith("Seeds") and cell[0] == 1 and self.gold >= 10:
            self.gold -= 10; cell[0] = 2
        elif self.tool == "Water" and cell[0] in (1, 2, 3):
            cell[1] = True
        elif self.tool == "Harvest" and cell[0] == 4:
            self.gold += 28; self.harvested += 1; cell[0] = 1; cell[1] = False
        self.update_hud(); self.update()

    def grow_tick(self):
        changed = False
        for row in self.grid_data:
            for cell in row:
                if cell[0] in (2, 3) and cell[1] and random.random() < 0.45:
                    cell[0] += 1; changed = True
        if changed: self.update()

    def next_day(self):
        self.day += 1
        for row in self.grid_data:
            for cell in row:
                if cell[0] in (2, 3):
                    cell[0] = min(4, cell[0] + (2 if cell[1] else 1))
                cell[1] = False
        self.update_hud(); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        rect = self.board.geometry()
        cw, ch = rect.width() / self.COLS, rect.height() / self.ROWS
        colors = {0: "#4caf50", 1: "#795548", 2: "#6d4c41", 3: "#5d4037", 4: "#5d4037"}
        icons = {0: "", 1: "", 2: "🌱", 3: "🌿", 4: "🌾"}
        f = QFont(); f.setPixelSize(int(min(cw, ch) * 0.48)); p.setFont(f)
        for r in range(self.ROWS):
            for c in range(self.COLS):
                st, wet = self.grid_data[r][c]
                cell_r = QRectF(rect.x() + c * cw + 3, rect.y() + r * ch + 3, cw - 6, ch - 6)
                col = QColor(colors[st]).darker(135 if wet else 100)
                p.setBrush(col); p.setPen(QPen(QColor(255, 255, 255, 45), 1))
                p.drawRoundedRect(cell_r, 8, 8)
                if icons[st]:
                    p.drawText(cell_r, Qt.AlignCenter, icons[st])
                if wet:
                    p.setBrush(QColor("#29b6f6")); p.setPen(Qt.NoPen)
                    p.drawEllipse(QPointF(cell_r.right() - 10, cell_r.top() + 10), 4, 4)

    def cleanup(self):
        self.timer.stop()


class DungeonGame(QWidget):
    """Playable real-time arena survival game (Hades / Among Us / Roblox)."""
    def __init__(self, desk, arg=None):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.keys = set()
        self.reset()
        self.timer = QTimer(self); self.timer.timeout.connect(self.step); self.timer.start(16)

    def reset(self):
        self.px, self.py = 360.0, 260.0
        self.hp = 100; self.score = 0; self.wave = 1; self.inv = 0; self.slash = 0
        self.face = (1.0, 0.0)
        self.enemies = []
        self.spawn_cd = 30

    def keyPressEvent(self, e):
        self.keys.add(e.key())
        if e.key() == Qt.Key_Space and self.hp > 0:
            self.attack()
        elif e.key() == Qt.Key_R and self.hp <= 0:
            self.reset()

    def keyReleaseEvent(self, e):
        self.keys.discard(e.key())

    def mousePressEvent(self, e):
        self.setFocus()
        if self.hp <= 0: self.reset(); return
        dx, dy = e.position().x() - self.px, e.position().y() - self.py
        d = math.hypot(dx, dy) or 1.0
        self.face = (dx / d, dy / d)
        self.attack()

    def attack(self):
        self.slash = 10
        kept = []
        for ex, ey, spd in self.enemies:
            if math.hypot(ex - self.px, ey - self.py) < 78:
                self.score += 10
            else:
                kept.append([ex, ey, spd])
        self.enemies = kept
        self.wave = 1 + self.score // 100

    def step(self):
        if self.hp <= 0:
            self.update(); return
        dx = (Qt.Key_D in self.keys or Qt.Key_Right in self.keys) - (Qt.Key_A in self.keys or Qt.Key_Left in self.keys)
        dy = (Qt.Key_S in self.keys or Qt.Key_Down in self.keys) - (Qt.Key_W in self.keys or Qt.Key_Up in self.keys)
        if dx or dy:
            ln = math.hypot(dx, dy); dx /= ln; dy /= ln
            self.face = (dx, dy)
            self.px = max(20, min(self.width() - 20, self.px + dx * 4.4))
            self.py = max(44, min(self.height() - 20, self.py + dy * 4.4))
        self.slash = max(0, self.slash - 1)
        self.inv = max(0, self.inv - 1)
        self.spawn_cd -= 1
        if self.spawn_cd <= 0 and len(self.enemies) < 5 + self.wave * 2:
            side = random.choice(["l", "r", "t", "b"])
            x = 15 if side == "l" else (self.width() - 15 if side == "r" else random.randint(20, max(30, self.width() - 20)))
            y = 45 if side == "t" else (self.height() - 15 if side == "b" else random.randint(45, max(60, self.height() - 20)))
            self.enemies.append([float(x), float(y), 1.5 + self.wave * 0.18 + random.random() * 0.5])
            self.spawn_cd = max(18, 62 - self.wave * 4)
        for en in self.enemies:
            vx, vy = self.px - en[0], self.py - en[1]
            d = math.hypot(vx, vy) or 1.0
            en[0] += vx / d * en[2]; en[1] += vy / d * en[2]
            if d < 24 and self.inv == 0:
                self.hp = max(0, self.hp - 15); self.inv = 32
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#15131c"))
        p.setPen(QColor("white"))
        p.drawText(14, 24, f"HP: {self.hp}   ·   Score: {self.score}   ·   Wave: {self.wave}   |   WASD Move · Space/Click Slash")
        p.setBrush(QColor("#333")); p.setPen(Qt.NoPen); p.drawRoundedRect(14, 30, 140, 8, 4, 4)
        p.setBrush(QColor("#ef5350")); p.drawRoundedRect(14, 30, int(1.4 * self.hp), 8, 4, 4)
        if self.slash > 0:
            p.setBrush(QColor(76, 194, 255, 75)); p.setPen(QPen(QColor("#4cc2ff"), 2))
            p.drawEllipse(QPointF(self.px, self.py), 74, 74)
        p.setBrush(QColor("#ffffff") if (self.inv // 4) % 2 else QColor("#4cc2ff")); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(self.px, self.py), 14, 14)
        for ex, ey, _ in self.enemies:
            p.setBrush(QColor("#ff5252")); p.drawEllipse(QPointF(ex, ey), 12, 12)
        if self.hp <= 0:
            p.fillRect(self.rect(), QColor(0, 0, 0, 160))
            p.setPen(QColor("white")); f = QFont(); f.setPixelSize(28); f.setBold(True); p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, f"GAME OVER\nScore: {self.score}\nClick or press R to retry")

    def cleanup(self):
        self.timer.stop()


class ClimberGame(QWidget):
    """Playable mountain platformer (Celeste)."""
    def __init__(self, desk, arg=None):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.keys = set()
        self.reset()
        self.timer = QTimer(self); self.timer.timeout.connect(self.step); self.timer.start(16)

    def reset(self):
        self.x, self.y, self.vx, self.vy = 320.0, 420.0, 0.0, 0.0
        self.cam_y = 0.0; self.on_ground = False; self.can_dash = True
        self.berries_got = 0; self.best_h = 0; self.dead = False
        self.plats = [(40, 460, 620)]
        self.berries = []
        y = 390
        for _ in range(30):
            px = random.randint(40, 520); pw = random.randint(90, 150)
            self.plats.append((px, y, pw))
            if random.random() < 0.45:
                self.berries.append([px + pw / 2, y - 20, False])
            y -= random.randint(68, 92)

    def keyPressEvent(self, e):
        self.keys.add(e.key())
        if e.key() in (Qt.Key_Space, Qt.Key_W, Qt.Key_Up) and self.on_ground:
            self.vy = -12.8; self.on_ground = False
        elif e.key() == Qt.Key_Shift and self.can_dash:
            self.vy = -10.5; self.can_dash = False
        elif e.key() == Qt.Key_R and self.dead:
            self.reset()

    def keyReleaseEvent(self, e):
        self.keys.discard(e.key())

    def mousePressEvent(self, e):
        self.setFocus()
        if self.dead: self.reset()

    def step(self):
        if self.dead: self.update(); return
        mv = (Qt.Key_D in self.keys or Qt.Key_Right in self.keys) - (Qt.Key_A in self.keys or Qt.Key_Left in self.keys)
        self.vx = mv * 5.2
        self.x = (self.x + self.vx) % max(400, self.width())
        prev_y = self.y
        self.vy = min(14.0, self.vy + 0.52)
        self.y += self.vy
        self.on_ground = False
        if self.vy >= 0:
            for px, py, pw in self.plats:
                if px - 10 <= self.x <= px + pw + 10 and prev_y + 14 <= py + 4 and self.y + 14 >= py:
                    self.y = py - 14; self.vy = 0; self.on_ground = True; self.can_dash = True; break
        for b in self.berries:
            if not b[2] and math.hypot(self.x - b[0], self.y - b[1]) < 22:
                b[2] = True; self.berries_got += 1
        top_plat = min(p[1] for p in self.plats)
        while top_plat > self.cam_y - 300:
            top_plat -= random.randint(68, 92)
            px = random.randint(40, max(120, self.width() - 160)); pw = random.randint(90, 145)
            self.plats.append((px, top_plat, pw))
            if random.random() < 0.45: self.berries.append([px + pw / 2, top_plat - 20, False])
        if self.y - self.cam_y < self.height() * 0.4:
            self.cam_y = self.y - self.height() * 0.4
        self.best_h = max(self.best_h, int((446 - self.y) // 10))
        if self.y - self.cam_y > self.height() + 40:
            self.dead = True
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#121a3a")); g.setColorAt(1, QColor("#2c1e4a"))
        p.fillRect(self.rect(), g)
        p.setPen(Qt.NoPen)
        for px, py, pw in self.plats:
            sy = py - self.cam_y
            if -20 <= sy <= self.height() + 20:
                p.setBrush(QColor("#80cbc4"))
                p.drawRoundedRect(QRectF(px, sy, pw, 12), 5, 5)
        f = QFont(); f.setPixelSize(18); p.setFont(f)
        for bx, by, got in self.berries:
            sy = by - self.cam_y
            if not got and -20 <= sy <= self.height() + 20:
                p.drawText(QRectF(bx - 12, sy - 12, 24, 24), Qt.AlignCenter, "🍓")
        p.setBrush(QColor("#ff4081" if self.can_dash else "#40c4ff"))
        p.drawRoundedRect(QRectF(self.x - 11, self.y - self.cam_y - 14, 22, 28), 6, 6)
        p.setPen(QColor("white")); f.setPixelSize(13); p.setFont(f)
        score = self.best_h + self.berries_got * 50
        p.drawText(14, 24, f"Height: {self.best_h}m  ·  🍓 {self.berries_got}  ·  Score: {score}  |  A/D Move · Space Jump · Shift Dash")
        if self.dead:
            p.fillRect(self.rect(), QColor(0, 0, 0, 165))
            f.setPixelSize(26); f.setBold(True); p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, f"Fell off the mountain!\nScore: {score}\nClick or press R to climb again")

    def cleanup(self):
        self.timer.stop()


# ── App launch mapping ──
NATIVE = {"VLC": ["vlc"], "Visual Studio Code": ["code"], "Firefox": ["firefox"], "OBS Studio": ["obs"],
          "GIMP": ["gimp"], "Blender": ["blender"], "Krita": ["krita"], "Inkscape": ["inkscape"],
          "LibreOffice": ["libreoffice", "soffice"], "Audacity": ["audacity"], "Thunderbird": ["thunderbird"],
          "Docker Desktop": ["docker-desktop"], "Neovim": ["nvim"], "Steam": ["steam"], "Discord": ["discord"],
          "Telegram": ["telegram-desktop", "Telegram"], "Signal": ["signal-desktop"], "Obsidian": ["obsidian"],
          "Slack": ["slack"], "Zoom": ["zoom"], "Spotify": ["spotify"], "Bitwarden": ["bitwarden"],
          "7-Zip": ["7zFM", "7zG"], "Terraria": ["Terraria"], "Stardew Valley": ["StardewValley"]}

WEB = {"Spotify": "https://open.spotify.com", "Discord": "https://discord.com/app",
       "Telegram": "https://web.telegram.org", "WhatsApp": "https://web.whatsapp.com",
       "Zoom": "https://app.zoom.us", "Slack": "https://app.slack.com", "Kindle": "https://read.amazon.com",
       "Netflix": "https://www.netflix.com", "Duolingo": "https://www.duolingo.com",
       "Wikipedia": "https://www.wikipedia.org",
       "uBlock Origin": "https://chromewebstore.google.com/detail/cjpalhdlnbpafiamejdnhcphjbkeiagm",
       "Firefox": "https://www.mozilla.org/firefox/new/", "Thunderbird": "https://www.thunderbird.net"}

BUILTIN_TOOLS = {
    "Visual Studio Code": (CodeEditorApp, (960, 620)),
    "Neovim":             (CodeEditorApp, (960, 620)),
    "GIMP":               (PaintApp, (920, 620)),
    "Krita":              (PaintApp, (920, 620)),
    "Inkscape":           (PaintApp, (920, 620)),
    "VLC":                (MediaPlayerApp, (840, 540)),
    "Audacity":           (MediaPlayerApp, (840, 540)),
    "Obsidian":           (MarkdownNotesApp, (940, 580)),
    "Notion":             (MarkdownNotesApp, (940, 580)),
    "LibreOffice":        (WordProcessorApp, (920, 600)),
    "Blender":            (Studio3DApp, (820, 580)),
    "OBS Studio":         (SnapshotApp, (820, 560)),
    "Bitwarden":          (VaultApp, (760, 520)),
    "7-Zip":              (ZipTool, (620, 420)),
    "Python 3":           (PyConsole, (760, 440)),
    "Git":                (Terminal, (760, 440)),
    "Stardew Valley":     (FarmGame, (760, 540)),
    "Terraria":           (FarmGame, (760, 540)),
    "Hades":              (DungeonGame, (760, 560)),
    "Among Us":           (DungeonGame, (760, 560)),
    "Roblox":             (DungeonGame, (760, 560)),
    "Celeste":            (ClimberGame, (720, 560)),
}


def native_launch(name):
    """Start the real program if it exists on this computer."""
    for exe in NATIVE.get(name, []):
        try:
            path = shutil.which(exe)
            if path:
                subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return True
        except Exception:
            pass
    if sys.platform == "darwin":
        try:
            if subprocess.run(["open", "-a", name], capture_output=True).returncode == 0: return True
        except Exception:
            pass
    return False


class InstalledApp(QWidget):
    """Fallback window for apps with no local binary, built-in app, or web version."""
    def __init__(self, desk, item):
        super().__init__()
        v = QVBoxLayout(self); v.setAlignment(Qt.AlignCenter); v.setSpacing(8)
        ic = QLabel(); ic.setPixmap(tile(item["emoji"], item["color"], 110)); ic.setAlignment(Qt.AlignCenter); v.addWidget(ic)
        n = QLabel(f"<span style='font-size:24px;font-weight:600'>{item['name']}</span>"); n.setAlignment(Qt.AlignCenter); v.addWidget(n)
        for t in (item["dev"], item["desc"], f"Installed from {S.installed.get(item['name'], '—')}"):
            l = QLabel(t); l.setProperty("sub", True); l.setAlignment(Qt.AlignCenter); v.addWidget(l)
        note = QLabel("No native copy was found on this computer.")
        note.setProperty("sub", True); note.setAlignment(Qt.AlignCenter); note.setWordWrap(True)
        v.addSpacing(14); v.addWidget(note)
        b = QPushButton("Find the real installer"); b.setProperty("kind", "accent")
        b.clicked.connect(lambda: webbrowser.open("https://www.bing.com/search?q=" + quote(item["name"] + " download")))
        v.addWidget(b, 0, Qt.AlignHCenter)


# ───────────────────────────── universal store ─────────────────────────────
class AppCard(QFrame):
    def __init__(self, store, item):
        super().__init__()
        self.setObjectName("card"); self.store, self.item = store, item
        self.setMinimumHeight(122)
        h = QHBoxLayout(self); h.setContentsMargins(14, 12, 14, 12); h.setSpacing(14)
        ic = QLabel(); ic.setPixmap(tile(item["emoji"], item["color"], 58)); ic.setFixedSize(58, 58); h.addWidget(ic, 0, Qt.AlignTop)
        mid = QVBoxLayout(); mid.setSpacing(2); h.addLayout(mid, 1)
        badge = "  ⚡" if item["name"] in BUILTIN_TOOLS else ""
        mid.addWidget(QLabel(f"<b style='font-size:14px'>{item['name']}{badge}</b>"))
        d = QLabel(f"{item['dev']} · {item['cat']} · ★ {item['rating']}"); d.setProperty("sub", True); mid.addWidget(d)
        ds = QLabel(item["desc"]); ds.setWordWrap(True); mid.addWidget(ds)
        shown = item["sources"][:4]
        more = len(item["sources"]) - len(shown)
        s = QLabel("Available on: " + " · ".join(shown) + (f" +{more}" if more else ""))
        s.setProperty("sub", True); s.setWordWrap(True); s.setStyleSheet("font-size:11px;"); mid.addWidget(s)
        col = QVBoxLayout(); h.addLayout(col); col.addStretch()
        self.btn = QPushButton(); self.btn.setFixedWidth(92); col.addWidget(self.btn)
        if item["name"] in S.installed:
            self.btn.setText("Open"); self.btn.setProperty("kind", "accent")
            self.btn.clicked.connect(lambda: store.desk.launch_installed(item))
            u = QPushButton("Uninstall"); u.setFixedWidth(92); u.clicked.connect(lambda: store.uninstall(item)); col.addWidget(u)
        else:
            self.btn.setText("Get"); self.btn.setProperty("kind", "accent")
            self.btn.clicked.connect(self.install)
        col.addStretch()

    def install(self):
        srcs = self.item["sources"]
        if len(srcs) > 1:
            m = QMenu(self)
            for sname in srcs:
                m.addAction(f"Install from {sname}").setData(sname)
            act = m.exec(QCursor.pos())
            if not act: return
            src = act.data()
        else:
            src = srcs[0]
        self.btn.setEnabled(False); prog = [0]
        t = QTimer(self)

        def tick():
            prog[0] += 10
            if prog[0] >= 100:
                t.stop(); self.store.finish_install(self.item, src)
            else:
                self.btn.setText(f"{prog[0]}%")
        t.timeout.connect(tick); t.start(50)


class Store(QWidget):
    def __init__(self, desk, arg=None):
        super().__init__()
        self.desk, self.tab = desk, "discover"
        v = QVBoxLayout(self); v.setContentsMargins(14, 6, 14, 10); v.setSpacing(10)
        hero = QLabel(f"<span style='font-size:21px;font-weight:600;color:white'>One store. Every store.</span><br>"
                      f"<span style='color:rgba(255,255,255,0.85)'>{len(CATALOG)} apps from {len(SOURCES)} stores · ⚡ = full interactive built-in app ready to run.</span>")
        hero.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #2563eb,stop:1 #9333ea);"
                           "border-radius:12px;padding:16px 20px;")
        v.addWidget(hero)
        bar = QHBoxLayout(); v.addLayout(bar)
        self.search = QLineEdit(); self.search.setPlaceholderText("🔍  Search all stores")
        self.search.textChanged.connect(self.refresh); bar.addWidget(self.search, 1)
        self.srcbox = QComboBox(); self.srcbox.addItem("All stores"); self.srcbox.addItems(SOURCES.values())
        self.catbox = QComboBox(); self.catbox.addItem("All categories"); self.catbox.addItems(CATEGORIES)
        for c in (self.srcbox, self.catbox):
            c.currentIndexChanged.connect(self.refresh); bar.addWidget(c)
        tabs = QHBoxLayout(); v.addLayout(tabs)
        self.b_disc = QPushButton("Discover"); self.b_inst = QPushButton("Installed")
        for b, k in ((self.b_disc, "discover"), (self.b_inst, "installed")):
            b.clicked.connect(lambda _, k=k: self.set_tab(k)); tabs.addWidget(b)
        tabs.addStretch(); self.count = QLabel(); self.count.setProperty("sub", True); tabs.addWidget(self.count)
        self.sc = QScrollArea(); self.sc.setWidgetResizable(True)
        self.holder = QWidget(); self.grid = QGridLayout(self.holder)
        self.grid.setSpacing(10); self.grid.setContentsMargins(0, 0, 6, 0)
        self.sc.setWidget(self.holder); v.addWidget(self.sc, 1)
        if arg: self.search.setText(arg)
        self.set_tab("discover")

    def set_tab(self, k):
        self.tab = k
        self.b_disc.setProperty("kind", "accent" if k == "discover" else "flat")
        self.b_inst.setProperty("kind", "accent" if k == "installed" else "flat")
        for b in (self.b_disc, self.b_inst):
            b.style().unpolish(b); b.style().polish(b)
        self.refresh()

    def refresh(self, *_):
        q = self.search.text().lower(); src = self.srcbox.currentText(); cat = self.catbox.currentText()
        items = [i for i in CATALOG
                 if (self.tab == "discover" or i["name"] in S.installed)
                 and (not q or q in (i["name"] + " " + i["dev"] + " " + i["desc"]).lower())
                 and (src == "All stores" or src in i["sources"])
                 and (cat == "All categories" or i["cat"] == cat)]
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.setParent(None); w.deleteLater()
        for n, it in enumerate(items):
            self.grid.addWidget(AppCard(self, it), n // 2, n % 2)
        self.grid.setRowStretch(len(items) // 2 + 1, 1)
        self.count.setText(f"{len(items)} apps" + ("" if self.tab == "discover" else " installed"))

    def finish_install(self, item, src):
        S.installed[item["name"]] = src; save_state()
        self.desk.toast("Installed", f"{item['name']} was installed from {src}.")
        self.desk.after_change(); self.refresh()

    def uninstall(self, item):
        S.installed.pop(item["name"], None); save_state()
        self.desk.toast("Uninstalled", f"{item['name']} was removed.")
        self.desk.after_change(); self.refresh()


# ───────────────────────────── settings ─────────────────────────────
class Settings(QWidget):
    def __init__(self, desk, arg=None):
        super().__init__()
        self.desk = desk
        h = QHBoxLayout(self); h.setContentsMargins(10, 6, 10, 10); h.setSpacing(12)
        nav = QListWidget(); nav.setFixedWidth(190)
        nav.addItems(["🖥️  System", "🎨  Personalization", "📦  Apps", "ℹ️  About"])
        h.addWidget(nav)
        self.stack = QStackedWidget(); h.addWidget(self.stack, 1)
        nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.stack.addWidget(self.page_system()); self.stack.addWidget(self.page_personal())
        self.apps_page = QWidget(); self.stack.addWidget(self.apps_page); self.stack.addWidget(self.page_about())
        nav.currentRowChanged.connect(lambda i: self.fill_apps() if i == 2 else None)
        nav.setCurrentRow(1)

    def page(self, title):
        w = QWidget(); v = QVBoxLayout(w); v.setAlignment(Qt.AlignTop); v.setSpacing(10)
        v.addWidget(QLabel(f"<span style='font-size:22px;font-weight:600'>{title}</span>"))
        return w, v

    def page_system(self):
        w, v = self.page("System")
        for t in (f"Host OS: {platform.system()} {platform.release()}", f"Python {platform.python_version()}",
                  f"Display: {self.desk.width()} × {self.desk.height()}"):
            l = QLabel(t); l.setProperty("sub", True); v.addWidget(l)
        return w

    def page_personal(self):
        w, v = self.page("Personalization")
        v.addWidget(QLabel("Operating system style"))
        osb = QComboBox(); osb.addItems([SKINS[k]["label"] for k in OS_LIST]); osb.setCurrentIndex(OS_LIST.index(S.skin))
        osb.currentIndexChanged.connect(lambda i: self.desk.set_skin(OS_LIST[i])); v.addWidget(osb)
        v.addWidget(QLabel("Theme"))
        cb = QComboBox(); cb.addItems(["Dark", "Light"]); cb.setCurrentIndex(0 if S.theme == "dark" else 1)
        cb.currentIndexChanged.connect(lambda i: self.set_theme("dark" if i == 0 else "light")); v.addWidget(cb)
        v.addWidget(QLabel("Accent color"))
        row = QHBoxLayout(); v.addLayout(row)
        for c in ("#4cc2ff", "#7a7cff", "#ff6bd6", "#ff8a4c", "#3ddc97", "#ffd23f"):
            b = QPushButton(); b.setFixedSize(34, 34)
            b.setStyleSheet(f"QPushButton{{background:{c};border-radius:17px;border:2px solid rgba(255,255,255,0.4);}}")
            b.clicked.connect(lambda _, c=c: self.set_accent(c)); row.addWidget(b)
        row.addStretch()
        v.addWidget(QLabel("Background"))
        row = QHBoxLayout(); v.addLayout(row)
        for i in range(6):
            b = QPushButton(); b.setFixedSize(92, 58)
            pm = make_wallpaper(92, 58, i); b.setIcon(QIcon(pm)); b.setIconSize(pm.size())
            b.clicked.connect(lambda _, i=i: self.set_wall(i)); row.addWidget(b)
        row.addStretch()
        return w

    def page_about(self):
        w, v = self.page("About")
        import PySide6
        for t in ("Windows 12 · Python Edition", "Version 12.0 (shell build)", f"Qt for Python {PySide6.__version__}",
                  f"Store catalog: {len(CATALOG)} apps ({len(BUILTIN_TOOLS)} interactive built-ins)",
                  "Not affiliated with Microsoft. A desktop shell simulation, not a real operating system."):
            l = QLabel(t); l.setProperty("sub", True); l.setWordWrap(True); v.addWidget(l)
        return w

    def fill_apps(self):
        lay = self.apps_page.layout()
        if lay is None:
            lay = QVBoxLayout(self.apps_page); lay.setAlignment(Qt.AlignTop)
        while lay.count():
            x = lay.takeAt(0).widget()
            if x: x.setParent(None); x.deleteLater()
        lay.addWidget(QLabel("<span style='font-size:22px;font-weight:600'>Installed apps</span>"))
        if not S.installed:
            l = QLabel("Nothing installed yet — open the Store."); l.setProperty("sub", True); lay.addWidget(l)
        for n, s in S.installed.items():
            if n not in BY_NAME: continue
            r = QHBoxLayout(); l = QLabel(f"{BY_NAME[n]['emoji']}  {n}  — {s}"); r.addWidget(l, 1)
            b = QPushButton("Uninstall"); b.clicked.connect(lambda _, n=n: self.remove(n)); r.addWidget(b)
            c = QWidget(); c.setLayout(r); lay.addWidget(c)

    def remove(self, n):
        S.installed.pop(n, None); save_state(); self.desk.after_change(); self.fill_apps()

    def set_theme(self, t):
        S.theme = t; self.desk.restyle()

    def set_accent(self, c):
        S.accent = c; self.desk.restyle()

    def set_wall(self, i):
        S.wallpaper = i; self.desk.rebuild_wall(); self.desk.restyle()


# ───────────────────────────── desktop ─────────────────────────────
class DesktopIcon(QWidget):
    def __init__(self, parent, key, cb):
        super().__init__(parent)
        self.key, self.cb, self.hover = key, cb, False
        self.setFixedSize(86, 94); self.setMouseTracking(True)

    def enterEvent(self, e): self.hover = True; self.update()
    def leaveEvent(self, e): self.hover = False; self.update()
    def mouseDoubleClickEvent(self, e): self.cb()

    def paintEvent(self, e):
        t, em, c = info(self.key)
        p = QPainter(self); p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        if self.hover:
            p.setPen(QPen(QColor(255, 255, 255, 70))); p.setBrush(QColor(255, 255, 255, 38))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 6, 6)
        p.drawPixmap(21, 8, tile(em, c, 44))
        r = QRect(2, 58, 82, 34)
        p.setPen(QColor(0, 0, 0, 160)); p.drawText(r.translated(1, 1), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, t)
        p.setPen(QColor("white")); p.drawText(r, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, t)


class LockScreen(QWidget):
    def __init__(self, desk):
        super().__init__(desk); self.desk = desk
        self.setGeometry(desk.rect()); self.setFocusPolicy(Qt.StrongFocus)

    def paintEvent(self, e):
        p = QPainter(self); p.drawPixmap(self.rect(), self.desk.wall)
        p.fillRect(self.rect(), QColor(0, 0, 0, 70)); p.setPen(QColor("white"))
        n = QDateTime.currentDateTime()
        f = QFont(); f.setPixelSize(120); f.setWeight(QFont.Light); p.setFont(f)
        p.drawText(self.rect().adjusted(0, -80, 0, 0), Qt.AlignCenter, n.toString("h:mm"))
        f.setPixelSize(26); p.setFont(f)
        p.drawText(self.rect().adjusted(0, 150, 0, 0), Qt.AlignCenter, n.toString("dddd, MMMM d"))
        f.setPixelSize(14); p.setFont(f)
        p.drawText(self.rect().adjusted(0, 0, 0, -60), Qt.AlignHCenter | Qt.AlignBottom, "Click or press any key to unlock")

    def mousePressEvent(self, e): self.deleteLater()
    def keyPressEvent(self, e): self.deleteLater()


class Desktop(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Windows 12 — Python Edition"); self.setMinimumSize(900, 600)
        self.setFocusPolicy(Qt.StrongFocus)
        self.wall = self.blur = None
        self.wins, self.active, self.recent = [], None, []
        self.chrome_ready = False
        self.tb = self.tray = self.start = self.pill = None
        self.icons = []
        for i, k in enumerate(("files", "edge", "store", "terminal")):
            ic = DesktopIcon(self, k, lambda k=k: self.launch(k)); ic.move(14, 14 + i * 100); self.icons.append(ic)
        self.build_chrome()
        QApplication.instance().installEventFilter(self)
        QTimer.singleShot(400, lambda: self.toast(f"Welcome to {SKINS[S.skin]['label']}",
                                                  "Open the Store — apps marked ⚡ run interactively inside the shell."))

    def insets(self):
        return SKINS[S.skin]["ins"]

    def work_rect(self):
        top, left, bot = self.insets()
        return QRect(left, top, self.width() - left, self.height() - top - bot)

    def build_chrome(self):
        self.chrome_ready = False
        for n in ("tb", "tray", "start", "pill"):
            w = getattr(self, n)
            if w is not None:
                w.hide(); w.setParent(None); w.deleteLater()
        sk = S.skin
        self.tb = Taskbar(self)
        self.tray = Tray(self) if sk == "win12" else TopBar(self)
        self.start = StartMenu(self)
        self.pill = HomePill(self) if sk == "android" else None
        for ic in self.icons: ic.setVisible(sk == "win12")
        self.chrome_ready = True
        self.tb.show(); self.tray.show()
        if self.pill: self.pill.show()
        self.tb.refresh()

    def set_skin(self, name):
        if name == S.skin: return
        S.skin, S.wallpaper = name, SKINS[name]["wall"]
        QApplication.instance().setStyleSheet(build_qss())
        self.build_chrome(); self.rebuild_wall()
        for w in self.wins: w.apply_skin()
        save_state(); self.tb.refresh()
        self.toast(f"Switched to {SKINS[name]['label']}", "Same apps, same Universal Store.")

    def update_topbar(self):
        if hasattr(self.tray, "set_app"):
            ok = self.active is not None and self.active.isVisible()
            self.tray.set_app(self.active.title_text if ok else info("files")[0])

    def go_home(self):
        self.start.hide()
        for w in self.wins: w.hide()
        self.active = None; self.tb.refresh()

    def fill_power_menu(self, m):
        m.addAction("Lock", self.lock)
        sub = m.addMenu("Switch OS")
        for k in OS_LIST:
            a = sub.addAction(SKINS[k]["label"] + ("  ✓" if k == S.skin else ""))
            a.triggered.connect(lambda _=False, k=k: self.set_skin(k))
        m.addSeparator()
        m.addAction("Restart", lambda: os.execv(sys.executable, [sys.executable] + sys.argv))
        m.addAction("Shut down", QApplication.quit)

    def rebuild_wall(self):
        w, h = self.width(), self.height()
        self.wall = make_wallpaper(w, h, S.wallpaper)
        self.blur = self.wall.scaled(max(1, w // 20), max(1, h // 20), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.update()

    def layout_chrome(self):
        if not self.chrome_ready: return
        w, h = self.width(), self.height()
        sk = S.skin; top, left, bot = self.insets()
        tb = self.tb
        if sk == "ubuntu":
            tb.setFixedHeight(h - top); tb.move(0, top)
        else:
            tb.move((w - tb.width()) // 2, h - tb.height() - SKINS[sk]["tb_gap"])
        if sk == "win12":
            self.tray.adjustSize(); self.tray.move(w - self.tray.width() - 12, h - 58 - 12)
        else:
            self.tray.setGeometry(0, 0, w, top)
        if self.pill: self.pill.move((w - self.pill.width()) // 2, h - 14)
        if self.start.isVisible(): self.start.raise_()
        for x in (tb, self.tray, self.pill):
            if x is not None: x.raise_()

    def resizeEvent(self, e):
        self.rebuild_wall(); self.layout_chrome()
        for win in self.wins:
            if win.maxed: win.setGeometry(self.work_rect())
        if self.chrome_ready and self.start.isVisible(): self.start.fit()

    def paintEvent(self, e):
        if self.wall: QPainter(self).drawPixmap(self.rect(), self.wall)

    def restyle(self):
        QApplication.instance().setStyleSheet(build_qss()); save_state()
        for w in self.findChildren(QWidget): w.update()
        self.tb.refresh()

    # ---- apps & windows ----
    def entries(self):
        out = [dict(title=info(k)[0], emoji=info(k)[1], color=info(k)[2], launch=lambda k=k: self.launch(k)) for k in BUILTIN_ORDER]
        for it in CATALOG:
            if it["name"] in S.installed:
                out.append(dict(title=it["name"], emoji=it["emoji"], color=it["color"], launch=lambda it=it: self.launch_installed(it)))
        return out

    def launch(self, key, arg=None):
        if key in ("store", "settings"):
            for w in self.wins:
                if w.key == key:
                    if arg and key == "store": w.content.search.setText(arg)
                    self.restore(w); return w
        title, emoji, color = info(key)
        cls = dict(files=Files, edge=Browser, store=Store, notepad=Notepad, calc=Calculator, terminal=Terminal, settings=Settings)[key]
        self.recent.append(title)
        return self._open(OSWindow(self, key, title, emoji, color, cls(self, arg), SIZES[key], shadow=(key != "edge")))

    def open_tool(self, name, arg=None):
        """Open a built-in catalog tool directly (used by File Explorer file associations)."""
        it = BY_NAME[name]
        cls, size = BUILTIN_TOOLS[name]
        self.recent.append(name)
        return self._open(OSWindow(self, "app:" + name, name, it["emoji"], it["color"], cls(self, arg), size))

    def launch_installed(self, it):
        key = "app:" + it["name"]
        for w in self.wins:
            if w.key == key: self.restore(w); return
        name = it["name"]
        self.recent.append(name)
        shadow, size = True, SIZES["app"]
        if name in BUILTIN_TOOLS:
            cls, size = BUILTIN_TOOLS[name]
            content = cls(self, None)
        elif native_launch(name):
            self.toast(name, "Launched the copy installed on this computer."); return
        elif name in WEB:
            content, size, shadow = Browser(self, WEB[name]), SIZES["edge"], False
        else:
            content = InstalledApp(self, it)
        self._open(OSWindow(self, key, name, it["emoji"], it["color"], content, size, shadow=shadow))

    def _open(self, w):
        top, left, bot = self.insets()
        off = 28 * (len(self.wins) % 8)
        w.move(max(left, min(left + 120 + off, self.width() - w.width())),
               max(top, min(top + 40 + off, self.height() - w.height() - bot)))
        if S.skin == "android": w.toggle_max()
        self.wins.append(w); w.show(); self.focus(w)
        w.content.setFocus()
        return w

    def focus(self, w):
        w.raise_(); self.active = w
        self.layout_chrome(); self.tb.refresh()

    def restore(self, w):
        w.show(); self.focus(w)

    def close_window(self, w):
        if w in self.wins: self.wins.remove(w)
        if self.active is w:
            vis = [x for x in self.wins if x.isVisible()]
            self.active = vis[-1] if vis else None
        w.setParent(None); w.deleteLater(); self.tb.refresh()

    def after_change(self):
        vis = [x for x in self.wins if x.isVisible()]
        if self.active not in vis: self.active = vis[-1] if vis else None
        self.tb.refresh()
        if self.start.isVisible(): self.start.refresh_apps(self.start.search.text())

    def tb_click(self, key):
        ws = [w for w in self.wins if w.key == key]
        if not ws: self.launch(key)
        elif self.active is not None and self.active.key == key and self.active.isVisible(): self.active.minimize()
        else: self.restore(ws[-1])

    def toggle_start(self, focus_search=False):
        if self.start.isVisible() and not focus_search: self.start.hide()
        else: self.start.popup(focus_search)

    def toast(self, title, msg):
        t = Acrylic(self, 12); t.setFixedSize(310, 78)
        v = QVBoxLayout(t); v.setContentsMargins(16, 10, 16, 10); v.setSpacing(2)
        v.addWidget(QLabel(f"<b>{title}</b>")); m = QLabel(msg); m.setProperty("sub", True); m.setWordWrap(True); v.addWidget(m)
        if S.skin == "win12":
            t.move(self.width() - 322, self.height() - 58 - 12 - 78 - 12)
        else:
            t.move(self.width() - 322, self.insets()[0] + 12)
        t.show(); t.raise_()
        QTimer.singleShot(4500, t.deleteLater)

    def lock(self):
        self.start.hide(); ls = LockScreen(self); ls.show(); ls.raise_(); ls.setFocus()

    def contextMenuEvent(self, e):
        m = QMenu(self)
        m.addAction("Change background", lambda: (setattr(S, "wallpaper", (S.wallpaper + 1) % 6), self.rebuild_wall(), self.restyle()))
        sub = m.addMenu("Switch OS")
        for k in OS_LIST:
            a = sub.addAction(SKINS[k]["label"] + ("  ✓" if k == S.skin else ""))
            a.triggered.connect(lambda _=False, k=k: self.set_skin(k))
        m.addAction("Personalize", lambda: self.launch("settings"))
        m.addSeparator()
        m.addAction("Open Terminal", lambda: self.launch("terminal"))
        m.addAction("Open Store", lambda: self.launch("store"))
        m.exec(e.globalPos())

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
        elif e.key() == Qt.Key_Escape and self.isFullScreen(): self.showNormal()
        elif e.key() == Qt.Key_Meta: self.toggle_start()

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.MouseButtonPress and isinstance(obj, QWidget) and obj.window() is self:
            w = obj
            while w is not None and not isinstance(w, OSWindow): w = w.parentWidget()
            if w is not None and w is not self.active and w.isVisible(): self.focus(w)
            if self.chrome_ready and self.start.isVisible():
                gp = ev.globalPosition().toPoint()
                over_start = self.start.rect().contains(self.start.mapFromGlobal(gp))
                over_btn = False
                for b in (self.tb.btn_start, getattr(self.tray, "act_btn", None)):
                    if b is not None and b.rect().contains(b.mapFromGlobal(gp)): over_btn = True
                if not over_start and not over_btn: self.start.hide()
        return False


def main():
    try:
        load_state()
        app = QApplication(sys.argv)
        app.setApplicationName("Windows 12")
        app.setStyleSheet(build_qss())
        d = Desktop()
        d.resize(1280, 800)
        d.show()
        d.raise_()
        d.activateWindow()
        sys.exit(app.exec())
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    main()
