# 🗡️ SlayerDownloader

Descarrega vídeos e músicas de YouTube, TikTok, Instagram e mais — com um clique.

---

## ⬇️ Download Rápido

**Só queres usar o programa?** Descarrega o ficheiro pronto a usar a partir da secção de **Releases**:

1. Vai ao separador [Releases](../../releases) aqui no GitHub (do lado direito).
2. Descarrega o ficheiro `SlayerDownloader.rar` da versão mais recente.
3. Extrai o `.rar`, abre o `SlayerDownloader.exe` e está pronto a usar!

⚠️ O Windows pode bloquear o `.exe` por não estar assinado digitalmente.  
Nesse caso, clica em **"Mais informações" → "Executar mesmo assim"**.

---

## ✨ Funcionalidades

- 📋 **Colar automático** — cola o URL do clipboard ao abrir a app
- 🖼️ **Preview** — mostra miniatura e título do vídeo antes de descarregar
- 📂 **Abrir pasta** — acesso rápido à pasta de destino após download
- 🕐 **Histórico** — acesso rápido aos últimos downloads
- 🔄 **Atualizar yt-dlp** — mantém a app funcional com um clique
- 🔔 **Notificação sonora** — avisa quando o download termina
- ⚡ **Fila de downloads** — adiciona vários links e descarrega de uma vez

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
pip install yt-dlp Pillow
python downloader.py
```

### Compilar para .exe
```bash
build.bat
```
> O `build.bat` descarrega o FFmpeg automaticamente e cria a pasta `SlayerDownloader/` com tudo pronto.

### Requisitos
- **Python 3.10+**
- **yt-dlp** — motor de download
- **Pillow** — para mostrar thumbnails
- **FFmpeg** — descarregado automaticamente pelo `build.bat`

### Estrutura
```
SlayerDownloader/
├── downloader.py         # App principal (UI + lógica)
├── build.bat             # Compila para .exe + descarrega FFmpeg
└── assets/
    └── icon.ico          # Ícone da aplicação
```
