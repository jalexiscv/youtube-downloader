import sys
import os
import threading
import urllib.request

import yt_dlp
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QPropertyAnimation,
    QEasingCurve, QObject
)
from PyQt6.QtGui import (
    QFont, QPixmap, QColor, QPalette, QIcon, QCursor, QPainter,
    QLinearGradient, QBrush
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QProgressBar,
    QFileDialog, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
    QScrollArea
)


# ─── ffmpeg auto-detect ───────────────────────────────────────────────────────

def _find_ffmpeg():
    if getattr(sys, "frozen", False):
        candidates = [sys._MEIPASS, os.path.dirname(sys.executable)]
    else:
        candidates = [os.path.dirname(os.path.abspath(__file__))]
    for path in candidates:
        if os.path.isfile(os.path.join(path, "ffmpeg.exe")):
            return path
    return None

FFMPEG_DIR = _find_ffmpeg()


# ─── Colores / tema ───────────────────────────────────────────────────────────

C = {
    "bg":        "#0d0d1a",
    "surface":   "#12122a",
    "card":      "#1a1a35",
    "border":    "#2a2a4a",
    "accent":    "#e94560",
    "accent2":   "#ff6b81",
    "text":      "#f0f0f0",
    "muted":     "#8080a0",
    "success":   "#4caf50",
    "warning":   "#ff9800",
    "input_bg":  "#1e1e3a",
}


# ─── Workers ──────────────────────────────────────────────────────────────────

class InfoWorker(QThread):
    """Obtiene metadatos + thumbnail en un hilo separado."""
    ready   = pyqtSignal(dict)
    failed  = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

            thumbnail_data = None
            thumb_url = info.get("thumbnail") or ""
            if thumb_url:
                try:
                    req = urllib.request.Request(
                        thumb_url,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    with urllib.request.urlopen(req, timeout=8) as r:
                        thumbnail_data = r.read()
                except Exception:
                    pass

            self.ready.emit({
                "title":     info.get("title", "Sin título"),
                "channel":   info.get("uploader") or info.get("channel", "—"),
                "duration":  info.get("duration", 0),
                "view_count": info.get("view_count", 0),
                "thumbnail": thumbnail_data,
            })
        except Exception as e:
            self.failed.emit(str(e))


class DownloadWorker(QThread):
    """Ejecuta la descarga y emite señales de progreso."""
    progress = pyqtSignal(float, str)   # pct, status_text
    finished = pyqtSignal(str)          # ruta destino
    error    = pyqtSignal(str)

    def __init__(self, url, fmt_string, out_dir, ffmpeg_dir):
        super().__init__()
        self.url        = url
        self.fmt_string = fmt_string
        self.out_dir    = out_dir
        self.ffmpeg_dir = ffmpeg_dir
        self._phase     = 1   # 1 = video, 2 = audio

    def _hook(self, d):
        if d["status"] == "downloading":
            total     = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            done      = d.get("downloaded_bytes", 0)
            speed     = d.get("_speed_str", "").strip()
            eta       = d.get("_eta_str", "").strip()
            pct_chunk = (done / total * 100) if total else 0

            # Fase 1 ocupa 0-80%, fase 2 (audio) ocupa 80-95%
            if self._phase == 1:
                pct = pct_chunk * 0.80
            else:
                pct = 80 + pct_chunk * 0.15

            self.progress.emit(pct, f"Descargando... {pct_chunk:.1f}%  ·  {speed}  ·  ETA {eta}")

        elif d["status"] == "finished":
            self._phase = 2
            self.progress.emit(95, "Mezclando pistas con ffmpeg…")

    def run(self):
        try:
            outtmpl = os.path.join(self.out_dir, "%(title)s.%(ext)s")
            opts = {
                "format":               self.fmt_string,
                "outtmpl":              outtmpl,
                "merge_output_format":  "mp4",
                "progress_hooks":       [self._hook],
            }
            if self.fmt_string.startswith("bestaudio"):
                opts["postprocessors"] = [{
                    "key":              "FFmpegExtractAudio",
                    "preferredcodec":   "mp3",
                    "preferredquality": "192",
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
            short = msg.split("ERROR:")[-1].strip() if "ERROR:" in msg else msg
            self.error.emit(short)


# ─── Componentes UI ───────────────────────────────────────────────────────────

def shadow(radius=18, color="#000000", opacity=120, offset=(0, 4)):
    e = QGraphicsDropShadowEffect()
    c = QColor(color)
    c.setAlpha(opacity)
    e.setColor(c)
    e.setBlurRadius(radius)
    e.setOffset(*offset)
    return e


class Card(QFrame):
    def __init__(self, parent=None, radius=16):
        super().__init__(parent)
        self.setStyleSheet(f"""
            Card {{
                background: {C['card']};
                border: 1px solid {C['border']};
                border-radius: {radius}px;
            }}
        """)
        self.setGraphicsEffect(shadow())


class IconButton(QPushButton):
    def __init__(self, text, color=None, parent=None):
        super().__init__(text, parent)
        bg = color or C["accent"]
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {C['accent2']};
            }}
            QPushButton:disabled {{
                background: {C['border']};
                color: {C['muted']};
            }}
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


class GhostButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['muted']};
                border: 1px solid {C['border']};
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {C['border']};
                color: {C['text']};
            }}
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


# ─── Ventana principal ────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    FORMATS = [
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
        ("Solo audio  (MP3 192 kbps)",
         "bestaudio/best"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Downloader")
        self.setMinimumSize(820, 620)
        self.resize(860, 660)
        self._apply_theme()
        self._build_ui()

        self._info_worker    = None
        self._dl_worker      = None
        self._preview_timer  = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._fetch_info)
        self._download_path  = os.path.expanduser("~/Downloads")

    # ── tema global ──────────────────────────────────────────────────────────

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {C['bg']}; color: {C['text']}; }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: {C['surface']}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['border']}; border-radius: 3px;
            }}
        """)

    # ── construcción UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(24, 24, 24, 24)
        main.setSpacing(16)

        main.addWidget(self._make_header())
        main.addWidget(self._make_url_bar())

        # Área central: preview izquierda + opciones derecha
        center = QHBoxLayout()
        center.setSpacing(16)
        center.addWidget(self._make_preview_panel(), 2)
        center.addWidget(self._make_options_panel(), 3)
        main.addLayout(center, 1)

        main.addWidget(self._make_progress_bar())

    # ── header ────────────────────────────────────────────────────────────────

    def _make_header(self):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)

        icon = QLabel("▶")
        icon.setStyleSheet(f"color: {C['accent']}; font-size: 22px;")

        title = QLabel("YouTube  Downloader")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C['text']};")

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        ffmpeg_ok = FFMPEG_DIR is not None
        badge_text = "ffmpeg  ✓" if ffmpeg_ok else "ffmpeg  ✗"
        badge_color = C["success"] if ffmpeg_ok else C["warning"]
        badge = QLabel(badge_text)
        badge.setStyleSheet(f"""
            background: transparent;
            color: {badge_color};
            border: 1px solid {badge_color};
            border-radius: 6px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 600;
        """)

        author = QLabel("Jose Alexis Correa Valencia")
        author.setStyleSheet(f"color: {C['muted']}; font-size: 11px;")

        row.addWidget(icon)
        row.addSpacing(8)
        row.addWidget(title)
        row.addWidget(spacer)
        row.addWidget(badge)
        row.addSpacing(14)
        row.addWidget(author)
        return w

    # ── barra URL ─────────────────────────────────────────────────────────────

    def _make_url_bar(self):
        card = Card(radius=12)
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(10)

        lbl = QLabel("URL")
        lbl.setStyleSheet(f"color: {C['muted']}; font-weight: 700; font-size: 12px;")
        lbl.setFixedWidth(28)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Pega aquí el enlace de YouTube…")
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C['input_bg']};
                color: {C['text']};
                border: 1.5px solid {C['border']};
                border-radius: 8px;
                padding: 9px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {C['accent']};
            }}
        """)
        self.url_input.textChanged.connect(self._on_url_changed)

        self.clear_btn = GhostButton("✕")
        self.clear_btn.setFixedSize(36, 36)
        self.clear_btn.clicked.connect(self._clear_url)

        self.preview_btn = IconButton("  Vista previa")
        self.preview_btn.setFixedHeight(36)
        self.preview_btn.clicked.connect(self._fetch_info)

        row.addWidget(lbl)
        row.addWidget(self.url_input)
        row.addWidget(self.clear_btn)
        row.addWidget(self.preview_btn)
        return card

    # ── panel preview ─────────────────────────────────────────────────────────

    def _make_preview_panel(self):
        card = Card(radius=16)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(12)

        # Miniatura
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setFixedHeight(180)
        self.thumb_label.setStyleSheet(f"""
            background: {C['surface']};
            border-radius: 10px;
            color: {C['muted']};
            font-size: 28px;
        """)
        self.thumb_label.setText("🎬")

        # Info
        self.title_label = QLabel("Sin video")
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {C['text']};")
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.channel_label = self._meta_label("Canal", "—")
        self.duration_label = self._meta_label("Duración", "—")
        self.views_label = self._meta_label("Vistas", "—")

        # Spinner / estado
        self.preview_status = QLabel("")
        self.preview_status.setStyleSheet(f"color: {C['muted']}; font-size: 11px;")
        self.preview_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        vbox.addWidget(self.thumb_label)
        vbox.addWidget(self.title_label)
        vbox.addWidget(self.channel_label)
        vbox.addWidget(self.duration_label)
        vbox.addWidget(self.views_label)
        vbox.addStretch()
        vbox.addWidget(self.preview_status)
        return card

    def _meta_label(self, key, val):
        w = QLabel(f"<span style='color:{C['muted']};font-size:11px;'>{key}:</span>"
                   f"  <span style='color:{C['text']};font-size:12px;'>{val}</span>")
        w.setTextFormat(Qt.TextFormat.RichText)
        w.setWordWrap(True)
        return w

    def _update_meta(self, key_widget, key, val):
        key_widget.setText(
            f"<span style='color:{C['muted']};font-size:11px;'>{key}:</span>"
            f"  <span style='color:{C['text']};font-size:12px;'>{val}</span>"
        )

    # ── panel opciones ────────────────────────────────────────────────────────

    def _make_options_panel(self):
        card = Card(radius=16)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.setSpacing(14)

        # Formato
        vbox.addWidget(self._section_label("Formato de descarga"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems([f[0] for f in self.FORMATS])
        self.fmt_combo.setStyleSheet(f"""
            QComboBox {{
                background: {C['input_bg']};
                color: {C['text']};
                border: 1.5px solid {C['border']};
                border-radius: 8px;
                padding: 9px 14px;
                font-size: 13px;
            }}
            QComboBox:focus {{ border-color: {C['accent']}; }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {C['muted']};
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background: {C['card']};
                color: {C['text']};
                selection-background-color: {C['accent']};
                border: 1px solid {C['border']};
                border-radius: 8px;
                padding: 4px;
            }}
        """)

        # Carpeta destino
        vbox.addWidget(self._section_label("Carpeta de destino"))
        dest_row = QHBoxLayout()
        dest_row.setSpacing(8)
        self.dest_label = QLabel(os.path.expanduser("~/Downloads"))
        self.dest_label.setStyleSheet(f"""
            background: {C['input_bg']};
            color: {C['text']};
            border: 1.5px solid {C['border']};
            border-radius: 8px;
            padding: 9px 14px;
            font-size: 12px;
        """)
        self.dest_label.setWordWrap(False)
        self.dest_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        browse_btn = GhostButton("Examinar")
        browse_btn.setFixedHeight(38)
        browse_btn.clicked.connect(self._browse)
        dest_row.addWidget(self.dest_label)
        dest_row.addWidget(browse_btn)

        # Botón descargar
        self.dl_btn = QPushButton("⬇   Descargar")
        self.dl_btn.setFixedHeight(52)
        self.dl_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.dl_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dl_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['accent']}, stop:1 #c0392b);
                color: white;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['accent2']}, stop:1 {C['accent']});
            }}
            QPushButton:disabled {{
                background: {C['border']};
                color: {C['muted']};
            }}
        """)
        self.dl_btn.clicked.connect(self._start_download)

        # Info extra
        self.dl_info = QLabel("")
        self.dl_info.setStyleSheet(f"color: {C['muted']}; font-size: 11px;")
        self.dl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dl_info.setWordWrap(True)

        vbox.addWidget(self.fmt_combo)
        vbox.addSpacing(4)
        vbox.addWidget(self._section_label("Carpeta de destino"))
        vbox.addLayout(dest_row)
        vbox.addStretch()
        vbox.addWidget(self.dl_btn)
        vbox.addWidget(self.dl_info)
        return card

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['muted']}; font-size: 11px; font-weight: 700;")
        return lbl

    # ── barra de progreso ─────────────────────────────────────────────────────

    def _make_progress_bar(self):
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setTextVisible(False)
        self.progress.setValue(0)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background: {C['surface']};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['accent']}, stop:1 #ff6b35);
                border-radius: 4px;
            }}
        """)

        self.status_lbl = QLabel("Listo para descargar")
        self.status_lbl.setStyleSheet(f"color: {C['muted']}; font-size: 11px;")

        vbox.addWidget(self.progress)
        vbox.addWidget(self.status_lbl)
        return w

    # ── lógica URL / preview ──────────────────────────────────────────────────

    def _on_url_changed(self, text):
        text = text.strip()
        if "youtube.com" in text or "youtu.be" in text:
            self._preview_timer.start(900)   # espera 900ms tras dejar de escribir
        else:
            self._reset_preview()

    def _clear_url(self):
        self.url_input.clear()
        self._reset_preview()

    def _reset_preview(self):
        self.thumb_label.setText("🎬")
        self.thumb_label.setPixmap(QPixmap())
        self.title_label.setText("Sin video")
        self._update_meta(self.channel_label,  "Canal",    "—")
        self._update_meta(self.duration_label, "Duración", "—")
        self._update_meta(self.views_label,    "Vistas",   "—")
        self.preview_status.setText("")

    def _fetch_info(self):
        url = self.url_input.text().strip()
        if not url:
            return
        if self._info_worker and self._info_worker.isRunning():
            return

        self.preview_status.setText("Cargando información…")
        self.title_label.setText("…")
        self._update_meta(self.channel_label,  "Canal",    "—")
        self._update_meta(self.duration_label, "Duración", "—")
        self._update_meta(self.views_label,    "Vistas",   "—")
        self.thumb_label.setText("⏳")

        self._info_worker = InfoWorker(url)
        self._info_worker.ready.connect(self._on_info_ready)
        self._info_worker.failed.connect(self._on_info_failed)
        self._info_worker.start()

    def _on_info_ready(self, info):
        self.title_label.setText(info["title"])

        self._update_meta(self.channel_label, "Canal", info["channel"])

        secs = info["duration"] or 0
        dur  = f"{secs//3600}h {(secs%3600)//60}m {secs%60}s" if secs >= 3600 \
               else f"{secs//60}:{secs%60:02d}"
        self._update_meta(self.duration_label, "Duración", dur)

        views = info["view_count"]
        if views >= 1_000_000:
            views_str = f"{views/1_000_000:.1f}M"
        elif views >= 1_000:
            views_str = f"{views/1_000:.1f}K"
        else:
            views_str = str(views)
        self._update_meta(self.views_label, "Vistas", views_str)

        if info["thumbnail"]:
            pix = QPixmap()
            pix.loadFromData(info["thumbnail"])
            pix = pix.scaled(
                self.thumb_label.width(),
                self.thumb_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumb_label.setPixmap(pix)
            self.thumb_label.setText("")
        else:
            self.thumb_label.setText("🎬")

        self.preview_status.setText("✓  Vista previa cargada")
        self.preview_status.setStyleSheet(f"color: {C['success']}; font-size: 11px;")

    def _on_info_failed(self, err):
        self.thumb_label.setText("✗")
        self.preview_status.setText("No se pudo cargar el video")
        self.preview_status.setStyleSheet(f"color: {C['accent']}; font-size: 11px;")
        self.title_label.setText("Error al obtener información")

    # ── lógica descarga ───────────────────────────────────────────────────────

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Carpeta de destino", self._download_path)
        if folder:
            self._download_path = folder
            short = folder if len(folder) < 45 else "…" + folder[-42:]
            self.dest_label.setText(short)

    def _start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.status_lbl.setText("⚠  Ingresa una URL primero.")
            return
        if self._dl_worker and self._dl_worker.isRunning():
            return

        idx        = self.fmt_combo.currentIndex()
        fmt_string = self.FORMATS[idx][1]

        if fmt_string.startswith("bestaudio") and not FFMPEG_DIR:
            self.status_lbl.setText("✗  ffmpeg no encontrado — MP3 no disponible.")
            return

        self.dl_btn.setEnabled(False)
        self.progress.setValue(0)
        self.status_lbl.setText("Iniciando descarga…")
        self.dl_info.setText("")

        self._dl_worker = DownloadWorker(url, fmt_string, self._download_path, FFMPEG_DIR)
        self._dl_worker.progress.connect(self._on_progress)
        self._dl_worker.finished.connect(self._on_finished)
        self._dl_worker.error.connect(self._on_error)
        self._dl_worker.start()

    def _on_progress(self, pct, text):
        self.progress.setValue(int(pct))
        self.status_lbl.setText(text)

    def _on_finished(self, folder):
        self.progress.setValue(100)
        self.status_lbl.setStyleSheet(f"color: {C['success']}; font-size: 11px;")
        self.status_lbl.setText(f"✓  Guardado en: {folder}")
        self.dl_info.setText("Descarga completada con éxito")
        self.dl_btn.setEnabled(True)

    def _on_error(self, msg):
        self.progress.setValue(0)
        self.status_lbl.setStyleSheet(f"color: {C['accent']}; font-size: 11px;")
        self.status_lbl.setText(f"✗  {msg[:120]}")
        self.dl_btn.setEnabled(True)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Paleta base oscura para los widgets nativos (menús, scrollbars, etc.)
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(C["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Base,            QColor(C["input_bg"]))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(C["surface"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor(C["card"]))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Text,            QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Button,          QColor(C["card"]))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(C["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
