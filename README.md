# 🗡️ SlayerDownloader

Descarrega vídeos e músicas de YouTube, TikTok, Instagram e mais — com um clique.

---

## ⬇️ Download Rápido

**Só queres usar o programa?** Descarrega o ficheiro pronto:

### 📦 [Descarregar SlayerDownloader.rar](SlayerDownloader.rar)

> Extrai o `.rar`, abre o `SlayerDownloader.exe` e está pronto a usar!

⚠️ O Windows pode bloquear o `.exe` por não estar assinado digitalmente.  
Nesse caso, clica em **"Mais informações" → "Executar mesmo assim"**.

---

## 🎯 Formatos disponíveis

| Formato | Descrição |
|---------|-----------|
| 🎵 MP3  | Só áudio, qualidade máxima (320kbps) |
| 🎬 720p | Vídeo MP4 em HD |
| 🎬 1080p | Vídeo MP4 em Full HD |
| ⭐ Melhor | Vídeo MP4 na melhor qualidade possível |

---

## 🛠️ Para programadores

### Correr o script Python
```bash
pip install yt-dlp
python downloader.py
```

### Compilar para .exe
```bash
build.bat
```

### Requisitos
- **Python 3.10+**
- **FFmpeg** — copiado automaticamente pelo `build.bat`

### Estrutura
```
SlayerDownloader/
├── downloader.py      # App principal
├── build.bat          # Compila para .exe + copia FFmpeg
├── assets/
│   └── icon.ico       # Ícone da aplicação
└── SlayerDownloader.rar  # Programa pronto a usar
```
