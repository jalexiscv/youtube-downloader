# Higgs Video Downloader

**Aplicación de escritorio para descargar videos y audio de YouTube — sin instalar nada adicional.**

Desarrollado por **Jose Alexis Correa Valencia** · Freeware de uso irrestricto

---

## Descarga

➡️ Ve a [**Releases**](../../releases/latest) y descarga `Higgs.Video.Downloader.exe`

> No requiere Python ni ffmpeg instalados. Todo está incluido en el ejecutable.

---

## Características

| Función | Detalle |
|---|---|
| Vista previa automática | Miniatura, título, canal, duración y vistas al pegar la URL |
| Descarga de video | Mejor calidad, 1080p, 720p, 480p, 360p en MP4 |
| Descarga de audio | MP3 a 192 kbps |
| ffmpeg integrado | Mezcla de pistas y conversión sin instalar nada |
| Carpeta destino | Seleccionable desde la interfaz |
| Barra de progreso | Velocidad, ETA y fases (descarga / mezcla) en tiempo real |
| Sin consola | Aplicación de ventana, sin terminal visible |
| Interfaz moderna | Tema oscuro con PyQt6 |

---

## Interfaz

```
┌──────────────────────────────────────────────────────────────┐
│  ▶  Higgs Video Downloader          ffmpeg ✓  Jose A. Correa │
├──────────────────────────────────────────────────────────────┤
│  URL │ [ https://youtube.com/watch?v=...              ✕ ] [Vista previa] │
├─────────────────────┬────────────────────────────────────────┤
│                     │  Formato de descarga:                  │
│   [ Miniatura ]     │  [ Mejor calidad (video + audio)  ▼ ] │
│                     │                                        │
│  Título del video   │  Carpeta de destino:                   │
│  Canal: @nombre     │  [ ~/Downloads            ] [Examinar] │
│  Duración: 3:32     │                                        │
│  Vistas: 1.2M       │  [        ⬇   Descargar            ]  │
│                     │                                        │
├─────────────────────┴────────────────────────────────────────┤
│  ████████████████████░░░░  72%                               │
│  Descargando... 72% · 8.2 MB/s · ETA 4s                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Formatos disponibles

- **Mejor calidad (video+audio)** — mayor resolución disponible, fusionado en MP4
- **1080p / 720p / 480p / 360p** — resolución específica fusionada en MP4
- **Solo audio (MP3)** — extrae y convierte a MP3 192 kbps

---

## Uso

1. Descarga `Higgs.Video.Downloader.exe` desde [Releases](../../releases/latest)
2. Ejecuta el archivo (doble clic) — no requiere instalación
3. Pega la URL del video de YouTube — la vista previa se carga automáticamente
4. Selecciona el formato deseado
5. Elige la carpeta de destino (por defecto `~/Downloads`)
6. Haz clic en **⬇ Descargar**

---

## Construcción desde el código fuente

### Requisitos

```bash
pip install yt-dlp pyinstaller PyQt6
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
pyinstaller --onefile --windowed --name "Higgs Video Downloader" \
  --add-binary "ffmpeg.exe;." \
  --add-binary "ffprobe.exe;." \
  youtube_downloader.py
```

El ejecutable resultante queda en `dist/Higgs Video Downloader.exe`.

---

## Tecnologías utilizadas

| Librería | Propósito |
|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Descarga de video/audio de YouTube |
| [ffmpeg](https://ffmpeg.org/) | Mezcla de streams y conversión de audio |
| [PyQt6](https://pypi.org/project/PyQt6/) | Interfaz gráfica moderna |
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
