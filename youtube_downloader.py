import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import yt_dlp


def _find_ffmpeg():
    """
    Busca ffmpeg/ffprobe en:
    1. Directorio del ejecutable (bundled con PyInstaller)
    2. Directorio del script (desarrollo)
    Retorna la ruta al directorio o None si no se encuentra.
    """
    # Cuando está empaquetado con PyInstaller, los binarios van a _MEIPASS
    if getattr(sys, "frozen", False):
        candidates = [sys._MEIPASS, os.path.dirname(sys.executable)]
    else:
        candidates = [os.path.dirname(os.path.abspath(__file__))]

    for path in candidates:
        if os.path.isfile(os.path.join(path, "ffmpeg.exe")):
            return path
    return None


FFMPEG_DIR = _find_ffmpeg()


class YoutubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("680x540")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        self.download_path = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.url_var = tk.StringVar()
        self.format_var = tk.StringVar(value="Mejor calidad (video+audio)")
        self.status_var = tk.StringVar(value="Listo para descargar")
        self.progress_var = tk.DoubleVar(value=0)
        self.is_downloading = False

        self._build_ui()

        # Advertencia si ffmpeg no está disponible
        if FFMPEG_DIR is None:
            self._set_status(
                "Advertencia: ffmpeg no encontrado — MP3 y mezcla de pistas no disponibles",
                color="#ff9800",
            )

    def _build_ui(self):
        BG = "#1a1a2e"
        CARD = "#16213e"
        ACCENT = "#e94560"
        TEXT = "#eaeaea"
        MUTED = "#888"
        ENTRY_BG = "#0f3460"

        # Header
        header = tk.Frame(self.root, bg=ACCENT, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = tk.Frame(header, bg=ACCENT)
        header_inner.pack(expand=True)
        tk.Label(
            header_inner,
            text="YouTube Downloader",
            font=("Segoe UI", 18, "bold"),
            bg=ACCENT, fg="white",
        ).pack(side="left")

        # Indicador ffmpeg
        ffmpeg_color = "#4caf50" if FFMPEG_DIR else "#ff9800"
        ffmpeg_text = "ffmpeg OK" if FFMPEG_DIR else "sin ffmpeg"
        tk.Label(
            header_inner,
            text=f"  [{ffmpeg_text}]",
            font=("Segoe UI", 9),
            bg=ACCENT, fg=ffmpeg_color,
        ).pack(side="left", pady=(8, 0))

        # Main card
        card = tk.Frame(self.root, bg=CARD, padx=30, pady=20)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        def label(parent, text, **kw):
            return tk.Label(
                parent, text=text, bg=CARD, fg=TEXT,
                font=("Segoe UI", 10), anchor="w", **kw
            )

        # URL
        label(card, "URL del video de YouTube:").pack(fill="x", pady=(0, 4))
        url_frame = tk.Frame(card, bg=CARD)
        url_frame.pack(fill="x", pady=(0, 14))
        self.url_entry = tk.Entry(
            url_frame, textvariable=self.url_var,
            bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
            font=("Segoe UI", 11), relief="flat", bd=6,
        )
        self.url_entry.pack(side="left", fill="x", expand=True)
        tk.Button(
            url_frame, text="✕", command=lambda: self.url_var.set(""),
            bg=ENTRY_BG, fg=MUTED, relief="flat", cursor="hand2",
            font=("Segoe UI", 11), padx=8,
        ).pack(side="left")

        # Formato
        label(card, "Formato de descarga:").pack(fill="x", pady=(0, 4))
        formats = [
            "Mejor calidad (video+audio)",
            "1080p (video+audio)",
            "720p (video+audio)",
            "480p (video+audio)",
            "360p (video+audio)",
            "Solo audio (MP3)",
        ]
        self.format_combo = ttk.Combobox(
            card, textvariable=self.format_var, values=formats,
            state="readonly", font=("Segoe UI", 10),
        )
        self.format_combo.pack(fill="x", pady=(0, 14))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TCombobox",
            fieldbackground=ENTRY_BG,
            background=ENTRY_BG,
            foreground=TEXT,
            selectbackground=ACCENT,
            borderwidth=0,
        )

        # Carpeta de destino
        label(card, "Carpeta de destino:").pack(fill="x", pady=(0, 4))
        path_frame = tk.Frame(card, bg=CARD)
        path_frame.pack(fill="x", pady=(0, 20))
        tk.Entry(
            path_frame, textvariable=self.download_path,
            bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
            font=("Segoe UI", 10), relief="flat", bd=6, state="readonly",
        ).pack(side="left", fill="x", expand=True)
        tk.Button(
            path_frame, text="Examinar",
            command=self._browse_folder,
            bg=ACCENT, fg="white", relief="flat", cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=12, pady=4,
        ).pack(side="left", padx=(6, 0))

        # Botón descargar
        self.download_btn = tk.Button(
            card, text="⬇  Descargar",
            command=self._start_download,
            bg=ACCENT, fg="white", relief="flat", cursor="hand2",
            font=("Segoe UI", 13, "bold"), pady=10,
        )
        self.download_btn.pack(fill="x", pady=(0, 16))

        # Barra de progreso
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=ENTRY_BG,
            background=ACCENT,
            borderwidth=0,
            thickness=12,
        )
        self.progress_bar = ttk.Progressbar(
            card, variable=self.progress_var,
            maximum=100, style="Custom.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill="x", pady=(0, 8))

        # Estado
        self.status_label = tk.Label(
            card, textvariable=self.status_var,
            bg=CARD, fg=MUTED, font=("Segoe UI", 9), anchor="w",
        )
        self.status_label.pack(fill="x")

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path.get())
        if folder:
            self.download_path.set(folder)

    def _get_ydl_opts(self):
        fmt = self.format_var.get()
        out_template = os.path.join(self.download_path.get(), "%(title)s.%(ext)s")

        base = {
            "progress_hooks": [self._progress_hook],
        }
        if FFMPEG_DIR:
            base["ffmpeg_location"] = FFMPEG_DIR

        if fmt == "Solo audio (MP3)":
            if not FFMPEG_DIR:
                raise RuntimeError(
                    "ffmpeg es requerido para convertir a MP3.\n"
                    "Coloca ffmpeg.exe y ffprobe.exe junto al ejecutable."
                )
            return {
                **base,
                "format": "bestaudio/best",
                "outtmpl": out_template,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

        # Priorizar mp4+m4a (H.264+AAC): se mezclan en MP4 sin transcodificación.
        # Fallback 1: cualquier video+audio separados (ffmpeg los mezcla).
        # Fallback 2: mejor stream pre-mezclado disponible.
        format_map = {
            "Mejor calidad (video+audio)": (
                "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
                "/bestvideo+bestaudio/best"
            ),
            "1080p (video+audio)": (
                "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]"
                "/bestvideo[height<=1080]+bestaudio/best[height<=1080]"
            ),
            "720p (video+audio)": (
                "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]"
                "/bestvideo[height<=720]+bestaudio/best[height<=720]"
            ),
            "480p (video+audio)": (
                "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]"
                "/bestvideo[height<=480]+bestaudio/best[height<=480]"
            ),
            "360p (video+audio)": (
                "bestvideo[ext=mp4][height<=360]+bestaudio[ext=m4a]"
                "/bestvideo[height<=360]+bestaudio/best[height<=360]"
            ),
        }
        return {
            **base,
            "format": format_map.get(fmt, "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"),
            "outtmpl": out_template,
            "merge_output_format": "mp4",
        }

    def _progress_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("_speed_str", "").strip()
            eta = d.get("_eta_str", "").strip()
            if total:
                pct = downloaded / total * 100
                self.progress_var.set(pct)
                self._set_status(f"Descargando... {pct:.1f}%  |  {speed}  |  ETA: {eta}")
        elif d["status"] == "finished":
            self.progress_var.set(100)
            self._set_status("Procesando archivo...")

    def _set_status(self, msg, color="#888"):
        self.root.after(0, lambda: (
            self.status_var.set(msg),
            self.status_label.configure(fg=color),
        ))

    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Sin URL", "Por favor ingresa la URL del video.")
            return
        if self.is_downloading:
            return

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="Descargando...")
        self.progress_var.set(0)
        self._set_status("Iniciando descarga...")

        threading.Thread(target=self._download, daemon=True).start()

    def _download(self):
        try:
            opts = self._get_ydl_opts()
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url_var.get().strip()])
            self._set_status(
                f"¡Descarga completada! Guardado en: {self.download_path.get()}",
                color="#4caf50",
            )
        except RuntimeError as e:
            msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("ffmpeg no encontrado", msg))
            self._set_status("Error: ffmpeg requerido", color="#e94560")
        except yt_dlp.utils.DownloadError as e:
            # Extraer mensaje limpio sin el prefijo verbose de yt-dlp
            msg = str(e)
            short = msg.split("ERROR:")[-1].strip() if "ERROR:" in msg else msg
            self._set_status(f"Error: {short}", color="#e94560")
            self.root.after(0, lambda: messagebox.showerror("Error de descarga", short))
        except Exception as e:
            msg = str(e)
            self._set_status(f"Error inesperado: {msg}", color="#e94560")
            self.root.after(0, lambda: messagebox.showerror("Error inesperado", msg))
        finally:
            self.is_downloading = False
            self.root.after(0, lambda: self.download_btn.configure(
                state="normal", text="⬇  Descargar"
            ))


if __name__ == "__main__":
    root = tk.Tk()
    app = YoutubeDownloader(root)
    root.mainloop()
