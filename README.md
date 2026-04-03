# Higgs Video Downloader

**Dashboard de escritorio para descargar videos de YouTube y TikTok — sin instalar nada adicional.**

Desarrollado por **Jose Alexis Correa Valencia** · Freeware de uso irrestricto

---

## Descarga

➡️ Ve a [**Releases**](../../releases/latest) y descarga `Higgs.Video.Downloader.exe`

> No requiere Python ni ffmpeg instalados. Todo está incluido en el ejecutable.

---

## Características

| Función | Detalle |
|---|---|
| Dashboard con sidebar | Cambia entre YouTube y TikTok con un clic |
| YouTube | Mejor calidad, 1080p, 720p, 480p, 360p en MP4 |
| TikTok | Descarga sin marca de agua |
| Descarga de audio | MP3 a 192 kbps (ambas plataformas) |
| Vista previa automática | Miniatura, título, canal, duración, vistas y likes |
| ffmpeg integrado | Mezcla de pistas y conversión sin instalar nada |
| Directorio por defecto | Carpeta Videos del usuario |
| Barra de progreso | Fases diferenciadas: descarga / mezcla |
| Sin consola | Ventana limpia, sin terminal visible |

---

## Interfaz — Dashboard

```
┌────────────┬──────────────────────────────────────────────────────┐
│            │  ▶ YouTube                    ffmpeg ✓               │
│  Higgs     ├────────────────────────────────────────────────────  │
│  Video     │  URL │ [ https://youtube.com/...         ✕ ] [Preview]│
│  Downloader├──────────────────┬─────────────────────────────────  │
│            │                  │  FORMATO                          │
│ PLATAFORMAS│  [ Miniatura ]   │  [ Mejor calidad (video+audio) ▼] │
│            │                  │                                   │
│ ▶ YouTube  │  Título          │  CARPETA DE DESTINO               │
│ ♪ TikTok   │  Autor: @canal   │  [ ~/Videos          ] [Examinar] │
│            │  Duración: 3:32  │                                   │
│            │  Vistas: 1.2M    │  [      ⬇  Descargar          ]  │
│            │  Likes: 45K      │                                   │
│            ├──────────────────┴─────────────────────────────────  │
│ v3.0       │  ████████████████░░░  72%  · 8.2 MB/s · ETA 4s      │
└────────────┴──────────────────────────────────────────────────────┘
```

---

## Formatos disponibles

### YouTube
- **Mejor calidad** — mayor resolución disponible, fusionado en MP4
- **1080p / 720p / 480p / 360p** — resolución específica en MP4
- **Solo audio (MP3)** — extrae y convierte a MP3 192 kbps

### TikTok
- **Alta calidad (sin marca de agua)** — descarga limpia sin watermark
- **Solo audio (MP3)** — extrae el audio del video

---

## Uso

1. Descarga `Higgs.Video.Downloader.exe` desde [Releases](../../releases/latest)
2. Ejecuta el archivo — no requiere instalación
3. Selecciona la plataforma en la sidebar (YouTube o TikTok)
4. Pega la URL — la vista previa se carga automáticamente
5. Selecciona el formato deseado
6. Haz clic en **⬇ Descargar**

---

## Construcción desde el código fuente

### Requisitos

```bash
pip install yt-dlp pyinstaller PyQt6
```

Coloca `ffmpeg.exe` y `ffprobe.exe` en el mismo directorio que `youtube_downloader.py`.

### Ejecutar sin compilar

```bash
python youtube_downloader.py
```

### Compilar el ejecutable

```bash
pyinstaller --onefile --windowed --name "Higgs Video Downloader" \
  --add-binary "ffmpeg.exe;." \
  --add-binary "ffprobe.exe;." \
  youtube_downloader.py
```

---

## Tecnologías utilizadas

| Librería | Propósito |
|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Descarga de YouTube y TikTok |
| [ffmpeg](https://ffmpeg.org/) | Mezcla de streams y conversión de audio |
| [PyQt6](https://pypi.org/project/PyQt6/) | Interfaz gráfica (dashboard) |
| [PyInstaller](https://pyinstaller.org/) | Empaquetado en ejecutable Windows |

---

## Licencia

**Freeware de uso irrestricto** — Copyright © 2026 Jose Alexis Correa Valencia

Consulta el archivo [LICENSE](LICENSE) para los términos completos.

---

## Autor

**Jose Alexis Correa Valencia**
📧 jalexiscv@gmail.com
🐙 [@jalexiscv](https://github.com/jalexiscv)
