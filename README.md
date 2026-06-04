# 🗡️ SlayerHub — Downloader & Conversor

[![GitHub release](https://img.shields.io/github/v/release/TheSlayer999/SlayerHub?style=flat-square)](https://github.com/TheSlayer999/SlayerHub/releases)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078d4?style=flat-square)](https://github.com/TheSlayer999/SlayerHub)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-powered-brightgreen?style=flat-square)](https://github.com/yt-dlp/yt-dlp)

**SlayerHub** é uma aplicação desktop para Windows, construída em Python com Tkinter, que permite descarregar vídeos e áudio de dezenas de plataformas online e converter ficheiros de media entre formatos — tudo com uma interface gráfica limpa e moderna.

---

## Índice

- [Funcionalidades](#funcionalidades)
  - [Downloader](#-downloader)
  - [Conversor](#-conversor)
- [Capturas de Ecrã](#capturas-de-ecrã)
- [Formatos de Download](#formatos-de-download)
- [Plataformas Suportadas](#plataformas-suportadas)
- [Instalação](#instalação)
- [Compilar para .exe](#compilar-para-exe)
- [Para Programadores](#para-programadores)
- [Configuração](#configuração)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [Licença](#licença)
- [Contribuições](#contribuições)
- [Contacto](#contacto)

---

## Funcionalidades

### 📥 Downloader

A aba **Downloader** permite colar links de vídeo/áudio, escolher formato e qualidade, e fazer download individual ou em fila.

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

A aba **Conversor** permite transformar ficheiros entre formatos de vídeo, áudio e imagem.

- **Vídeo para vídeo** — MP4, MKV, AVI, WEBM
- **Vídeo para áudio** — Extrai MP3, WAV, AAC de qualquer vídeo
- **Áudio para áudio** — MP3, WAV, AAC, FLAC, OGG
- **Imagem para imagem** — PNG, JPG, WEBP, BMP, ICO (via Pillow)
- **Suporte a HEIC/HEIF** — Converte fotos de iPhone para outros formatos (requer `pillow-heif`)
- **Batch conversion** — Seleciona múltiplos ficheiros de uma vez
- **Barra de progresso precisa** — Usa `ffprobe` para calcular a percentagem real durante a conversão

---

## Capturas de Ecrã

| Aba Downloader | Aba Conversor |
|---|---|
| ![Aba Downloader](assets/DownloaderTela.png) | ![Aba Conversor](assets/ConversorTela.png) |

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

A app deteta automaticamente a plataforma ao colar o link e apresenta a pré-visualização antes do download.

---

## 📥 Instalação

### Opção 1 — Executável pronto (recomendado)

1. Vai à secção **[Releases](https://github.com/TheSlayer999/SlayerHub/releases)** do repositório.
2. Descarrega o ficheiro `SlayerHub.zip` da versão mais recente.
3. Extrai o `.zip` e abre `SlayerHub.exe`.

> ⚠️ O Windows pode bloquear o `.exe` por não estar assinado digitalmente. Clica em **"Mais informações" → "Executar mesmo assim"**.

A pasta descomprimida contém:

```
SlayerHub/
└── SlayerHub.exe   # Aplicação completa (tudo incluído)
```

> O FFmpeg é descarregado automaticamente pela app na primeira vez que for necessário.

### Opção 2 — A partir do código-fonte

```bash
git clone https://github.com/TheSlayer999/SlayerHub.git
cd SlayerHub
pip install -r requirements.txt
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

> O FFmpeg **não** é incluído no pacote — a app descarrega-o automaticamente na primeira execução, se necessário. A pasta final pode ser comprimida em `.zip` ou `.rar` e partilhada diretamente.

---

## 🛠️ Para Programadores

### Tech Stack

| Tecnologia | Finalidade |
|------------|------------|
| **Python 3.10+** | Linguagem principal |
| **Tkinter (ttk)** | Interface gráfica nativa |
| **yt-dlp** | Motor de download (YouTube, TikTok, etc.) |
| **FFmpeg** | Merge de vídeo/áudio e conversão |
| **Pillow** | Miniaturas e conversão de imagens |
| **pillow-heif** | Suporte a fotos HEIC/HEIF (iPhone) |
| **PyInstaller** | Compilação para `.exe` |
| **argparse** | Parsing de argumentos da CLI |

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
├── downloader.py              # Código principal — UI (Tkinter) + lógica de download/conversão
├── requirements.txt           # Dependências Python
├── build.bat                  # Script de compilação (PyInstaller)
├── SlayerHub.spec             # Spec do PyInstaller
├── release-notes-v3.0.1.txt   # Notas da versão atual
├── LICENSE                    # Licença MIT
├── CLAUDE.md                  # Regras de contexto para Claude Code
├── config.json                # Configurações do utilizador (auto-gerado)
├── assets/
│   ├── icon.ico               # Ícone da aplicação
│   ├── icon.jpg               # Ícone alternativo
│   ├── DownloaderTela.png     # Screenshot da aba Downloader
│   └── ConversorTela.png      # Screenshot da aba Conversor
├── build/                     # Artefactos temporários de compilação (gitignored)
├── dist/                      # Executável compilado (gitignored)
├── old versions/              # Versões anteriores (gitignored)
└── .claude/                   # Configurações do Claude Code
```

### Arquitetura Interna

O código está organizado em 4 classes principais, dentro de um único ficheiro (`downloader.py`):

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

## 🗺️ Roadmap

- [ ] Tema claro/escuro selecionável
- [ ] Download de playlists completas
- [ ] Suporte a legendas
- [ ] Localização EN/PT
- [ ] Modo portátil (config na mesma pasta)
- [ ] Instalador MSI / winget

---

## 📋 Changelog

As notas de versão detalhadas estão em [`release-notes-v3.0.1.txt`](release-notes-v3.0.1.txt).

Consulta todas as versões na página [Releases do GitHub](https://github.com/TheSlayer999/SlayerHub/releases).

---

## 📄 Licença

Este projeto está licenciado sob a **MIT License** — vê o ficheiro [`LICENSE`](LICENSE) para mais detalhes.

---

## 🤝 Contribuições

Contribuições são bem-vindas! Abre uma *issue* para relatar bugs ou sugerir funcionalidades, ou submete um *pull request* diretamente.

Se encontrares problemas com downloads, verifica primeiro se o **yt-dlp** está atualizado — há um botão na app para isso (cabeçalho → "Atualizar yt-dlp").

---

## 📞 Contacto

- **GitHub:** https://github.com/TheSlayer999/SlayerHub
- **Autor:** TheSlayer999
