# 🗡️ SlayerDownloader

Descarrega vídeos e músicas de YouTube, TikTok, Instagram e mais — com um clique.

## Como usar

### Executável (.exe)
1. Corre o `build.bat`
2. Abre `dist/SlayerDownloader.exe`
3. Cola o link, escolhe o formato e carrega em **Descarregar**

### Script Python
```bash
pip install yt-dlp
python downloader.py
```

## Formatos disponíveis

| Formato | Descrição |
|---------|-----------|
| 🎵 MP3  | Só áudio, qualidade máxima (320kbps) |
| 🎬 720p | Vídeo MP4 em HD |
| 🎬 1080p | Vídeo MP4 em Full HD |
| ⭐ Melhor | Vídeo MP4 na melhor qualidade possível |

## Requisitos

- **Python 3.10+** (só para correr o script)
- **FFmpeg** — copiado automaticamente pelo `build.bat`

## Estrutura

```
SlayerDownloader/
├── downloader.py      # App principal
├── build.bat          # Compila para .exe + copia FFmpeg
└── assets/
    └── icon.ico       # Ícone da aplicação
```
