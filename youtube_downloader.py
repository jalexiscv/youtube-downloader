"""
Higgs Video Downloader — Dashboard
Copyright (c) 2026 Jose Alexis Correa Valencia — Freeware de uso irrestricto
"""

import sys, os, uuid, urllib.request
import yt_dlp
from PyQt6.QtCore  import Qt, QThread, pyqtSignal, QTimer, QSize, QRect, QPoint
from PyQt6.QtGui   import (
    QFont, QPixmap, QColor, QPalette, QCursor, QPainter,
    QBrush, QLinearGradient, QPen, QRadialGradient, QImage
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QProgressBar,
    QFileDialog, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
    QStackedWidget, QScrollArea, QAbstractItemView
)


# ── ffmpeg ────────────────────────────────────────────────────────────────────

def _find_ffmpeg():
    candidates = (
        [sys._MEIPASS, os.path.dirname(sys.executable)]
        if getattr(sys, "frozen", False)
        else [os.path.dirname(os.path.abspath(__file__))]
    )
    for p in candidates:
        if os.path.isfile(os.path.join(p, "ffmpeg.exe")):
            return p
    return None

FFMPEG_DIR = _find_ffmpeg()

def default_video_dir():
    v = os.path.expanduser("~/Videos")
    return v if os.path.isdir(v) else os.path.expanduser("~/Downloads")


# ── Paleta — iTunes / Apple dark ─────────────────────────────────────────────

P = {
    # superficies
    "bg":       "#1c1c1e",
    "sidebar":  "#161618",
    "card":     "#2c2c2e",
    "card2":    "#3a3a3c",
    "input":    "#2c2c2e",
    "border":   "#48484a",
    "divider":  "#3a3a3c",
    # texto
    "text":     "#f5f5f7",
    "text2":    "#aeaeb2",
    "muted":    "#636366",
    # sistema
    "blue":     "#0071e3",
    "green":    "#30d158",
    "orange":   "#ff9f0a",
    "red":      "#ff375f",
}

# Acentos por plataforma
PA = {
    "youtube": {"pri": "#ff375f", "sec": "#ff6b35", "icon": "▶"},
    "tiktok":  {"pri": "#64d2ff", "sec": "#bf5af2", "icon": "♪"},
}


# ── Plataformas ───────────────────────────────────────────────────────────────

PLATFORMS = {
    "youtube": {
        "label": "YouTube", "hint": "Pega un enlace de YouTube…",
        "formats": [
            ("Mejor calidad  (video + audio)",
             "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"),
            ("1080p  (video + audio)",
             "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]"),
            ("720p  (video + audio)",
             "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]"),
            ("480p  (video + audio)",
             "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]"),
            ("360p  (video + audio)",
             "bestvideo[ext=mp4][height<=360]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]"),
            ("Solo audio  (MP3 192 kbps)", "bestaudio/best"),
        ],
        "extractor_args": {},
        "code": "yt",
    },
    "tiktok": {
        "label": "TikTok", "hint": "Pega un enlace de TikTok…",
        "formats": [
            ("Alta calidad  (sin marca de agua)",
             "best[format_id!*=watermark][ext=mp4]/best[format_id!*=watermark]/best[ext=mp4]/best"),
            ("Solo audio  (MP3 192 kbps)", "bestaudio/best"),
        ],
        "extractor_args": {"tiktok": {"api_hostname": "api22-normal-c-useast2a.tiktokv.com"}},
        "code": "tt",
    },
}


# ── Workers ───────────────────────────────────────────────────────────────────

class InfoWorker(QThread):
    ready  = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url, extractor_args=None):
        super().__init__()
        self.url = url
        self.extractor_args = extractor_args or {}

    def run(self):
        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True,
                    "extractor_args": self.extractor_args}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

            thumb = None
            # Intentar obtener la miniatura de mayor resolución
            thumbs = info.get("thumbnails") or []
            thumb_url = (
                sorted(thumbs, key=lambda t: t.get("width", 0), reverse=True)[0]["url"]
                if thumbs else info.get("thumbnail", "")
            )
            if thumb_url:
                try:
                    req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=8) as r:
                        thumb = r.read()
                except Exception:
                    pass

            self.ready.emit({
                "title":      info.get("title") or info.get("description", "")[:80] or "Sin título",
                "channel":    info.get("uploader") or info.get("creator") or info.get("channel") or "—",
                "duration":   int(info.get("duration") or 0),
                "view_count": info.get("view_count") or 0,
                "like_count": info.get("like_count") or 0,
                "thumbnail":  thumb,
            })
        except Exception as e:
            self.failed.emit(str(e))


class DownloadWorker(QThread):
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, url, fmt, out_dir, ffmpeg_dir, platform_code, extractor_args=None):
        super().__init__()
        self.url           = url
        self.fmt           = fmt
        self.out_dir       = out_dir
        self.ffmpeg_dir    = ffmpeg_dir
        self.pcode         = platform_code
        self.extractor_args = extractor_args or {}
        self._phase        = 1

    def _hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            done  = d.get("downloaded_bytes", 0)
            spd   = d.get("_speed_str", "").strip()
            eta   = d.get("_eta_str", "").strip()
            chunk = (done / total * 100) if total else 0
            pct   = chunk * 0.80 if self._phase == 1 else 80 + chunk * 0.15
            self.progress.emit(pct, f"Descargando…  {chunk:.1f}%   ·   {spd}   ·   ETA {eta}")
        elif d["status"] == "finished":
            self._phase = 2
            self.progress.emit(95, "Procesando archivo…")

    def run(self):
        try:
            is_audio  = self.fmt.startswith("bestaudio")
            uid       = uuid.uuid4().hex[:8]           # ID único de 8 caracteres
            res_part  = "mp3" if is_audio else "%(height|best)sp"
            filename  = f"{uid}-{self.pcode}-{res_part}-%(title)s.%(ext)s"
            outtmpl   = os.path.join(self.out_dir, filename)

            opts = {
                "format":              self.fmt,
                "outtmpl":             outtmpl,
                "merge_output_format": "mp4",
                "progress_hooks":      [self._hook],
                "extractor_args":      self.extractor_args,
            }
            if is_audio:
                opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3", "preferredquality": "192",
                }]
                opts.pop("merge_output_format", None)
            if self.ffmpeg_dir:
                opts["ffmpeg_location"] = self.ffmpeg_dir

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])

            self.progress.emit(100, "¡Listo!")
            self.finished.emit(self.out_dir)
        except Exception as e:
            msg = str(e)
            self.error.emit(msg.split("ERROR:")[-1].strip() if "ERROR:" in msg else msg)


# ── Helpers ───────────────────────────────────────────────────────────────────

def shadow(r=20, offset=(0, 4), alpha=140):
    e = QGraphicsDropShadowEffect()
    c = QColor("#000000"); c.setAlpha(alpha)
    e.setColor(c); e.setBlurRadius(r); e.setOffset(*offset)
    return e

def fmt_num(n):
    if not n: return "—"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)

def fmt_dur(secs):
    if not secs: return "—"
    if secs >= 3600: return f"{secs//3600}h {(secs%3600)//60}m {secs%60:02d}s"
    return f"{secs//60}:{secs%60:02d}"

def short_path(p, n=52):
    return p if len(p) <= n else "…" + p[-(n-1):]


# ── Componentes de estilo ─────────────────────────────────────────────────────

# CSS global de la app
APP_CSS = f"""
* {{ font-family: "Segoe UI", sans-serif; }}
QToolTip {{
    background: {P['card2']}; color: {P['text']};
    border: 1px solid {P['border']}; border-radius: 6px; padding: 4px 8px;
    font-size: 11px;
}}
QScrollBar:vertical {{
    background: transparent; width: 5px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {P['border']}; border-radius: 2px; min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

def input_css(accent):
    return f"""
    QLineEdit, QComboBox {{
        background: {P['input']};
        color: {P['text']};
        border: 1px solid {P['border']};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 13px;
        selection-background-color: {accent};
    }}
    QLineEdit:focus {{ border-color: {accent}; }}
    QComboBox:focus {{ border-color: {accent}; }}
    QComboBox::drop-down {{ border: none; width: 32px; }}
    QComboBox::down-arrow {{
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {P['muted']};
        margin-right: 12px;
    }}
    QComboBox QAbstractItemView {{
        background: {P['card2']};
        color: {P['text']};
        selection-background-color: {accent}55;
        selection-color: {P['text']};
        border: 1px solid {P['border']};
        border-radius: 10px;
        padding: 6px 4px;
        outline: 0;
    }}
    QComboBox QAbstractItemView::item {{
        padding: 7px 14px;
        border-radius: 6px;
        min-height: 28px;
    }}
    """


# ── Botones ───────────────────────────────────────────────────────────────────

class PrimaryBtn(QPushButton):
    def __init__(self, text, pri, sec, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {pri}, stop:1 {sec});
                color: white;
                border: none;
                border-radius: 12px;
                padding: 0 28px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {sec}, stop:1 {pri});
            }}
            QPushButton:disabled {{
                background: {P['card2']};
                color: {P['muted']};
            }}
        """)


class GhostBtn(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {P['text2']};
                border: 1px solid {P['border']};
                border-radius: 9px;
                padding: 7px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {P['card2']};
                color: {P['text']};
                border-color: {P['card2']};
            }}
        """)


class NavBtn(QPushButton):
    def __init__(self, icon, label, accent, parent=None):
        super().__init__(parent)
        self._icon   = icon
        self._label  = label
        self._accent = accent
        self._active = False
        self.setFixedHeight(44)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._paint()

    def setActive(self, v):
        self._active = v
        self._paint()

    def _paint(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {self._accent}20;
                    color: {self._accent};
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                    padding: 0 14px;
                    font-size: 13px;
                    font-weight: 700;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {P['text2']};
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                    padding: 0 14px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: {P['card2']}88;
                    color: {P['text']};
                }}
            """)
        self.setText(f"  {self._icon}   {self._label}")


# ── Sidebar ───────────────────────────────────────────────────────────────────

class Sidebar(QWidget):
    changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(f"background: {P['sidebar']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Logo / App name ───────────────────────────────────────────────────
        logo = QWidget()
        logo.setFixedHeight(88)
        logo.setStyleSheet(f"background: {P['sidebar']};")
        ll = QVBoxLayout(logo); ll.setContentsMargins(20, 20, 20, 8)

        app_lbl = QLabel("Higgs")
        app_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        app_lbl.setStyleSheet(f"color: {P['text']};")

        sub_lbl = QLabel("Video Downloader")
        sub_lbl.setStyleSheet(f"color: {P['muted']}; font-size: 10px; letter-spacing: 1px; font-weight: 600;")

        ll.addWidget(app_lbl)
        ll.addWidget(sub_lbl)
        root.addWidget(logo)

        # ── Divisor ───────────────────────────────────────────────────────────
        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet(f"background: {P['divider']};")
        root.addWidget(div)

        # ── Sección nav ───────────────────────────────────────────────────────
        sec = QLabel("PLATAFORMAS")
        sec.setStyleSheet(f"""
            color: {P['muted']}; font-size: 9px; font-weight: 700;
            letter-spacing: 1.8px; padding: 18px 20px 6px;
        """)
        root.addWidget(sec)

        nav = QWidget()
        nl = QVBoxLayout(nav); nl.setContentsMargins(10, 0, 10, 0); nl.setSpacing(3)

        self._btns = {}
        for key in ("youtube", "tiktok"):
            cfg = PLATFORMS[key]
            btn = NavBtn(PA[key]["icon"], cfg["label"], PA[key]["pri"])
            btn.clicked.connect(lambda _, k=key: self._pick(k))
            self._btns[key] = btn
            nl.addWidget(btn)

        root.addWidget(nav)
        root.addStretch()

        # ── Divisor ───────────────────────────────────────────────────────────
        div2 = QFrame(); div2.setFixedHeight(1)
        div2.setStyleSheet(f"background: {P['divider']};")
        root.addWidget(div2)

        # ── Footer ────────────────────────────────────────────────────────────
        foot = QWidget()
        foot.setFixedHeight(60)
        fl = QVBoxLayout(foot); fl.setContentsMargins(20, 10, 20, 12); fl.setSpacing(2)
        fl.addWidget(self._foot_lbl("Jose Alexis Correa Valencia", P["text2"], "10px", "600"))
        fl.addWidget(self._foot_lbl("v3.2  ·  Freeware", P["muted"], "9px"))
        root.addWidget(foot)

        self._pick("youtube")

    def _foot_lbl(self, text, color, size, weight="400"):
        l = QLabel(text)
        l.setStyleSheet(f"color: {color}; font-size: {size}; font-weight: {weight};")
        l.setWordWrap(True)
        return l

    def _pick(self, key):
        for k, b in self._btns.items():
            b.setActive(k == key)
        self.changed.emit(key)


# ── Panel de plataforma ───────────────────────────────────────────────────────

class PlatformPanel(QWidget):

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self.pk   = key
        self.cfg  = PLATFORMS[key]
        self.pri  = PA[key]["pri"]
        self.sec  = PA[key]["sec"]
        self.icon = PA[key]["icon"]
        self.setStyleSheet(f"background: {P['bg']};")

        self._dl_path    = default_video_dir()
        self._info_w     = None
        self._dl_w       = None
        self._debounce   = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._fetch)

        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 18)
        root.setSpacing(16)

        root.addWidget(self._build_topbar())
        root.addWidget(self._build_url_row())

        mid = QHBoxLayout(); mid.setSpacing(16)
        mid.addWidget(self._build_preview(), 45)
        mid.addWidget(self._build_options(), 55)
        root.addLayout(mid, 1)

        root.addWidget(self._build_progress())

    # ── Topbar ────────────────────────────────────────────────────────────────

    def _build_topbar(self):
        w = QWidget()
        r = QHBoxLayout(w); r.setContentsMargins(0, 0, 0, 0)

        ico = QLabel(self.icon)
        ico.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        ico.setStyleSheet(f"color: {self.pri};")

        title = QLabel(self.cfg["label"])
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {P['text']};")

        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        ffok  = FFMPEG_DIR is not None
        badge = QLabel("  ffmpeg ✓  " if ffok else "  ffmpeg ✗  ")
        badge.setStyleSheet(f"""
            color: {P['green'] if ffok else P['orange']};
            background: {'#30d15818' if ffok else '#ff9f0a18'};
            border: 1px solid {'#30d15840' if ffok else '#ff9f0a40'};
            border-radius: 8px; font-size: 10px; font-weight: 700;
            padding: 3px 0;
        """)

        r.addWidget(ico); r.addSpacing(8); r.addWidget(title)
        r.addWidget(spacer); r.addWidget(badge)
        return w

    # ── URL row ───────────────────────────────────────────────────────────────

    def _build_url_row(self):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {P['card']};
                border: 1px solid {P['border']};
                border-radius: 14px;
            }}
        """)
        card.setGraphicsEffect(shadow(14, (0, 2), 100))

        r = QHBoxLayout(card); r.setContentsMargins(16, 10, 12, 10); r.setSpacing(10)

        pill = QLabel("URL")
        pill.setFixedSize(38, 22)
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.setStyleSheet(f"""
            background: {self.pri}22; color: {self.pri};
            border-radius: 6px; font-size: 10px; font-weight: 700;
        """)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(self.cfg["hint"])
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; color: {P['text']};
                border: none; font-size: 13px; padding: 6px 0;
            }}
        """)
        self.url_input.textChanged.connect(self._on_url)

        clr = QPushButton("✕")
        clr.setFixedSize(28, 28)
        clr.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        clr.setStyleSheet(f"""
            QPushButton {{
                background: {P['card2']}; color: {P['muted']};
                border: none; border-radius: 7px; font-size: 11px;
            }}
            QPushButton:hover {{ color: {P['text']}; }}
        """)
        clr.clicked.connect(self._clear)

        prev = PrimaryBtn("Preview", self.pri, self.sec)
        prev.setFixedHeight(34)
        prev.setStyleSheet(prev.styleSheet() + "QPushButton { font-size: 12px; border-radius: 9px; }")
        prev.clicked.connect(self._fetch)

        r.addWidget(pill); r.addWidget(self.url_input, 1)
        r.addWidget(clr);  r.addWidget(prev)
        return card

    # ── Preview card ──────────────────────────────────────────────────────────

    def _build_preview(self):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {P['card']};
                border: 1px solid {P['border']};
                border-radius: 16px;
            }}
        """)
        card.setGraphicsEffect(shadow(18, (0, 4), 110))

        v = QVBoxLayout(card); v.setContentsMargins(0, 0, 0, 16); v.setSpacing(0)

        # Thumbnail con esquinas redondeadas arriba
        self.thumb = ThumbnailWidget(self.icon, self.pri)
        self.thumb.setFixedHeight(190)
        v.addWidget(self.thumb)

        info = QWidget()
        il   = QVBoxLayout(info); il.setContentsMargins(16, 12, 16, 0); il.setSpacing(8)

        self.lbl_title = QLabel("Sin video")
        self.lbl_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet(f"color: {P['text']};")
        self.lbl_title.setWordWrap(True)
        il.addWidget(self.lbl_title)

        grid = QWidget()
        gl = QHBoxLayout(grid); gl.setContentsMargins(0, 0, 0, 0); gl.setSpacing(0)

        self.col_left  = QVBoxLayout(); self.col_left.setSpacing(6)
        self.col_right = QVBoxLayout(); self.col_right.setSpacing(6)

        self.m_channel  = self._meta_item("Canal",    "—")
        self.m_duration = self._meta_item("Duración", "—")
        self.m_views    = self._meta_item("Vistas",   "—")
        self.m_likes    = self._meta_item("Likes",    "—")

        self.col_left.addWidget(self.m_channel[0]);  self.col_left.addWidget(self.m_duration[0])
        self.col_right.addWidget(self.m_views[0]);   self.col_right.addWidget(self.m_likes[0])

        gl.addLayout(self.col_left, 1); gl.addSpacing(12); gl.addLayout(self.col_right, 1)
        il.addWidget(grid)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color: {P['muted']}; font-size: 10px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.addWidget(self.status_lbl)

        v.addWidget(info)
        return card

    def _meta_item(self, key, val):
        """Retorna (widget, key_label, val_label)."""
        w  = QWidget()
        vb = QVBoxLayout(w); vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(1)
        kl = QLabel(key.upper())
        kl.setStyleSheet(f"color: {P['muted']}; font-size: 9px; font-weight: 700; letter-spacing: 0.8px;")
        vl = QLabel(val)
        vl.setStyleSheet(f"color: {P['text2']}; font-size: 12px; font-weight: 500;")
        vb.addWidget(kl); vb.addWidget(vl)
        return w, kl, vl

    def _set_meta(self, item_tuple, val):
        item_tuple[2].setText(val)

    # ── Options card ──────────────────────────────────────────────────────────

    def _build_options(self):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {P['card']};
                border: 1px solid {P['border']};
                border-radius: 16px;
            }}
        """)
        card.setGraphicsEffect(shadow(18, (0, 4), 110))

        v = QVBoxLayout(card); v.setContentsMargins(22, 22, 22, 22); v.setSpacing(6)

        v.addWidget(self._opt_label("FORMATO"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems([f[0] for f in self.cfg["formats"]])
        self.fmt_combo.setStyleSheet(input_css(self.pri))
        self.fmt_combo.setFixedHeight(44)
        v.addWidget(self.fmt_combo)

        v.addSpacing(10)
        v.addWidget(self._opt_label("CARPETA DE DESTINO"))

        dest_row = QHBoxLayout(); dest_row.setSpacing(8)
        self.dest_lbl = QLabel(short_path(self._dl_path))
        self.dest_lbl.setStyleSheet(f"""
            background: {P['input']}; color: {P['text2']};
            border: 1px solid {P['border']}; border-radius: 10px;
            padding: 10px 14px; font-size: 11px;
        """)
        self.dest_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.dest_lbl.setFixedHeight(44)
        browse = GhostBtn("Examinar"); browse.setFixedHeight(44)
        browse.clicked.connect(self._browse)
        dest_row.addWidget(self.dest_lbl); dest_row.addWidget(browse)
        v.addLayout(dest_row)

        # ID hint
        self.id_hint = QLabel("")
        self.id_hint.setStyleSheet(f"color: {P['muted']}; font-size: 9px; font-family: monospace;")
        self.id_hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        v.addWidget(self.id_hint)

        v.addStretch()

        # Divisor
        line = QFrame(); line.setFixedHeight(1)
        line.setStyleSheet(f"background: {P['divider']};")
        v.addWidget(line)
        v.addSpacing(10)

        self.dl_btn = PrimaryBtn("⬇   Descargar", self.pri, self.sec)
        self.dl_btn.setFixedHeight(52)
        v.addWidget(self.dl_btn)
        self.dl_btn.clicked.connect(self._start_dl)

        self.dl_note = QLabel("")
        self.dl_note.setStyleSheet(f"color: {P['muted']}; font-size: 10px;")
        self.dl_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.dl_note)
        return card

    def _opt_label(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {P['muted']}; font-size: 9px; font-weight: 700; letter-spacing: 1.5px;")
        return l

    # ── Progress ──────────────────────────────────────────────────────────────

    def _build_progress(self):
        w = QWidget(); w.setFixedHeight(32)
        v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(4)

        self.prog = QProgressBar()
        self.prog.setFixedHeight(4)
        self.prog.setTextVisible(False)
        self.prog.setValue(0)
        self.prog.setStyleSheet(f"""
            QProgressBar {{
                background: {P['card2']}; border-radius: 2px; border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {self.pri}, stop:1 {self.sec});
                border-radius: 2px;
            }}
        """)

        self.prog_lbl = QLabel("Listo")
        self.prog_lbl.setStyleSheet(f"color: {P['muted']}; font-size: 10px;")

        v.addWidget(self.prog)
        v.addWidget(self.prog_lbl)
        return w

    # ── Lógica preview ────────────────────────────────────────────────────────

    def _on_url(self, text):
        if any(d in text for d in ("youtube.com", "youtu.be", "tiktok.com", "vm.tiktok")):
            self._debounce.start(900)
        else:
            self._reset()

    def _clear(self):
        self.url_input.clear(); self._reset()
        self._set_prog("Listo", P["muted"])

    def _reset(self):
        self.thumb.reset(self.icon)
        self.lbl_title.setText("Sin video")
        self._set_meta(self.m_channel,  "—")
        self._set_meta(self.m_duration, "—")
        self._set_meta(self.m_views,    "—")
        self._set_meta(self.m_likes,    "—")
        self.status_lbl.setText("")
        self.id_hint.setText("")

    def _fetch(self):
        url = self.url_input.text().strip()
        if not url or (self._info_w and self._info_w.isRunning()):
            return
        self.status_lbl.setStyleSheet(f"color: {P['muted']}; font-size: 10px;")
        self.status_lbl.setText("Cargando información…")
        self.thumb.set_loading()
        self.lbl_title.setText("…")

        self._info_w = InfoWorker(url, self.cfg["extractor_args"])
        self._info_w.ready.connect(self._on_info)
        self._info_w.failed.connect(self._on_info_fail)
        self._info_w.start()

    def _on_info(self, info):
        self.lbl_title.setText(info["title"])
        self._set_meta(self.m_channel,  info["channel"])
        self._set_meta(self.m_duration, fmt_dur(info["duration"]))
        self._set_meta(self.m_views,    fmt_num(info["view_count"]))
        self._set_meta(self.m_likes,    fmt_num(info["like_count"]))

        if info["thumbnail"]:
            self.thumb.set_image(info["thumbnail"])
        else:
            self.thumb.reset(self.icon)

        self.status_lbl.setStyleSheet(f"color: {P['green']}; font-size: 10px;")
        self.status_lbl.setText("✓  Vista previa lista")

    def _on_info_fail(self, err):
        self.thumb.reset("✗")
        self.lbl_title.setText("No se pudo cargar el video")
        self.status_lbl.setStyleSheet(f"color: {self.pri}; font-size: 10px;")
        self.status_lbl.setText("Error al obtener información")

    # ── Lógica descarga ───────────────────────────────────────────────────────

    def _browse(self):
        f = QFileDialog.getExistingDirectory(self, "Carpeta de destino", self._dl_path)
        if f:
            self._dl_path = f
            self.dest_lbl.setText(short_path(f))

    def _start_dl(self):
        url = self.url_input.text().strip()
        if not url:
            self._set_prog("⚠  Ingresa una URL.", P["orange"]); return
        if self._dl_w and self._dl_w.isRunning():
            return

        idx = self.fmt_combo.currentIndex()
        fmt = self.cfg["formats"][idx][1]
        if fmt.startswith("bestaudio") and not FFMPEG_DIR:
            self._set_prog("✗  ffmpeg no encontrado — MP3 no disponible.", P["orange"]); return

        # Mostrar el ID que tendrá el archivo
        preview_id = uuid.uuid4().hex[:8]
        self.id_hint.setText(f"ID de archivo: {preview_id}-{self.cfg['code']}-…")

        self.dl_btn.setEnabled(False)
        self.prog.setValue(0)
        self.dl_note.setText("")
        self._set_prog("Iniciando descarga…", P["muted"])

        self._dl_w = DownloadWorker(
            url, fmt, self._dl_path, FFMPEG_DIR,
            self.cfg["code"], self.cfg["extractor_args"]
        )
        # Sobrescribir el uuid del worker con el que mostramos
        self._dl_w.uid_override = preview_id

        self._dl_w.progress.connect(lambda p, t: (self.prog.setValue(int(p)), self._set_prog(t, P["muted"])))
        self._dl_w.finished.connect(self._on_done)
        self._dl_w.error.connect(self._on_err)
        self._dl_w.start()

    def _on_done(self, folder):
        self.prog.setValue(100)
        self._set_prog(f"✓  Guardado en: {folder}", P["green"])
        self.dl_note.setText("Descarga completada")
        self.dl_btn.setEnabled(True)

    def _on_err(self, msg):
        self.prog.setValue(0)
        self._set_prog(f"✗  {msg[:140]}", self.pri)
        self.dl_btn.setEnabled(True)

    def _set_prog(self, text, color):
        self.prog_lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
        self.prog_lbl.setText(text)


# ── Widget de miniatura con efecto ────────────────────────────────────────────

class ThumbnailWidget(QLabel):
    """Miniatura con gradiente inferior y esquinas redondeadas arriba."""

    def __init__(self, placeholder, accent, parent=None):
        super().__init__(parent)
        self._placeholder = placeholder
        self._accent      = accent
        self._pix         = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_empty()

    def _apply_empty(self, text=None):
        self._pix = None
        self.setPixmap(QPixmap())
        self.setText(text or self._placeholder)
        self.setStyleSheet(f"""
            background: {P['card2']}; border-radius: 16px 16px 0 0;
            color: {P['muted']}; font-size: 32px;
        """)

    def reset(self, text=None):
        self._apply_empty(text)

    def set_loading(self):
        self._apply_empty("⏳")

    def set_image(self, data: bytes):
        pix = QPixmap()
        pix.loadFromData(data)
        self._pix = pix
        self.setStyleSheet("background: transparent;")
        self.update()

    def paintEvent(self, event):
        if self._pix is None:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()

        # Clip con esquinas redondeadas solo arriba
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 16, 16)
        painter.setClipPath(path)

        # Escalar y centrar la imagen
        scaled = self._pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                   Qt.TransformationMode.SmoothTransformation)
        x = (w - scaled.width()) // 2
        y = (h - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # Gradiente oscuro en la parte inferior
        grad = QLinearGradient(0, h * 0.5, 0, h)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 180))
        painter.fillRect(0, 0, w, h, grad)

        painter.end()


# ── Ventana principal ─────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Higgs Video Downloader")
        self.setMinimumSize(920, 640)
        self.resize(1060, 700)
        self._theme()
        self._build()

    def _theme(self):
        self.setStyleSheet(APP_CSS + f"""
            QMainWindow, QWidget {{ background: {P['bg']}; color: {P['text']}; }}
        """)
        pal = QPalette()
        for role, col in [
            (QPalette.ColorRole.Window,          P["bg"]),
            (QPalette.ColorRole.WindowText,      P["text"]),
            (QPalette.ColorRole.Base,            P["input"]),
            (QPalette.ColorRole.Text,            P["text"]),
            (QPalette.ColorRole.Button,          P["card"]),
            (QPalette.ColorRole.ButtonText,      P["text"]),
            (QPalette.ColorRole.Highlight,       P["blue"]),
            (QPalette.ColorRole.HighlightedText, "#ffffff"),
        ]:
            pal.setColor(role, QColor(col))
        QApplication.instance().setPalette(pal)

    def _build(self):
        root = QWidget(); self.setCentralWidget(root)
        row  = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0); row.setSpacing(0)

        self.sidebar = Sidebar()
        self.stack   = QStackedWidget()
        self.stack.setStyleSheet(f"background: {P['bg']};")

        self._panels = {}
        for key in ("youtube", "tiktok"):
            p = PlatformPanel(key)
            self._panels[key] = p
            self.stack.addWidget(p)

        self.sidebar.changed.connect(lambda k: self.stack.setCurrentWidget(self._panels[k]))

        # Línea separadora sidebar / contenido
        line = QFrame(); line.setFixedWidth(1)
        line.setStyleSheet(f"background: {P['divider']};")

        row.addWidget(self.sidebar)
        row.addWidget(line)
        row.addWidget(self.stack, 1)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
