"""
Higgs Video Downloader — Dashboard
Copyright (c) 2026 Jose Alexis Correa Valencia — Freeware de uso irrestricto
"""

import sys
import os
import urllib.request

import yt_dlp
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPoint
from PyQt6.QtGui  import (
    QFont, QPixmap, QColor, QPalette, QCursor,
    QPainter, QBrush, QLinearGradient, QPen
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QProgressBar,
    QFileDialog, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
    QStackedWidget, QScrollArea, QSpacerItem, QAbstractItemView
)


# ── ffmpeg ────────────────────────────────────────────────────────────────────

def _find_ffmpeg():
    if getattr(sys, "frozen", False):
        candidates = [sys._MEIPASS, os.path.dirname(sys.executable)]
    else:
        candidates = [os.path.dirname(os.path.abspath(__file__))]
    for p in candidates:
        if os.path.isfile(os.path.join(p, "ffmpeg.exe")):
            return p
    return None

FFMPEG_DIR = _find_ffmpeg()


def default_video_dir():
    v = os.path.expanduser("~/Videos")
    return v if os.path.isdir(v) else os.path.expanduser("~/Downloads")


# ── Paleta ────────────────────────────────────────────────────────────────────

BG      = "#08080f"
SIDEBAR = "#0d0d1a"
SURFACE = "#111120"
CARD    = "#171728"
BORDER  = "#22223a"
TEXT    = "#ececf4"
MUTED   = "#606080"
SUCCESS = "#4caf50"
WARNING = "#ff9800"
INPUT   = "#1a1a2d"

# Acento por plataforma
ACCENT = {
    "youtube": {"primary": "#e94560", "secondary": "#ff6b35"},
    "tiktok":  {"primary": "#69c9d0", "secondary": "#ee1d52"},
}


# ── Configuración de plataformas ──────────────────────────────────────────────

PLATFORMS = {
    "youtube": {
        "label":    "YouTube",
        "icon":     "▶",
        "hint":     "Pega un enlace de YouTube…",
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
    },
    "tiktok": {
        "label":    "TikTok",
        "icon":     "♪",
        "hint":     "Pega un enlace de TikTok…",
        "formats": [
            ("Alta calidad  (sin marca de agua)",
             "best[format_id!*=watermark][ext=mp4]/best[format_id!*=watermark]/best[ext=mp4]/best"),
            ("Solo audio  (MP3 192 kbps)", "bestaudio/best"),
        ],
        "extractor_args": {
            "tiktok": {"api_hostname": "api22-normal-c-useast2a.tiktokv.com"}
        },
    },
}


# ── Workers ───────────────────────────────────────────────────────────────────

class InfoWorker(QThread):
    ready  = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url, extractor_args=None):
        super().__init__()
        self.url             = url
        self.extractor_args  = extractor_args or {}

    def run(self):
        try:
            opts = {
                "quiet": True, "no_warnings": True, "skip_download": True,
                "extractor_args": self.extractor_args,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

            thumb = None
            for key in ("thumbnail", "thumbnails"):
                url = info.get(key)
                if isinstance(url, list) and url:
                    url = sorted(url, key=lambda t: t.get("width", 0), reverse=True)[0].get("url", "")
                if url and isinstance(url, str):
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=8) as r:
                            thumb = r.read()
                        break
                    except Exception:
                        pass

            self.ready.emit({
                "title":      info.get("title") or info.get("description", "")[:80] or "Sin título",
                "channel":    info.get("uploader") or info.get("creator") or info.get("channel") or "—",
                "duration":   info.get("duration", 0) or 0,
                "view_count": info.get("view_count") or info.get("repost_count") or 0,
                "like_count": info.get("like_count") or 0,
                "thumbnail":  thumb,
                "platform":   info.get("extractor_key", "").lower(),
            })
        except Exception as e:
            self.failed.emit(str(e))


class DownloadWorker(QThread):
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, url, fmt, out_dir, ffmpeg_dir, extractor_args=None):
        super().__init__()
        self.url            = url
        self.fmt            = fmt
        self.out_dir        = out_dir
        self.ffmpeg_dir     = ffmpeg_dir
        self.extractor_args = extractor_args or {}
        self._phase         = 1

    def _hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            done  = d.get("downloaded_bytes", 0)
            spd   = d.get("_speed_str", "").strip()
            eta   = d.get("_eta_str", "").strip()
            chunk = (done / total * 100) if total else 0
            pct   = chunk * 0.80 if self._phase == 1 else 80 + chunk * 0.15
            self.progress.emit(pct, f"Descargando… {chunk:.1f}%  ·  {spd}  ·  ETA {eta}")
        elif d["status"] == "finished":
            self._phase = 2
            self.progress.emit(95, "Procesando archivo…")

    def run(self):
        try:
            outtmpl = os.path.join(self.out_dir, "%(title)s.%(ext)s")
            opts = {
                "format":              self.fmt,
                "outtmpl":             outtmpl,
                "merge_output_format": "mp4",
                "progress_hooks":      [self._hook],
                "extractor_args":      self.extractor_args,
            }
            if self.fmt.startswith("bestaudio"):
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


# ── Helpers de estilo ─────────────────────────────────────────────────────────

def shadow(r=16, ofs=(0, 4), alpha=100):
    e = QGraphicsDropShadowEffect()
    c = QColor("#000000"); c.setAlpha(alpha)
    e.setColor(c); e.setBlurRadius(r); e.setOffset(*ofs)
    return e


def card_style(radius=14):
    return f"""
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: {radius}px;
    """


def input_style(accent):
    return f"""
        QLineEdit, QComboBox {{
            background: {INPUT};
            color: {TEXT};
            border: 1.5px solid {BORDER};
            border-radius: 8px;
            padding: 9px 14px;
            font-size: 13px;
        }}
        QLineEdit:focus, QComboBox:focus {{ border-color: {accent}; }}
        QComboBox::drop-down {{ border: none; width: 28px; }}
        QComboBox::down-arrow {{
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {MUTED};
            margin-right: 10px;
        }}
        QComboBox QAbstractItemView {{
            background: {CARD};
            color: {TEXT};
            selection-background-color: {accent};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 4px;
            outline: none;
        }}
    """


# ── Componentes ───────────────────────────────────────────────────────────────

class Card(QFrame):
    def __init__(self, parent=None, radius=14):
        super().__init__(parent)
        self.setStyleSheet(f"Card {{ {card_style(radius)} }}")
        self.setGraphicsEffect(shadow())


class NavButton(QPushButton):
    def __init__(self, icon, label, accent, parent=None):
        super().__init__(parent)
        self._icon   = icon
        self._label  = label
        self._accent = accent
        self._active = False
        self.setFixedHeight(48)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setCheckable(True)
        self._update_style()

    def setActive(self, v):
        self._active = v
        self.setChecked(v)
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {self._accent}22;
                    color: {self._accent};
                    border: none;
                    border-left: 3px solid {self._accent};
                    border-radius: 0px;
                    text-align: left;
                    padding-left: 20px;
                    font-size: 14px;
                    font-weight: 700;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {MUTED};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    text-align: left;
                    padding-left: 20px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background: {BORDER}44;
                    color: {TEXT};
                }}
            """)
        self.setText(f"  {self._icon}   {self._label}")


class GhostBtn(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {MUTED};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: {BORDER}; color: {TEXT}; }}
        """)


class SectionLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 1px;")


# ── Panel de plataforma ───────────────────────────────────────────────────────

class PlatformPanel(QWidget):
    def __init__(self, platform_key: str, parent=None):
        super().__init__(parent)
        self.pk      = platform_key
        self.cfg     = PLATFORMS[platform_key]
        self.accent  = ACCENT[platform_key]["primary"]
        self.accent2 = ACCENT[platform_key]["secondary"]

        self._info_worker = None
        self._dl_worker   = None
        self._dl_path     = default_video_dir()

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._fetch_info)

        self._build()

    # ── construcción ─────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        root.addWidget(self._make_header())
        root.addWidget(self._make_url_bar())

        center = QHBoxLayout()
        center.setSpacing(14)
        center.addWidget(self._make_preview_card(), 5)
        center.addWidget(self._make_options_card(), 6)
        root.addLayout(center, 1)

        root.addWidget(self._make_progress_section())

    # ── header ────────────────────────────────────────────────────────────────

    def _make_header(self):
        w = QWidget(); r = QHBoxLayout(w)
        r.setContentsMargins(0, 0, 0, 0)

        ico = QLabel(self.cfg["icon"])
        ico.setStyleSheet(f"color: {self.accent}; font-size: 20px;")

        name = QLabel(self.cfg["label"])
        name.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        name.setStyleSheet(f"color: {TEXT};")

        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        ffok  = FFMPEG_DIR is not None
        badge = QLabel("ffmpeg  ✓" if ffok else "ffmpeg  ✗")
        badge.setStyleSheet(f"""
            color: {SUCCESS if ffok else WARNING};
            border: 1px solid {'#4caf5055' if ffok else '#ff980055'};
            border-radius: 6px; padding: 3px 10px;
            font-size: 10px; font-weight: 700;
        """)

        r.addWidget(ico); r.addSpacing(8); r.addWidget(name)
        r.addWidget(spacer); r.addWidget(badge)
        return w

    # ── URL bar ───────────────────────────────────────────────────────────────

    def _make_url_bar(self):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ {card_style(12)} }}")
        card.setGraphicsEffect(shadow(10, (0, 2), 80))

        r = QHBoxLayout(card); r.setContentsMargins(14, 10, 14, 10); r.setSpacing(10)

        lbl = QLabel("URL")
        lbl.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 700;")
        lbl.setFixedWidth(26)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(self.cfg["hint"])
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background: {INPUT}; color: {TEXT};
                border: 1.5px solid {BORDER}; border-radius: 8px;
                padding: 9px 14px; font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {self.accent}; }}
        """)
        self.url_input.textChanged.connect(self._on_url_changed)

        clr = GhostBtn("✕"); clr.setFixedSize(34, 34)
        clr.clicked.connect(self._clear_url)

        prev_btn = QPushButton("  Vista previa")
        prev_btn.setFixedHeight(34)
        prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        prev_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.accent}; color: white;
                border: none; border-radius: 8px;
                padding: 0 16px; font-size: 12px; font-weight: 700;
            }}
            QPushButton:hover {{ background: {self.accent2}; }}
        """)
        prev_btn.clicked.connect(self._fetch_info)

        r.addWidget(lbl); r.addWidget(self.url_input)
        r.addWidget(clr); r.addWidget(prev_btn)
        return card

    # ── preview card ──────────────────────────────────────────────────────────

    def _make_preview_card(self):
        card = Card(radius=14)
        v = QVBoxLayout(card); v.setContentsMargins(16, 16, 16, 16); v.setSpacing(10)

        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setFixedHeight(170)
        self.thumb.setStyleSheet(f"""
            background: {SURFACE}; border-radius: 10px;
            color: {MUTED}; font-size: 30px;
        """)
        self.thumb.setText(self.cfg["icon"])

        self.meta_title = QLabel("Sin video")
        self.meta_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.meta_title.setStyleSheet(f"color: {TEXT};")
        self.meta_title.setWordWrap(True)

        self.meta_channel  = self._meta("Autor / Canal", "—")
        self.meta_duration = self._meta("Duración", "—")
        self.meta_views    = self._meta("Vistas", "—")
        self.meta_likes    = self._meta("Likes", "—")

        self.preview_status = QLabel("")
        self.preview_status.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        self.preview_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v.addWidget(self.thumb)
        v.addWidget(self.meta_title)
        v.addWidget(self.meta_channel)
        v.addWidget(self.meta_duration)
        v.addWidget(self.meta_views)
        v.addWidget(self.meta_likes)
        v.addStretch()
        v.addWidget(self.preview_status)
        return card

    def _meta(self, key, val):
        w = QLabel()
        w.setTextFormat(Qt.TextFormat.RichText)
        w.setWordWrap(True)
        self._set_meta(w, key, val)
        return w

    def _set_meta(self, widget, key, val):
        widget.setText(
            f"<span style='color:{MUTED};font-size:10px;'>{key}</span>"
            f"<br><span style='color:{TEXT};font-size:12px;'>{val}</span>"
        )

    # ── options card ──────────────────────────────────────────────────────────

    def _make_options_card(self):
        card = Card(radius=14)
        v = QVBoxLayout(card); v.setContentsMargins(20, 20, 20, 20); v.setSpacing(10)

        v.addWidget(SectionLabel("FORMATO"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems([f[0] for f in self.cfg["formats"]])
        self.fmt_combo.setStyleSheet(input_style(self.accent))
        v.addWidget(self.fmt_combo)

        v.addSpacing(6)
        v.addWidget(SectionLabel("CARPETA DE DESTINO"))
        row = QHBoxLayout(); row.setSpacing(8)
        self.dest_lbl = QLabel(self._short(self._dl_path))
        self.dest_lbl.setStyleSheet(f"""
            background: {INPUT}; color: {TEXT};
            border: 1.5px solid {BORDER}; border-radius: 8px;
            padding: 9px 14px; font-size: 11px;
        """)
        self.dest_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        browse = GhostBtn("Examinar"); browse.setFixedHeight(38)
        browse.clicked.connect(self._browse)
        row.addWidget(self.dest_lbl); row.addWidget(browse)
        v.addLayout(row)

        v.addStretch()

        self.dl_btn = QPushButton("⬇   Descargar")
        self.dl_btn.setFixedHeight(52)
        self.dl_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.dl_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dl_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {self.accent}, stop:1 {self.accent2});
                color: white; border: none; border-radius: 12px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {self.accent2}, stop:1 {self.accent});
            }}
            QPushButton:disabled {{
                background: {BORDER}; color: {MUTED};
            }}
        """)
        self.dl_btn.clicked.connect(self._start_download)
        v.addWidget(self.dl_btn)

        self.dl_note = QLabel("")
        self.dl_note.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        self.dl_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.dl_note)
        return card

    # ── progress section ──────────────────────────────────────────────────────

    def _make_progress_section(self):
        w = QWidget()
        v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(5)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(7)
        self.progress.setTextVisible(False)
        self.progress.setValue(0)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background: {SURFACE}; border-radius: 3px; border: none; }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {self.accent}, stop:1 {self.accent2});
                border-radius: 3px;
            }}
        """)

        self.status_lbl = QLabel("Listo")
        self.status_lbl.setStyleSheet(f"color: {MUTED}; font-size: 10px;")

        v.addWidget(self.progress)
        v.addWidget(self.status_lbl)
        return w

    # ── lógica preview ────────────────────────────────────────────────────────

    def _on_url_changed(self, text):
        if any(d in text for d in ("youtube.com", "youtu.be", "tiktok.com", "vm.tiktok")):
            self._preview_timer.start(900)
        else:
            self._reset_preview()

    def _clear_url(self):
        self.url_input.clear()
        self._reset_preview()
        self._set_status("Listo", MUTED)

    def _reset_preview(self):
        self.thumb.setPixmap(QPixmap())
        self.thumb.setText(self.cfg["icon"])
        self.meta_title.setText("Sin video")
        self._set_meta(self.meta_channel,  "Autor / Canal", "—")
        self._set_meta(self.meta_duration, "Duración",      "—")
        self._set_meta(self.meta_views,    "Vistas",        "—")
        self._set_meta(self.meta_likes,    "Likes",         "—")
        self.preview_status.setText("")

    def _fetch_info(self):
        url = self.url_input.text().strip()
        if not url:
            return
        if self._info_worker and self._info_worker.isRunning():
            return

        self.preview_status.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
        self.preview_status.setText("Cargando información…")
        self.thumb.setText("⏳")
        self.meta_title.setText("…")

        self._info_worker = InfoWorker(url, self.cfg["extractor_args"])
        self._info_worker.ready.connect(self._on_info_ready)
        self._info_worker.failed.connect(self._on_info_failed)
        self._info_worker.start()

    def _on_info_ready(self, info):
        self.meta_title.setText(info["title"])
        self._set_meta(self.meta_channel, "Autor / Canal", info["channel"])

        secs = int(info["duration"])
        if secs >= 3600:
            dur = f"{secs//3600}h {(secs%3600)//60}m {secs%60:02d}s"
        else:
            dur = f"{secs//60}:{secs%60:02d}"
        self._set_meta(self.meta_duration, "Duración", dur)

        def fmt_num(n):
            if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
            if n >= 1_000:     return f"{n/1_000:.1f}K"
            return str(n)

        self._set_meta(self.meta_views, "Vistas", fmt_num(info["view_count"]))
        self._set_meta(self.meta_likes, "Likes",  fmt_num(info["like_count"]))

        if info["thumbnail"]:
            pix = QPixmap()
            pix.loadFromData(info["thumbnail"])
            pix = pix.scaled(
                self.thumb.width(), self.thumb.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumb.setPixmap(pix)
            self.thumb.setText("")
        else:
            self.thumb.setText(self.cfg["icon"])

        self.preview_status.setStyleSheet(f"color: {SUCCESS}; font-size: 10px;")
        self.preview_status.setText("✓  Vista previa cargada")

    def _on_info_failed(self, err):
        self.thumb.setText("✗")
        self.meta_title.setText("No se pudo obtener el video")
        self.preview_status.setStyleSheet(f"color: {ACCENT[self.pk]['primary']}; font-size: 10px;")
        self.preview_status.setText("Error al cargar el video")

    # ── lógica descarga ───────────────────────────────────────────────────────

    def _browse(self):
        f = QFileDialog.getExistingDirectory(self, "Carpeta de destino", self._dl_path)
        if f:
            self._dl_path = f
            self.dest_lbl.setText(self._short(f))

    def _start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self._set_status("⚠  Ingresa una URL.", WARNING); return
        if self._dl_worker and self._dl_worker.isRunning():
            return

        idx = self.fmt_combo.currentIndex()
        fmt = self.cfg["formats"][idx][1]

        if fmt.startswith("bestaudio") and not FFMPEG_DIR:
            self._set_status("✗  ffmpeg no encontrado — MP3 no disponible.", WARNING); return

        self.dl_btn.setEnabled(False)
        self.progress.setValue(0)
        self.dl_note.setText("")
        self._set_status("Iniciando descarga…", MUTED)

        self._dl_worker = DownloadWorker(
            url, fmt, self._dl_path, FFMPEG_DIR, self.cfg["extractor_args"]
        )
        self._dl_worker.progress.connect(lambda p, t: (self.progress.setValue(int(p)), self._set_status(t, MUTED)))
        self._dl_worker.finished.connect(self._on_finished)
        self._dl_worker.error.connect(self._on_error)
        self._dl_worker.start()

    def _on_finished(self, folder):
        self.progress.setValue(100)
        self._set_status(f"✓  Guardado en: {folder}", SUCCESS)
        self.dl_note.setText("Descarga completada")
        self.dl_btn.setEnabled(True)

    def _on_error(self, msg):
        self.progress.setValue(0)
        self._set_status(f"✗  {msg[:140]}", ACCENT[self.pk]["primary"])
        self.dl_btn.setEnabled(True)

    # ── utilidades ────────────────────────────────────────────────────────────

    def _set_status(self, text, color=MUTED):
        self.status_lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
        self.status_lbl.setText(text)

    @staticmethod
    def _short(path, maxlen=50):
        return path if len(path) <= maxlen else "…" + path[-(maxlen - 1):]


# ── Sidebar ───────────────────────────────────────────────────────────────────

class Sidebar(QWidget):
    platform_changed = pyqtSignal(str)   # "youtube" | "tiktok"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setStyleSheet(f"background: {SIDEBAR}; border-right: 1px solid {BORDER};")

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ── Logo ──────────────────────────────────────────────────────────────
        logo_area = QWidget()
        logo_area.setFixedHeight(80)
        logo_area.setStyleSheet(f"background: {BG};")
        la = QVBoxLayout(logo_area)
        la.setContentsMargins(20, 16, 20, 14)

        app_name = QLabel("Higgs")
        app_name.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        app_name.setStyleSheet("color: #ececf4;")

        sub = QLabel("Video Downloader")
        sub.setStyleSheet(f"color: {MUTED}; font-size: 10px; font-weight: 600; letter-spacing: 1px;")

        la.addWidget(app_name)
        la.addWidget(sub)
        v.addWidget(logo_area)

        # ── Separador ─────────────────────────────────────────────────────────
        sep_lbl = QLabel("PLATAFORMAS")
        sep_lbl.setStyleSheet(f"""
            color: {MUTED}; font-size: 9px; font-weight: 700;
            letter-spacing: 1.5px; padding: 14px 20px 6px 20px;
        """)
        v.addWidget(sep_lbl)

        # ── Botones de navegación ─────────────────────────────────────────────
        self._btns = {}
        for key in ("youtube", "tiktok"):
            cfg = PLATFORMS[key]
            btn = NavButton(cfg["icon"], cfg["label"], ACCENT[key]["primary"])
            btn.clicked.connect(lambda _, k=key: self._select(k))
            self._btns[key] = btn
            v.addWidget(btn)

        v.addStretch()

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QWidget()
        fl = QVBoxLayout(footer); fl.setContentsMargins(20, 10, 20, 16); fl.setSpacing(2)
        author = QLabel("Jose Alexis Correa Valencia")
        author.setStyleSheet(f"color: {MUTED}; font-size: 9px; font-weight: 600;")
        author.setWordWrap(True)
        version = QLabel("v3.0  ·  Freeware")
        version.setStyleSheet(f"color: {BORDER}; font-size: 9px;")
        fl.addWidget(author); fl.addWidget(version)
        v.addWidget(footer)

        self._select("youtube")

    def _select(self, key):
        for k, b in self._btns.items():
            b.setActive(k == key)
        self.platform_changed.emit(key)


# ── Ventana principal ─────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Higgs Video Downloader")
        self.setMinimumSize(880, 620)
        self.resize(1020, 680)
        self._apply_palette()
        self._build()

    def _apply_palette(self):
        self.setStyleSheet(f"QMainWindow, QWidget {{ background: {BG}; color: {TEXT}; }}")
        pal = QPalette()
        for role, col in [
            (QPalette.ColorRole.Window,        BG),
            (QPalette.ColorRole.WindowText,    TEXT),
            (QPalette.ColorRole.Base,          INPUT),
            (QPalette.ColorRole.Text,          TEXT),
            (QPalette.ColorRole.Button,        CARD),
            (QPalette.ColorRole.ButtonText,    TEXT),
            (QPalette.ColorRole.Highlight,     ACCENT["youtube"]["primary"]),
            (QPalette.ColorRole.HighlightedText, "#ffffff"),
        ]:
            pal.setColor(role, QColor(col))
        QApplication.instance().setPalette(pal)

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.sidebar = Sidebar()
        self.stack   = QStackedWidget()
        self.stack.setStyleSheet(f"background: {BG};")

        self._panels = {}
        for key in ("youtube", "tiktok"):
            panel = PlatformPanel(key)
            self._panels[key] = panel
            self.stack.addWidget(panel)

        self.sidebar.platform_changed.connect(self._switch)
        self._switch("youtube")

        row.addWidget(self.sidebar)
        row.addWidget(self.stack, 1)

    def _switch(self, key):
        self.stack.setCurrentWidget(self._panels[key])


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
