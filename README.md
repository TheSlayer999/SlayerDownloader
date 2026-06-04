# 🗡️ SlayerHub — Downloader & Conversor

**SlayerHub** é uma aplicação desktop para Windows, construída em Python (Tkinter), que permite descarregar vídeos e áudio de dezenas de plataformas online e converter ficheiros de media entre formatos — tudo com uma interface gráfica limpa e moderna.

---

## ✨ Funcionalidades

### 📥 Downloader
- **Detecção automática de plataforma** — Identifica YouTube, TikTok, Instagram, Twitter/X, Vimeo e SoundCloud ao colar o link.
- **Pré-visualização do vídeo** — Mostra miniatura, título, canal e duração antes de descarregar.
- **Colagem automática** — Cola o URL do clipboard ao abrir ou focar a janela (se o campo estiver vazio).
- **Fila de downloads** — Adiciona múltiplos links e inicia todos com um único clique. Cada item tem botão de remoção individual.
- **Cancelamento a quente** — O botão de download transforma-se em "Cancelar" durante o processo.
- **Notificação sonora** — Emite beep nativo do Windows ao concluir.
- **Abrir pasta** — Botão de atalho para a pasta de destino aparece após cada download.
- **Log em tempo real** — Console expansível com progresso, velocidade, ETA e erros detalhados.
- **Atualizar yt-dlp** — Botão no cabeçalho que descarrega a versão mais recente do motor diretamente do GitHub.
- **FFmpeg automático** — Se o FFmpeg não for encontrado, a app oferece-se para o descarregar e instalar automaticamente (~100 MB).

### 🔄 Conversor
- **Vídeo para vídeo** — MP4, MKV, AVI, WEBM
- **Vídeo para áudio** — Extrai MP3, WAV, AAC de qualquer vídeo
- **Áudio para áudio** — MP3, WAV, AAC, FLAC, OGG
- **Imagem para imagem** — PNG, JPG, WEBP, BMP, ICO (via Pillow)
- **Suporte a HEIC/HEIF** — Converte fotos de iPhone para outros formatos (requer `pillow-heif`)
- **Batch conversion** — Seleciona múltiplos ficheiros de uma vez
- **Barra de progresso precisa** — Usa `ffprobe` para calcular a percentagem real durante a conversão

---

## 🎯 Formatos de Download

| Formato | Tipo | Qualidade |
|---------|------|-----------|
| 🎵 **Só Áudio (MP3)** | Áudio | 320 kbps |
| 🎬 **Vídeo 720p** | Vídeo MP4 | HD |
| 🎬 **Vídeo 1080p** | Vídeo MP4 | Full HD |
| ⭐ **Melhor Qualidade** | Vídeo MP4 | Máxima disponível |

---

## 🌐 Plataformas Suportadas

Qualquer site suportado pelo **yt-dlp** funciona, incluindo:

`YouTube` · `TikTok` · `Instagram` · `Twitter / X` · `Vimeo` · `SoundCloud` · e [muitos mais](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## 📥 Instalação

### Opção 1 — Executável pronto (recomendado)

1. Vai à secção **[Releases](https://github.com/TheSlayer999/SlayerDownloader/releases)** do repositório.
2. Descarrega o ficheiro `SlayerDownloader.rar` da versão mais recente.
3. Extrai o `.rar` e abre `SlayerDownloader.exe`.

> ⚠️ O Windows pode bloquear o `.exe` por não estar assinado digitalmente. Clica em **"Mais informações" → "Executar mesmo assim"**.

A pasta descomprimida contém:
```
SlayerHub/
└── SlayerHub.exe   # Aplicação completa (tudo incluído)
```

> O FFmpeg é descarregado automaticamente pela app na primeira vez que for necessário.

### Opção 2 — A partir do código-fonte

```bash
git clone https://github.com/TheSlayer999/SlayerDownloader.git
cd SlayerDownloader
pip install yt-dlp Pillow pillow-heif
python downloader.py
```

> Em modo script, o FFmpeg é descarregado automaticamente se não for encontrado. Podes também colocá-lo na pasta do projeto ou tê-lo instalado no PATH do sistema.

---

## 🔨 Compilar para .exe

O script `build.bat` automatiza todo o processo:

```bat
build.bat
```

O que faz automaticamente:
1. Instala todas as dependências Python (`pyinstaller`, `Pillow`, `pillow-heif`, `yt-dlp`)
2. Compila o `downloader.py` num único `.exe` com PyInstaller
3. Cria a pasta `SlayerHub/` com o executável pronto a distribuir

> O FFmpeg **não** é incluído no pacote — a app descarrega-o automaticamente na primeira execução, se necessário. A pasta final pode ser comprimida em `.rar` e partilhada diretamente.

---

## 🛠️ Para Programadores

### Requisitos

| Dependência | Função | Obrigatório |
|-------------|--------|-------------|
| **Python 3.10+** | Runtime | ✅ |
| **yt-dlp** | Motor de download | ✅ |
| **FFmpeg** | Merge de vídeo/áudio, conversão | ✅ |
| **Pillow** | Miniaturas e conversão de imagens | ⚠️ Recomendado |
| **pillow-heif** | Suporte a HEIC/HEIF (iPhone) | ⚠️ Opcional |

### Estrutura do Projeto

```
SlayerHub/
├── downloader.py     # Código principal — UI (Tkinter) + lógica de download/conversão
├── build.bat         # Script de compilação e distribuição
├── config.json       # Configurações persistentes do utilizador (auto-gerado)
├── SlayerHub.spec    # Spec do PyInstaller
└── assets/
    └── icon.ico      # Ícone da aplicação
```

### Arquitetura Interna

| Classe | Responsabilidade |
|--------|-----------------|
| `ConfigManager` | Leitura/escrita de `config.json` (pasta de destino, formato, visibilidade do log) |
| `QueueManager` | Gestão da lista de downloads em lote |
| `DownloadEngine` | Execução do `yt-dlp` em subprocesso; parsing de progresso, velocidade e erros |
| `PulsarUI` | Interface Tkinter completa com abas Downloader e Conversor |

---

## ⚙️ Configuração

As preferências são guardadas automaticamente em `config.json`:

```json
{
  "download_path": "C:/Users/utilizador/Downloads",
  "format": "🎵  Só Áudio (MP3)",
  "show_log": false
}
```

---

## 📄 Licença

Este projeto está licenciado sob a **MIT License** — vê o ficheiro [`LICENSE`](LICENSE) para mais detalhes.

---

## 🤝 Contribuições

Contribuições são bem-vindas! Abre uma *issue*, submete um *pull request* ou sugere novas funcionalidades.

---

## 📞 Contacto

- **GitHub:** https://github.com/TheSlayer999/SlayerDownloader
- **Autor:** TheSlayer999