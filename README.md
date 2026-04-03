# YouTube Downloader

**Aplicación de escritorio para descargar videos y audio de YouTube — sin instalar nada adicional.**

Desarrollado por **Jose Alexis Correa Valencia** · Freeware de uso irrestricto

---

## Descarga

➡️ Ve a [**Releases**](../../releases/latest) y descarga `YouTube Downloader.exe`

> No requiere Python ni ffmpeg instalados. Todo está incluido en el ejecutable.

---

## Características

| Función | Detalle |
|---|---|
| Descarga de video | Mejor calidad, 1080p, 720p, 480p, 360p en MP4 |
| Descarga de audio | MP3 a 192 kbps |
| ffmpeg integrado | Mezcla de pistas y conversión sin instalar nada |
| Carpeta destino | Seleccionable desde la interfaz |
| Barra de progreso | Velocidad y ETA en tiempo real |
| Sin consola | Aplicación de ventana, sin terminal visible |

---

## Capturas

```
┌─────────────────────────────────────────┐
│         YouTube Downloader  [ffmpeg OK] │  ← header rojo
├─────────────────────────────────────────┤
│ URL del video de YouTube:               │
│ [ https://youtube.com/watch?v=...    ✕ ]│
│                                         │
│ Formato de descarga:                    │
│ [ Mejor calidad (video+audio)        ▼ ]│
│                                         │
│ Carpeta de destino:                     │
│ [ C:/Users/.../Downloads    ] [Examinar]│
│                                         │
│ [        ⬇  Descargar               ]  │
│ ████████████████░░░░░░  72.3%           │
│ Descargando... 72.3% | 8.2 MiB/s | ETA: 4s │
└─────────────────────────────────────────┘
```

---

## Formatos disponibles

- **Mejor calidad (video+audio)** — descarga el stream de mayor resolución disponible, fusionado en MP4
- **1080p / 720p / 480p / 360p** — resolución específica fusionada en MP4
- **Solo audio (MP3)** — extrae el audio y lo convierte a MP3 192 kbps

---

## Uso

1. Descarga `YouTube Downloader.exe` desde [Releases](../../releases/latest)
2. Ejecuta el archivo (doble clic) — no requiere instalación
3. Pega la URL del video de YouTube
4. Selecciona el formato deseado
5. Elige la carpeta de destino (por defecto `~/Downloads`)
6. Haz clic en **⬇ Descargar**

---

## Construcción desde el código fuente

### Requisitos

```bash
pip install yt-dlp pyinstaller
```

Coloca `ffmpeg.exe` y `ffprobe.exe` en el mismo directorio que `youtube_downloader.py`
(descárgalos desde [ffmpeg.org](https://ffmpeg.org/download.html) o
[BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds/releases)).

### Ejecutar sin compilar

```bash
python youtube_downloader.py
```

### Compilar el ejecutable

```bash
pyinstaller --onefile --windowed --name "YouTube Downloader" \
  --add-binary "ffmpeg.exe;." \
  --add-binary "ffprobe.exe;." \
  youtube_downloader.py
```

El ejecutable resultante queda en `dist/YouTube Downloader.exe`.

---

## Tecnologías utilizadas

| Librería | Propósito |
|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Descarga de video/audio de YouTube |
| [ffmpeg](https://ffmpeg.org/) | Mezcla de streams y conversión de audio |
| tkinter | Interfaz gráfica (incluido en Python) |
| [PyInstaller](https://pyinstaller.org/) | Empaquetado en ejecutable Windows |

---

## Licencia

**Freeware de uso irrestricto** — Copyright © 2026 Jose Alexis Correa Valencia

Puedes usar, copiar, modificar y distribuir este software libremente.
Consulta el archivo [LICENSE](LICENSE) para los términos completos.

---

## Autor

**Jose Alexis Correa Valencia**
📧 jalexiscv@gmail.com
🐙 [@jalexiscv](https://github.com/jalexiscv)
