# 🗡️ SlayerDownloader

Um downloader de vídeos e áudio moderno, com interface gráfica escura e elegante.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-Private-red?style=flat-square)

## ✨ Funcionalidades

- 🎵 **Download de Áudio** — MP3 a 320kbps (qualidade máxima)
- 🎬 **Download de Vídeo** — MP4 em 720p, 1080p ou melhor qualidade
- 📋 **Fila de Downloads** — Adiciona vários links e descarrega tudo de uma vez
- 🔍 **Deteção Automática** — Reconhece YouTube, Twitter/X, Instagram, TikTok, Vimeo e SoundCloud
- 💾 **Preferências Guardadas** — Lembra a pasta de destino e o formato preferido
- ❌ **Cancelamento** — Cancela downloads em progresso a qualquer momento

## 🖥️ Interface

Interface escura moderna com paleta de azuis vibrantes, tipografia Calibri e design limpo.

## 📦 Requisitos

- **Python 3.10+**
- **yt-dlp** — `pip install yt-dlp`
- **FFmpeg** — Necessário para juntar vídeo+áudio e converter para MP3
  - Descarregar em [ffmpeg.org](https://ffmpeg.org/download.html)
  - Colocar `ffmpeg.exe` na mesma pasta do script ou adicionar ao PATH

## 🚀 Como Usar

### Executar como script Python
```bash
pip install yt-dlp
python downloader.py
```

### Compilar para .exe
```bash
build.bat
```
O executável será criado na pasta `dist/`.

## 📁 Estrutura

```
SlayerDownloader/
├── downloader.py      # Aplicação principal
├── config.json        # Preferências do utilizador (gerado automaticamente)  
├── icon.ico           # Ícone da aplicação
├── build.bat          # Script para compilar o .exe
├── ffmpeg.exe         # FFmpeg (não incluído no repo - ver requisitos)
└── .gitignore
```

## 🛠️ Tecnologias

- **Tkinter** — Interface gráfica nativa do Python
- **yt-dlp** — Motor de download de vídeos
- **FFmpeg** — Processamento e conversão de media
- **PyInstaller** — Compilação para executável Windows
