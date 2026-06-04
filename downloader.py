"""
Slayer Downloader

Interface gráfica (Tkinter) para download de vídeos e áudios de plataformas
como YouTube, TikTok, Twitter e Instagram. Suporta downloads individuais
e em fila, com conversão automática via FFmpeg.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import json
import os
import sys
import re
import shutil
import time
from datetime import datetime

# Suporte a notificações sonoras nativas do Windows
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

# Suporte a pré-visualização de miniaturas (Pillow)
try:
    from PIL import Image, ImageTk
    import urllib.request
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Suporte a imagens HEIC (iPhone) via pillow-heif
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

# Importação dinâmica da biblioteca yt-dlp
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False


# Configuração da paleta de cores e estilos visuais
C = {
    "bg":        "#0c1222",   # Cor de fundo principal (azul escuro)
    "surface":   "#131d33",   # Superfície primária (azul marinho)
    "surface2":  "#1a2744",   # Superfície secundária (painéis e botões)
    "border":    "#263758",   # Bordas e divisores
    "accent":    "#3b82f6",   # Destaque principal (azul vibrante)
    "accent2":   "#2563eb",   # Destaque secundário (hover do botão)
    "text":      "#f0f4ff",   # Texto principal
    "text_dim":  "#94a3c8",   # Texto secundário ou descritivo
    "text_muted": "#566b90",  # Texto desativado ou auxiliar
    "success":   "#34d399",   # Indicador de sucesso (verde)
    "warn":      "#fbbf24",   # Indicador de aviso ou atenção (amarelo)
    "error":     "#f87171",   # Indicador de erro ou falha (vermelho)
    "entry_bg":  "#0e1629",   # Fundo dos campos de entrada de texto
}

# Configurações de tipografia
F_MAIN = ("Calibri", 12)
F_BOLD = ("Calibri", 10, "bold")
F_TITLE = ("Calibri", 24, "bold")
F_SMALL = ("Calibri", 9)
F_MONO = ("Consolas", 10)

# Plataformas oficialmente suportadas e seus padrões de detecção
PLATFORMS = {
    "YouTube":  {"pattern": r"youtube\.com|youtu\.be",  "icon": "▶"},
    "Twitter":  {"pattern": r"twitter\.com|x\.com",     "icon": "✕"},
    "Instagram":{"pattern": r"instagram\.com",           "icon": "◉"},
    "TikTok":   {"pattern": r"tiktok\.com",              "icon": "♪"},
    "Vimeo":    {"pattern": r"vimeo\.com",               "icon": "◈"},
    "SoundCloud":{"pattern":r"soundcloud\.com",          "icon": "☁"},
}

# Opções de formato e qualidade de download
FORMAT_OPTIONS = {
    "🎵  Só Áudio (MP3)":          {"type": "audio", "ext": "mp3",  "quality": "320"},
    "🎬  Vídeo 720p":              {"type": "video", "ext": "mp4",  "quality": "720"},
    "🎬  Vídeo 1080p":             {"type": "video", "ext": "mp4",  "quality": "1080"},
    "⭐  Vídeo Melhor Qualidade":  {"type": "video", "ext": "mp4",  "quality": "best"},
}

# Caminho para o arquivo de configuração local do usuário
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


# --- Gerenciador de Configurações ---
class ConfigManager:
    """Gere a leitura, escrita e persistência das configurações locais do usuário."""

    DEFAULTS = {
        "download_path": os.path.expanduser("~/Downloads"),
        "format": list(FORMAT_OPTIONS.keys())[0],
        "show_log": True,
    }

    def __init__(self, path=CONFIG_PATH):
        self._path = path
        self._data = dict(self.DEFAULTS)
        self._load()

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Carrega apenas chaves de configuração suportadas
            for key in self.DEFAULTS:
                if key in saved:
                    self._data[key] = saved[key]
        except (FileNotFoundError, json.JSONDecodeError):
            pass  # Utiliza os valores padrões

    def save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass  # Ignora erros de permissão ou falta de espaço em disco ao salvar

    def get(self, key):
        return self._data.get(key, self.DEFAULTS.get(key))

    def set(self, key, value):
        self._data[key] = value


# --- Gerenciador da Fila de Downloads ---
class QueueManager:
    """Controla a lista de links adicionados para processamento em lote."""

    def __init__(self):
        self._items = []

    def add(self, url, fmt_label):
        self._items.append({"url": url, "format": fmt_label})

    def clear(self):
        self._items.clear()

    def remove(self, index):
        if 0 <= index < len(self._items):
            del self._items[index]

    def items(self):
        return list(self._items)

    def __len__(self):
        return len(self._items)

    def __bool__(self):
        return bool(self._items)


# --- Motor de Download (yt-dlp) ---
class DownloadEngine:
    """Controla a execução do yt-dlp em um subprocesso em segundo plano."""

    # Padrões de erro mapeados para diagnósticos mais amigáveis
    NETWORK_ERRORS = {
        "unable to download webpage": "Sem ligação à internet ou URL inválido",
        "urlopen error": "Sem ligação à internet",
        "timed out": "O servidor não respondeu (timeout)",
        "connection refused": "Ligação recusada pelo servidor",
        "http error 403": "Acesso bloqueado (403 Forbidden)",
        "http error 404": "Vídeo não encontrado (404)",
        "http error 429": "Demasiados pedidos — tenta novamente mais tarde",
        "video unavailable": "Vídeo indisponível ou privado",
        "private video": "Este vídeo é privado",
        "sign in to confirm": "Vídeo com restrição de idade — requer login",
        "no video formats": "Nenhum formato de vídeo disponível",
        "is not a valid url": "URL inválido",
    }

    def __init__(self, on_progress, on_log, on_status, on_done, on_phase):
        self._on_progress = on_progress
        self._on_log = on_log
        self._on_status = on_status
        self._on_done = on_done
        self._on_phase = on_phase  # "connecting" | "downloading" | "merging" | None
        self.cancel_requested = False
        self.is_downloading = False
        self._process = None
        self._last_progress_update = 0
        self._last_activity_time = 0

    def start(self, jobs, dest):
        """Inicia os downloads da fila em uma thread dedicada (daemon)."""
        self.cancel_requested = False
        self.is_downloading = True
        self._last_activity_time = time.time()
        thread = threading.Thread(
            target=self._run_jobs, args=(jobs, dest), daemon=True
        )
        thread.start()

    def cancel(self):
        """Interrompe e finaliza a execução ativa do subprocesso do yt-dlp."""
        self.cancel_requested = True
        if self._process:
            try:
                self._process.kill()
            except Exception:
                pass

    def _run_jobs(self, jobs, dest):
        total = len(jobs)
        for idx, job in enumerate(jobs, 1):
            if self.cancel_requested:
                self._on_log("⊘  Download cancelado pelo utilizador.", "warn")
                break
            self._on_phase("connecting")
            self._on_status(f"[{idx}/{total}] A preparar...", C["text_dim"])
            self._download_subprocess(job["url"], job["format"], dest, idx, total)

        self.is_downloading = False
        self._on_phase(None)
        self._on_done(cancelled=self.cancel_requested)

    def _download_subprocess(self, url, fmt_label, dest, idx, total):
        if self.cancel_requested:
            return

        fmt = FORMAT_OPTIONS[fmt_label]
        os.makedirs(dest, exist_ok=True)

        self._on_status(f"[{idx}/{total}] A ligar...", C["text_dim"])
        self._last_activity_time = time.time()

        # Determina o caminho do executável do yt-dlp conforme o ambiente
        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        local_ytdlp = os.path.join(app_dir, "yt-dlp.exe")

        if os.path.exists(local_ytdlp):
            cmd = [local_ytdlp, "--no-warnings", "--socket-timeout", "15", "--newline"]
        elif getattr(sys, 'frozen', False):
            cmd = [sys.executable, "--run-yt-dlp", "--no-warnings", "--socket-timeout", "15", "--newline"]
        else:
            cmd = [sys.executable, "-m", "yt_dlp", "--no-warnings", "--socket-timeout", "15", "--newline"]

        out_template = os.path.join(dest, "%(title)s.%(ext)s")
        cmd.extend(["-o", out_template])

        if fmt["type"] == "audio":
            cmd.extend([
                "-f", "bestaudio/best",
                "--extract-audio",
                "--audio-format", fmt["ext"],
                "--audio-quality", fmt["quality"]
            ])
        else:
            if fmt["quality"] == "best":
                if fmt["ext"] == "mp4":
                    fmt_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                else:
                    fmt_str = "bestvideo+bestaudio/best"
            else:
                if fmt["ext"] == "mp4":
                    fmt_str = (f"bestvideo[height<={fmt['quality']}][ext=mp4]+"
                               f"bestaudio[ext=m4a]/"
                               f"best[height<={fmt['quality']}][ext=mp4]")
                else:
                    fmt_str = (f"bestvideo[height<={fmt['quality']}]+"
                               f"bestaudio/"
                               f"best[height<={fmt['quality']}]")
            cmd.extend([
                "-f", fmt_str,
                "--merge-output-format", fmt["ext"],
                "--remux-video", fmt["ext"]
            ])

        cmd.append(url)

        try:
            # Oculta a janela do console/terminal no ambiente Windows
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

            # Inclui o diretório local no PATH para que o yt-dlp localize o FFmpeg
            app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            env = os.environ.copy()
            env["PATH"] = app_dir + os.pathsep + env.get("PATH", "")

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=creationflags,
                env=env
            )

            for line in iter(self._process.stdout.readline, ''):
                if self.cancel_requested:
                    self._process.kill()
                    break

                line = line.strip()
                self._last_activity_time = time.time()
                self._parse_output(line)
                self._check_network_errors(line)

            self._process.stdout.close()
            return_code = self._process.wait()

            if self.cancel_requested:
                return

            if return_code == 0:
                self._on_log(f"✓  Concluído: {url[:50]}...", "ok")
                self._on_status("Download concluído!", C["success"])
                self._on_progress(100)
            else:
                self._on_log(f"✗  Erro no download (código {return_code})", "err")
                self._on_status("Erro no download", C["error"])

        except Exception as e:
            msg = str(e)[:120]
            if "WinError 2" in msg and "yt_dlp" in msg:
                 self._on_log("✗  yt-dlp não está instalado de forma global.", "err")
            else:
                 self._on_log(f"✗  Erro inesperado no subprocesso: {msg}", "err")
            self._on_status("Erro inesperado", C["error"])
        finally:
            self._process = None

    def _check_network_errors(self, line):
        """Analisa a saída de texto do yt-dlp em busca de mensagens de erro conhecidas."""
        line_lower = line.lower()
        for pattern, message in self.NETWORK_ERRORS.items():
            if pattern in line_lower:
                self._on_log(f"✗  {message}", "err")
                self._on_status(message, C["error"])
                return True
        return False

    def _parse_output(self, line):
        """Processa a saída em tempo real do yt-dlp para atualizar o progresso na UI."""
        if line.startswith("[download]") and "%" in line:
            self._on_phase("downloading")
            parts = line.split()
            pct_str = next((p for p in parts if "%" in p), None)
            if pct_str:
                try:
                    pct = float(pct_str.replace('%', ''))

                    # Limita a frequência de atualização da interface gráfica para evitar sobrecarga
                    now = time.time()
                    if pct >= 100 or (now - self._last_progress_update) > 0.3:
                        self._last_progress_update = now
                        self._on_progress(pct)

                        # Extrai a velocidade atual e o tempo estimado (ETA) da linha de saída
                        speed = next((p for p in parts if "/s" in p), "")
                        eta = parts[-1] if "ETA" in line else ""

                        self._on_status(f"  {pct:.1f}%  •  {speed}  •  ETA {eta}", C["text_dim"])
                except ValueError:
                    pass
        elif "[Merger]" in line or "Merging formats into" in line:
             self._on_phase("merging")
             self._on_status("A juntar vídeo e áudio...", C["warn"])
             self._on_log("A juntar ficheiros com ffmpeg...", "info")
        elif "[ExtractAudio]" in line or "Destination:" in line and "audio" in line.lower():
             self._on_phase("merging")
             self._on_status("Processando media (FFmpeg)...", C["warn"])
        elif line.startswith("[youtube]") or line.startswith("[info]"):
             if "Downloading video info" in line or "Downloading webpage" in line:
                 self._on_status("A obter metadados...", C["text_dim"])
             elif "Downloading" not in line and "at" not in line and ":" in line:
                  self._on_log(line, "info")


# --- Interface Gráfica Principal (Tkinter) ---
class PulsarUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SlayerHub v3.0")
        self.root.geometry("800x800")
        # Removed fixed minsize; will set dynamically after UI is built
        # self.root.minsize(800, 800)
        self.root.configure(bg=C["bg"])

        # Inicialização dos gerenciadores de configuração, fila e downloads
        self.config = ConfigManager()
        self.queue = QueueManager()
        self.engine = DownloadEngine(
            on_progress=self._safe_progress,
            on_log=self._safe_log,
            on_status=self._safe_status,
            on_done=self._safe_done,
            on_phase=self._safe_phase,
        )

        # Inicialização das variáveis de controle da interface
        self.download_path = tk.StringVar(value=self.config.get("download_path"))
        self.url_var        = tk.StringVar()
        self.format_var     = tk.StringVar(value=self.config.get("format"))
        self.status_var     = tk.StringVar(value="Pronto para descarregar.")
        self.progress_var   = tk.DoubleVar(value=0)
        self.detected_platform = tk.StringVar(value="")

        # Inicialização das variáveis de controle do conversor de formatos
        self.conv_file_var = tk.StringVar(value="")
        self.conv_format_var = tk.StringVar(value="")
        self.is_converting = False
        self.conv_process = None
        self.conv_thread = None

        # Estado e referências para exibição de miniaturas (thumbnails)
        self._thumbnail_image = None   # Retém a referência da imagem para evitar a coleta de lixo (GC)
        self._thumbnail_job = 0        # Identificador único da requisição de miniatura ativa

        # Controle do status de colagem automática
        self._auto_pasted = False

        # Monitoramento para atualizar plataforma e miniatura ao alterar link
        self.url_var.trace_add("write", self._detect_platform)
        self.url_var.trace_add("write", self._on_url_change)

        # Salvamento automático de preferências
        self.download_path.trace_add("write", self._save_prefs)
        self.format_var.trace_add("write", self._save_prefs)

        self._build_ui()
        self._check_dependencies()
        # After UI is fully constructed, enforce a minimum window size
        self.root.update_idletasks()
        min_w = self.root.winfo_reqwidth()
        min_h = self.root.winfo_reqheight()
        self.root.minsize(min_w, min_h)

        # Detecção de foco na janela para colagem automática
        self.root.bind("<FocusIn>", self._on_focus_in)

        # Procedimentos de fechamento da aplicação
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- Callbacks Seguros para Threads (Thread-safe) ---
    def _safe_progress(self, pct):
        self.root.after(0, lambda p=pct: self.progress_var.set(p))

    def _safe_log(self, msg, tag="info"):
        self.root.after(0, lambda m=msg, t=tag: self._log(m, t))

    def _safe_status(self, msg, color=None):
        self.root.after(0, lambda m=msg, c=color: self._set_status(m, c))

    def _safe_done(self, cancelled=False):
        self.root.after(0, lambda c=cancelled: self._on_all_done(c))

    def _safe_phase(self, phase):
        self.root.after(0, lambda p=phase: self._set_phase(p))

    # --- Montagem e Estrutura da Interface ---
    def _build_ui(self):
        self._style_ttk()

        # Seção do cabeçalho
        header = tk.Frame(self.root, bg=C["bg"], pady=16)
        header.pack(fill="x", padx=28)

        tk.Label(header, text="SLAYER", font=F_TITLE,
                 fg=C["accent"], bg=C["bg"]).pack(side="left")
        tk.Label(header, text="HUB", font=("Calibri", 22),
                 fg=C["text_dim"], bg=C["bg"]).pack(side="left", padx=(6, 0))
        tk.Label(header, text="v3.0", font=F_SMALL,
                 fg=C["text_muted"], bg=C["bg"]).pack(side="left", padx=(10, 0), pady=(8, 0))

        # Botão para atualização do yt-dlp local
        self.update_btn = tk.Button(header, text="🔄 Atualizar yt-dlp",
                                     font=F_SMALL,
                                     bg=C["surface2"], fg=C["text_muted"],
                                     activebackground=C["accent"], activeforeground="#fff",
                                     relief="flat", bd=0, cursor="hand2",
                                     command=self._update_ytdlp,
                                     padx=8, pady=4)
        self.update_btn.pack(side="right")

        self._sep()

        # --- Menu de Navegação por Abas ---
        self.nav_frame = tk.Frame(self.root, bg=C["bg"])
        self.nav_frame.pack(fill="x", padx=28, pady=(4, 8))

        self.tab_downloader_btn = tk.Button(self.nav_frame, text="📥 Downloader", font=F_BOLD,
                                            bg=C["accent"], fg="#ffffff", activebackground=C["accent2"], activeforeground="#ffffff",
                                            relief="flat", bd=0, cursor="hand2", padx=20, pady=8,
                                            command=lambda: self._switch_tab("downloader"))
        self.tab_downloader_btn.pack(side="left", padx=(0, 10))

        self.tab_converter_btn = tk.Button(self.nav_frame, text="🔄 Conversor", font=F_BOLD,
                                           bg=C["surface2"], fg=C["text_dim"], activebackground=C["accent"], activeforeground="#ffffff",
                                           relief="flat", bd=0, cursor="hand2", padx=20, pady=8,
                                           command=lambda: self._switch_tab("converter"))
        self.tab_converter_btn.pack(side="left")

        self._sep(pady=4)

        # --- Painel Inferior Fixo (Status, Progresso e Log) ---
        bottom_panel = tk.Frame(self.root, bg=C["bg"])
        bottom_panel.pack(side="bottom", fill="x")

        # Barra de progresso principal
        self._sep(pady=12, parent=bottom_panel)
        prog_frame = tk.Frame(bottom_panel, bg=C["bg"], padx=28)
        prog_frame.pack(fill="x")

        self.prog_bar = ttk.Progressbar(prog_frame, variable=self.progress_var,
                                        maximum=100, style="Pulsar.Horizontal.TProgressbar")
        self.prog_bar.pack(fill="x", ipady=3)

        # Mensagem de status e atalho de visualização rápida
        status_row = tk.Frame(prog_frame, bg=C["bg"])
        status_row.pack(fill="x", pady=(4, 0))

        self.status_label = tk.Label(status_row, textvariable=self.status_var,
                                     font=F_BOLD,
                                     fg=C["text_dim"], bg=C["bg"],
                                     anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True)

        self.open_folder_btn = tk.Button(status_row, text="📂 Abrir pasta",
                                          font=F_SMALL,
                                          bg=C["surface2"], fg=C["success"],
                                          activebackground=C["accent"], activeforeground="#fff",
                                          relief="flat", bd=0, cursor="hand2",
                                          command=self._open_download_folder,
                                          padx=10, pady=4)
        # Escondido inicialmente por padrão

        # Variável controladora da visibilidade do console
        self.show_log_var = tk.BooleanVar(value=bool(self.config.get("show_log")))

        # Painel de registro histórico (Log)
        self.log_container = tk.Frame(bottom_panel, bg=C["bg"])

        # Botão interativo para expansão do log
        log_header = tk.Frame(self.log_container, bg=C["bg"], padx=28)
        log_header.pack(fill="x")

        self.log_toggle_btn = tk.Label(log_header, text="▼ Ocultar log" if self.show_log_var.get() else "▶ Mostrar log",
                                       font=F_SMALL,
                                       fg=C["text_muted"], bg=C["bg"], cursor="hand2")
        self.log_toggle_btn.pack(side="left", pady=(4, 4))
        self.log_toggle_btn.bind("<Button-1>", self._toggle_log)

        # Painel de exibição enriquecido de texto do console
        self.log_frame = tk.Frame(self.log_container, bg=C["surface"], padx=28, pady=8)

        self.log_text = tk.Text(self.log_frame, font=F_MONO,
                                bg=C["surface"], fg=C["text_dim"],
                                relief="flat", bd=0, state="disabled",
                                height=4, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_config("ok",    foreground=C["success"])
        self.log_text.tag_config("err",   foreground=C["error"])
        self.log_text.tag_config("info",  foreground=C["text_dim"])
        self.log_text.tag_config("warn",  foreground=C["warn"])

        # Inicializa o log com a visibilidade salva
        self.log_container.pack(fill="x", side="bottom")
        if self.show_log_var.get():
            self.log_frame.pack(fill="both", expand=True, pady=(0, 12))
        else:
            self.log_frame.pack_forget()

        # --- Frame de Conteúdo Principal (Abas) ---
        self.content_frame = tk.Frame(self.root, bg=C["bg"])
        self.content_frame.pack(fill="both", expand=True, padx=28, pady=(15, 20))

        # --- ABA 1: DOWNLOADER ---
        self.downloader_page = tk.Frame(self.content_frame, bg=C["bg"])
        self.downloader_page.pack(fill="both", expand=True, padx=12, pady=12)
        self._build_downloader_tab()

        # --- ABA 2: CONVERSOR ---
        self.converter_page = tk.Frame(self.content_frame, bg=C["bg"])
        self._build_converter_tab()

    def _build_downloader_tab(self):
        main = self.downloader_page

        # ── Botão principal de ação — packed FIRST so tkinter reserves its space ──
        btn_frame = tk.Frame(main, bg=C["bg"], pady=8)
        btn_frame.pack(fill="x", side="bottom")

        self.dl_btn = tk.Button(btn_frame,
                                text="▼  DESCARREGAR",
                                font=("Segoe UI", 14, "bold"),
                                bg=C["accent"], fg="#ffffff",
                                activebackground=C["accent2"],
                                activeforeground="#ffffff",
                                relief="flat", bd=0,
                                cursor="hand2",
                                command=self._start_download,
                                padx=24, pady=8)
        self.dl_btn.pack(fill="x")

        # Comportamento de foco/hover para o botão principal
        self.dl_btn.bind("<Enter>", lambda e: self._btn_hover_enter())
        self.dl_btn.bind("<Leave>", lambda e: self._btn_hover_leave())

        # ── Conteúdo (packed AFTER the button, fills remaining space) ──

        # Campo de entrada da URL
        self._label(main, "Link do vídeo")
        url_row = tk.Frame(main, bg=C["bg"])
        url_row.pack(fill="x", pady=(4, 2))

        self.url_entry = tk.Entry(url_row, textvariable=self.url_var,
                                  font=F_MAIN,
                                  bg=C["entry_bg"], fg=C["text"],
                                  insertbackground=C["accent"],
                                  relief="flat", bd=0,
                                  highlightthickness=1,
                                  highlightbackground=C["border"],
                                  highlightcolor=C["accent"])
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=8)

        self.platform_badge = tk.Label(url_row, textvariable=self.detected_platform,
                                       font=F_BOLD,
                                       fg=C["success"], bg=C["bg"])
        self.platform_badge.pack(side="left", padx=(6, 0))

        # Botão para adicionar link ativo à fila de downloads
        queue_btn = self._btn(url_row, "+ Fila", self._add_to_queue,
                               color=C["border"], fg=C["text_dim"])
        queue_btn.pack(side="left", padx=(4, 0))

        # Contêiner de exibição da miniatura do vídeo
        self.thumb_container = tk.Frame(main, bg=C["bg"])
        self.thumb_container.pack(fill="x")
        
        # Visualização de dados dinâmicos do link (título, autor, miniatura)
        self.thumb_frame = tk.Frame(self.thumb_container, bg=C["surface"], bd=0,
                                    highlightthickness=1,
                                    highlightbackground=C["border"])
        self.thumb_frame.pack(fill="x", pady=(8, 0))

        self.thumb_img_label = tk.Label(self.thumb_frame, bg=C["surface"], width=17, height=4) # Dimensões padrão para o espaço reservado
        self.thumb_img_label.pack(side="left", padx=(8, 10), pady=8)

        self.thumb_info_frame = tk.Frame(self.thumb_frame, bg=C["surface"])
        self.thumb_info_frame.pack(side="left", fill="both", expand=True, pady=8, padx=(0, 8))

        self.thumb_title_label = tk.Label(self.thumb_info_frame, text="A aguardar link...",
                                           font=F_BOLD, fg=C["text_dim"], bg=C["surface"],
                                           wraplength=450, justify="left", anchor="nw")
        self.thumb_title_label.pack(fill="x", anchor="w")

        self.thumb_channel_label = tk.Label(self.thumb_info_frame, text="Insere um URL para ver os detalhes",
                                             font=F_SMALL, fg=C["text_muted"], bg=C["surface"],
                                             anchor="w")
        self.thumb_channel_label.pack(fill="x", anchor="w", pady=(2, 0))

        self.thumb_duration_label = tk.Label(self.thumb_info_frame, text="",
                                              font=F_SMALL, fg=C["text_muted"], bg=C["surface"],
                                              anchor="w")
        self.thumb_duration_label.pack(fill="x", anchor="w")

        # Campo para escolha do formato e resolução do arquivo
        self._label(main, "Formato")
        fmt_row = tk.Frame(main, bg=C["bg"])
        fmt_row.pack(fill="x", pady=(4, 0))

        self.fmt_menu = ttk.Combobox(fmt_row, textvariable=self.format_var,
                                     values=list(FORMAT_OPTIONS.keys()),
                                     state="readonly", style="Pulsar.TCombobox",
                                     font=F_MAIN, takefocus=0)
        self.fmt_menu.pack(side="left", fill="x", expand=True)
        self.fmt_menu.bind("<<ComboboxSelected>>", lambda e: self.root.focus_set())

        # Campo para seleção da pasta de destino
        self._label(main, "Guardar em")
        path_row = tk.Frame(main, bg=C["bg"])
        path_row.pack(fill="x", pady=(4, 0))

        self.path_entry = tk.Entry(path_row, textvariable=self.download_path,
                                   font=F_MAIN,
                                   bg=C["entry_bg"], fg=C["text_dim"],
                                   insertbackground=C["accent"],
                                   relief="flat", bd=0,
                                   highlightthickness=1,
                                   highlightbackground=C["border"],
                                   highlightcolor=C["accent"])
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=6, ipadx=8)

        browse_btn = self._btn(path_row, "Escolher", self._browse_folder,
                               color=C["surface2"], fg=C["text_dim"])
        browse_btn.pack(side="left", padx=(8, 0))

        # Seção da fila de download ativo
        self._label(main, "Fila  (0 itens)", attr="queue_label")
        self.queue_frame = tk.Frame(main, bg=C["surface"], bd=0,
                                    highlightthickness=1,
                                    highlightbackground=C["border"])
        self.queue_frame.pack(fill="x", pady=(4, 0))
        
        self.queue_canvas = tk.Canvas(self.queue_frame, bg=C["surface"], highlightthickness=0, height=60)
        self.queue_container = tk.Frame(self.queue_canvas, bg=C["surface"])
        self.queue_window = self.queue_canvas.create_window((0, 0), window=self.queue_container, anchor="nw")
        
        self.queue_canvas.pack(fill="x", expand=True, padx=4, pady=4)
        
        def on_queue_configure(event):
            self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))
        self.queue_container.bind("<Configure>", on_queue_configure)
        
        def on_queue_canvas_configure(event):
            self.queue_canvas.itemconfig(self.queue_window, width=event.width)
        self.queue_canvas.bind("<Configure>", on_queue_canvas_configure)
        
        def on_queue_mousewheel(event):
            bbox = self.queue_canvas.bbox("all")
            if bbox and bbox[3] > self.queue_canvas.winfo_height():
                self.queue_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        if os.name == 'nt':
            self.queue_canvas.bind("<Enter>", lambda e: self.root.bind_all("<MouseWheel>", on_queue_mousewheel))
            self.queue_canvas.bind("<Leave>", lambda e: self.root.unbind_all("<MouseWheel>"))

        clear_btn = tk.Label(main, text="limpar fila",
                             font=F_SMALL,
                             fg=C["text_muted"], bg=C["bg"],
                             cursor="hand2")
        clear_btn.pack(anchor="e")
        clear_btn.bind("<Button-1>", lambda e: self._clear_queue())

    def _build_converter_tab(self):
        main = self.converter_page

        # Campo para escolha do ficheiro de entrada
        self._label(main, "Ficheiro para Converter")
        file_row = tk.Frame(main, bg=C["bg"])
        file_row.pack(fill="x", pady=(4, 2))

        self.conv_file_entry = tk.Entry(file_row, textvariable=self.conv_file_var,
                                        font=F_MAIN, state="readonly",
                                        bg=C["entry_bg"], fg=C["text_dim"],
                                        readonlybackground=C["entry_bg"],
                                        relief="flat", bd=0,
                                        highlightthickness=1,
                                        highlightbackground=C["border"],
                                        highlightcolor=C["accent"])
        self.conv_file_entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=8)

        browse_file_btn = self._btn(file_row, "Escolher Ficheiro", self._browse_conv_file,
                                    color=C["border"], fg=C["text_dim"])
        browse_file_btn.pack(side="left", padx=(8, 0))

        # Preview do ficheiro / Informações
        self.conv_info_frame = tk.Frame(main, bg=C["surface"], bd=0,
                                        highlightthickness=1,
                                        highlightbackground=C["border"])
        self.conv_info_frame.pack(fill="x", pady=(8, 0))
        
        self.conv_file_label = tk.Label(self.conv_info_frame, text="Nenhum ficheiro selecionado",
                                        font=F_BOLD, fg=C["text_dim"], bg=C["surface"],
                                        wraplength=700, justify="left", anchor="w", padx=12, pady=12)
        self.conv_file_label.pack(fill="x")

        # Formato de saída
        self._label(main, "Formato de Saída")
        fmt_row = tk.Frame(main, bg=C["bg"])
        fmt_row.pack(fill="x", pady=(4, 0))

        # Inicializa o menu de formatos com todos os formatos combinados
        self.conv_formats_list = []
        self.conv_fmt_menu = ttk.Combobox(fmt_row, textvariable=self.conv_format_var,
                                          values=self.conv_formats_list,
                                          state="readonly", style="Pulsar.TCombobox",
                                          font=F_MAIN, takefocus=0)
        self.conv_fmt_menu.pack(side="left", fill="x", expand=True)
        self.conv_fmt_menu.bind("<<ComboboxSelected>>", lambda e: self.root.focus_set())

        # Directório de destino (Mostra que vai guardar na pasta de downloads)
        self._label(main, "Guardar em")
        dest_row = tk.Frame(main, bg=C["bg"])
        dest_row.pack(fill="x", pady=(4, 0))

        self.conv_dest_label = tk.Label(dest_row, textvariable=self.download_path,
                                        font=F_MAIN, anchor="w",
                                        bg=C["entry_bg"], fg=C["text_dim"],
                                        relief="flat", bd=0,
                                        highlightthickness=1,
                                        highlightbackground=C["border"])
        self.conv_dest_label.pack(side="left", fill="x", expand=True, ipady=8, ipadx=8)

        browse_dest_btn = self._btn(dest_row, "Escolher", self._browse_folder,
                                    color=C["surface2"], fg=C["text_dim"])
        browse_dest_btn.pack(side="left", padx=(8, 0))

        # Espaçador vertical para empurrar o botão para baixo e dar ar limpo
        tk.Frame(main, bg=C["bg"], height=80).pack()

        # Botão principal de ação do Conversor
        btn_frame = tk.Frame(main, bg=C["bg"], pady=12)
        btn_frame.pack(fill="x", side="bottom")

        self.conv_btn = tk.Button(btn_frame,
                                  text="🔄  CONVERTER",
                                  font=("Segoe UI", 16, "bold"),
                                  bg=C["accent"], fg="#ffffff",
                                  activebackground=C["accent2"],
                                  activeforeground="#ffffff",
                                  relief="flat", bd=0,
                                  cursor="hand2",
                                  command=self._start_conversion,
                                  padx=24, pady=10)
        self.conv_btn.pack(fill="x")

        # Hover effects
        self.conv_btn.bind("<Enter>", lambda e: self._conv_btn_hover_enter())
        self.conv_btn.bind("<Leave>", lambda e: self._conv_btn_hover_leave())

    def _browse_conv_file(self):
        filetypes = [
            ("Todos os Ficheiros Suportados", "*.mp4 *.mkv *.avi *.mov *.wmv *.webm *.flv *.mp3 *.wav *.m4a *.aac *.flac *.ogg *.png *.jpg *.jpeg *.webp *.heic *.heif *.bmp *.ico"),
            ("Vídeos", "*.mp4 *.mkv *.avi *.mov *.wmv *.webm *.flv"),
            ("Áudio", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
            ("Imagens", "*.png *.jpg *.jpeg *.webp *.heic *.heif *.bmp *.ico"),
            ("Todos os Ficheiros", "*.*")
        ]
        filenames = filedialog.askopenfilenames(filetypes=filetypes)
        if filenames:
            self.conv_files = list(filenames)
            # Use first file for display and processing
            self.conv_file_var.set(self.conv_files[0])
            self._update_conv_file_info(self.conv_files[0])
            # Update label to show count if multiple
            count = len(self.conv_files)
            if count > 1:
                self.conv_file_label.config(text=f"{count} ficheiros selecionados")
            else:
                # Single file info already set by _update_conv_file_info
                pass

    def _update_conv_file_info(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        size_bytes = os.path.getsize(filename)
        size_mb = size_bytes / (1024 * 1024)
        
        # Mapeamento do tipo de arquivo para definir formatos de saída
        audio_exts = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"]
        video_exts = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv"]
        image_exts = [".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif", ".bmp", ".ico"]
        
        file_type = "Desconhecido"
        target_formats = []
        
        if ext in audio_exts:
            file_type = "Áudio"
            target_formats = ["MP3", "WAV", "AAC", "FLAC", "OGG"]
        elif ext in video_exts:
            file_type = "Vídeo"
            # Pode converter para vídeo ou extrair áudio!
            target_formats = ["MP4", "MKV", "AVI", "WEBM", "MP3", "WAV", "AAC"]
        elif ext in image_exts:
            file_type = "Imagem"
            target_formats = ["JPG", "PNG", "WEBP", "ICO", "BMP"]
            
        basename = os.path.basename(filename)
        self.conv_file_label.config(
            text=f"📄 Nome: {basename}\n"
                 f"⚙️ Tipo: {file_type} ({ext.upper()})\n"
                 f"💾 Tamanho: {size_mb:.2f} MB",
            fg=C["text"]
        )
        
        # Filtra os formatos disponíveis para não mostrar o mesmo formato de entrada
        current_fmt_upper = ext.replace(".", "").upper()
        if current_fmt_upper == "JPEG":
            current_fmt_upper = "JPG"
        if current_fmt_upper == "HEIF":
            current_fmt_upper = "HEIC"
            
        filtered_formats = [f for f in target_formats if f != current_fmt_upper]
        
        self.conv_fmt_menu.config(values=filtered_formats)
        if filtered_formats:
            self.conv_format_var.set(filtered_formats[0])
        else:
            self.conv_format_var.set("")

    def _switch_tab(self, tab):
        if tab == "downloader":
            self.converter_page.pack_forget()
            self.downloader_page.pack(fill="both", expand=True, padx=12, pady=12)
            self.tab_downloader_btn.config(bg=C["accent"], fg="#ffffff")
            self.tab_converter_btn.config(bg=C["surface2"], fg=C["text_dim"])
        elif tab == "converter":
            self.downloader_page.pack_forget()
            self.converter_page.pack(fill="both", expand=True)
            self.tab_downloader_btn.config(bg=C["surface2"], fg=C["text_dim"])
            self.tab_converter_btn.config(bg=C["accent"], fg="#ffffff")

    def _conv_btn_hover_enter(self):
        if self.is_converting:
            self.conv_btn.config(bg="#dc2626")  # Vermelho de cancelamento
        else:
            self.conv_btn.config(bg=C["accent2"])

    def _conv_btn_hover_leave(self):
        if self.is_converting:
            self.conv_btn.config(bg=C["error"])
        else:
            self.conv_btn.config(bg=C["accent"])

    def _start_conversion(self):
        if self.is_converting:
            self._cancel_conversion()
            return

        # Determine list of files to convert
        files = getattr(self, 'conv_files', None)
        if not files:
            # Fallback to single file variable
            single_path = self.conv_file_var.get()
            if not single_path:
                messagebox.showwarning("Ficheiro em falta", "Seleciona um ficheiro válido para converter.")
                return
            files = [single_path]
        else:
            if not files:
                messagebox.showwarning("Ficheiro em falta", "Seleciona pelo menos um ficheiro para converter.")
                return

        target_fmt = self.conv_format_var.get()
        if not target_fmt:
            messagebox.showwarning("Formato em falta", "Seleciona o formato de destino.")
            return

        # Prepare output directory
        output_dir = self.download_path.get()
        os.makedirs(output_dir, exist_ok=True)

        # Start batch conversion in a thread
        self.is_converting = True
        self.conv_btn.config(text="■  CANCELAR", bg=C["error"])
        self.progress_var.set(0)
        self.open_folder_btn.pack_forget()

        self.conv_thread = threading.Thread(
            target=self._run_batch_conversion,
            args=(files, target_fmt),
            daemon=True
        )
        self.conv_thread.start()

    def _run_batch_conversion(self, files, target_fmt):
        for input_path in files:
            basename = os.path.basename(input_path)
            name_without_ext = os.path.splitext(basename)[0]
            output_ext = target_fmt.lower()
            output_path = os.path.join(self.download_path.get(), f"{name_without_ext}.{output_ext}")
            # Check replace prompt for each file
            if os.path.exists(output_path):
                if not messagebox.askyesno("Substituir ficheiro?", f"O ficheiro já existe:\n{output_path}\n\nPretendes substituir?"):
                    continue
            # Run conversion for this file
            self._run_conversion(input_path, output_path, target_fmt)
        # After batch completed, reset UI state
        self.root.after(0, lambda: self._on_conversion_done(success=True, cancelled=False))

    def _run_conversion(self, input_path, output_path, target_fmt):
        ext = os.path.splitext(input_path)[1].lower()
        image_exts = [".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif", ".bmp", ".ico"]
        
        self._safe_status("A converter...", C["warn"])
        self._safe_log(f"🔄 A iniciar conversão de {os.path.basename(input_path)} para {target_fmt}...", "info")
        
        if ext in image_exts:
            # Conversão de imagem (Pillow + pillow-heif se HEIC)
            self._safe_phase("connecting")  # Modo indeterminado
            try:
                # Carrega imagem
                if ext in (".heic", ".heif") and not HEIF_AVAILABLE:
                    raise Exception("Suporte a HEIC indisponível (pillow-heif não carregado).")
                
                from PIL import Image
                img = Image.open(input_path)
                
                # Se for JPG/JPEG, remove canal alpha (transparência)
                if target_fmt.upper() in ("JPG", "JPEG"):
                    if img.mode in ("RGBA", "LA", "P"):
                        img = img.convert("RGB")
                
                # Salva
                save_fmt = target_fmt.upper()
                if save_fmt == "JPG":
                    save_fmt = "JPEG"
                img.save(output_path, save_fmt)
                
                self._safe_log(f"✓ Conversão de imagem concluída: {os.path.basename(output_path)}", "ok")
                self._safe_status("Conversão concluída!", C["success"])
                self._safe_progress(100)
                self._safe_done_conversion(success=True)
            except Exception as e:
                self._safe_log(f"✗ Erro na conversão de imagem: {str(e)}", "err")
                self._safe_status("Erro na conversão", C["error"])
                self._safe_done_conversion(success=False)
        else:
            # Conversão de áudio/vídeo (FFmpeg)
            ffmpeg_path = self._get_ffmpeg_path()
            if not ffmpeg_path:
                self._safe_log("✗ Erro: FFmpeg não encontrado! Impossível converter áudio/vídeo.", "err")
                self._safe_status("FFmpeg em falta", C["error"])
                self._safe_done_conversion(success=False)
                return
                
            # Verifica duração para a barra de progresso
            total_duration = self._get_media_duration(input_path)
            if total_duration:
                self._safe_log(f"Duração detetada: {total_duration:.1f} segundos", "info")
                self._safe_phase("downloading")  # Determinado
            else:
                self._safe_phase("connecting")  # Indeterminado se falhar obter duração
                
            # Constrói o comando FFmpeg
            cmd = [ffmpeg_path, "-y", "-i", input_path]
            
            fmt_lower = target_fmt.lower()
            if fmt_lower == "mp3":
                cmd.extend(["-vn", "-c:a", "libmp3lame", "-b:a", "320k"])
            elif fmt_lower == "wav":
                cmd.extend(["-vn", "-c:a", "pcm_s16le"])
            elif fmt_lower == "aac":
                cmd.extend(["-vn", "-c:a", "aac", "-b:a", "256k"])
            elif fmt_lower == "flac":
                cmd.extend(["-vn", "-c:a", "flac"])
            elif fmt_lower == "ogg":
                cmd.extend(["-vn", "-c:a", "libvorbis", "-q:a", "6"])
            elif fmt_lower == "mp4":
                cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-preset", "fast"])
            elif fmt_lower == "mkv":
                cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-preset", "fast"])
            elif fmt_lower == "avi":
                cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-preset", "fast"])
            elif fmt_lower == "webm":
                cmd.extend(["-c:v", "libvpx-vp9", "-c:a", "libvorbis", "-b:v", "0", "-crf", "30", "-preset", "fast"])
                
            cmd.append(output_path)
            
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                self.conv_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=creationflags
                )
                
                for line in iter(self.conv_process.stdout.readline, ''):
                    line = line.strip()
                    if line:
                        # Log FFmpeg no console
                        if "time=" in line:
                            # Tenta parsear tempo para progresso
                            time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                            if time_match and total_duration:
                                h, m, s = float(time_match.group(1)), float(time_match.group(2)), float(time_match.group(3))
                                curr_sec = h * 3600 + m * 60 + s
                                pct = min(100.0, (curr_sec / total_duration) * 100)
                                self._safe_progress(pct)
                                self._safe_status(f"A converter... {pct:.1f}%", C["warn"])
                        else:
                            # Se for aviso ou info útil
                            if not line.startswith("frame=") and not line.startswith("size="):
                                self._safe_log(line, "info")
                                
                self.conv_process.stdout.close()
                return_code = self.conv_process.wait()
                
                if return_code == 0:
                    self._safe_log(f"✓ Conversão concluída: {os.path.basename(output_path)}", "ok")
                    self._safe_status("Conversão concluída!", C["success"])
                    self._safe_progress(100)
                    self._safe_done_conversion(success=True)
                else:
                    if self.is_converting: # se não foi cancelado
                        self._safe_log(f"✗ Erro no FFmpeg (código {return_code})", "err")
                        self._safe_status("Erro na conversão", C["error"])
                        self._safe_done_conversion(success=False)
            except Exception as e:
                self._safe_log(f"✗ Erro inesperado no subprocesso do FFmpeg: {str(e)}", "err")
                self._safe_status("Erro inesperado", C["error"])
                self._safe_done_conversion(success=False)

    def _cancel_conversion(self):
        self._log("⊘ Conversão cancelada pelo utilizador.", "warn")
        self.is_converting = False
        if self.conv_process:
            try:
                self.conv_process.kill()
            except Exception:
                pass
        self._safe_done_conversion(success=False, cancelled=True)
        
    def _safe_done_conversion(self, success=False, cancelled=False):
        self.root.after(0, lambda: self._on_conversion_done(success, cancelled))
        
    def _on_conversion_done(self, success, cancelled):
        self.is_converting = False
        self.conv_process = None
        self.conv_btn.config(state="normal", text="🔄  CONVERTER", bg=C["accent"])
        self._set_phase(None)
        
        if cancelled:
            self._set_status("Conversão cancelada.", C["warn"])
        elif success:
            self._set_status(f"Conversão concluída! Guardado em: {self.download_path.get()}", C["success"])
            self.open_folder_btn.pack(side="right")
            if WINSOUND_AVAILABLE:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass
        else:
            self._set_status("Conversão falhou.", C["error"])

    def _get_media_duration(self, filepath):
        # Encontra o ffprobe
        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        ffprobe_exe = os.path.join(app_dir, "ffprobe.exe")
        if not os.path.exists(ffprobe_exe):
            if shutil.which("ffprobe") is not None:
                ffprobe_exe = "ffprobe"
            else:
                return None
        
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            cmd = [ffprobe_exe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags, timeout=5)
            return float(res.stdout.strip())
        except Exception:
            return None

    def _get_ffmpeg_path(self):
        if shutil.which("ffmpeg") is not None:
            return "ffmpeg"
        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        local_ffmpeg = os.path.join(app_dir, "ffmpeg.exe")
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
        return None



        # Inicializa o log com a visibilidade salva

    def _style_ttk(self):
        s = ttk.Style()
        s.theme_use("clam")

        # Remove a borda pontilhada de foco interna do Combobox
        s.layout("Pulsar.TCombobox", [
            ('Combobox.field', {'children': [
                ('Combobox.downarrow', {'side': 'right', 'sticky': 'ns'}),
                ('Combobox.padding', {'children': [
                    ('Combobox.textarea', {'sticky': 'nswe'})
                ], 'expand': '1', 'sticky': 'nswe'})
            ], 'sticky': 'nswe'})
        ])

        s.configure("Pulsar.TCombobox",
                     fieldbackground=C["entry_bg"],
                     background=C["entry_bg"],
                     foreground=C["text"],
                     arrowcolor=C["accent"],
                     borderwidth=0,
                     relief="flat",
                     selectbackground=C["entry_bg"],
                     selectforeground=C["text"],
                     padding=(10, 8))
        s.map("Pulsar.TCombobox",
              fieldbackground=[("readonly", C["entry_bg"]),
                               ("readonly focus", C["entry_bg"])],
              foreground=[("readonly", C["text"])],
              selectbackground=[("readonly", C["entry_bg"]),
                                ("readonly focus", C["entry_bg"])],
              selectforeground=[("readonly", C["text"]),
                                ("readonly focus", C["text"])])
        s.configure("Pulsar.Horizontal.TProgressbar",
                     troughcolor=C["surface2"],
                     background=C["accent"],
                     borderwidth=0,
                     thickness=10)

    def _label(self, parent, text, attr=None):
        lbl = tk.Label(parent, text=text,
                       font=F_BOLD,
                       fg=C["text_dim"], bg=C["bg"],
                       anchor="w")
        lbl.pack(fill="x", pady=(12, 0))
        if attr:
            setattr(self, attr, lbl)
        return lbl

    def _btn(self, parent, text, cmd, color=None, fg=None):
        color = color or C["surface2"]
        fg    = fg or C["text_dim"]
        b = tk.Button(parent, text=text, font=F_BOLD,
                      bg=color, fg=fg,
                      activebackground=C["accent"], activeforeground="#fff",
                      relief="flat", bd=0, cursor="hand2",
                      command=cmd, padx=14, pady=8)
        return b

    def _sep(self, pady=8, parent=None):
        parent = parent or self.root
        f = tk.Frame(parent, bg=C["border"], height=1)
        f.pack(fill="x", padx=28, pady=pady)

    # --- Efeitos Visuais do Botão Principal ---
    def _btn_hover_enter(self):
        if self.engine.is_downloading:
            self.dl_btn.config(bg="#dc2626")  # Cor de destaque de interrupção (vermelho)
        else:
            self.dl_btn.config(bg=C["accent2"])

    def _btn_hover_leave(self):
        if self.engine.is_downloading:
            self.dl_btn.config(bg=C["error"])
        else:
            self.dl_btn.config(bg=C["accent"])

    # --- Controle de Visibilidade do Log ---
    def _toggle_log(self, *_):
        is_visible = self.show_log_var.get()
        self.show_log_var.set(not is_visible)

        if self.show_log_var.get():
            self.log_toggle_btn.config(text="▼ Ocultar log")
            self.log_frame.pack(fill="both", expand=True, pady=(0, 12))
        else:
            self.log_toggle_btn.config(text="▶ Mostrar log")
            self.log_frame.pack_forget()

        # Salva o estado de visibilidade configurado
        self.config.set("show_log", self.show_log_var.get())
        self.config.save()

    # --- Colagem Automática do Link ---
    def _on_focus_in(self, event):
        """Cola a URL da área de transferência ao focar a janela, se o campo estiver vazio."""
        # Evita colisões de eventos gerados por subwidgets da janela
        if event.widget != self.root:
            return
        if self.url_var.get().strip():
            return  # Campo já contém texto
        if self._auto_pasted:
            return  # Impede nova colagem automática na mesma ativação de foco

        try:
            clipboard = self.root.clipboard_get().strip()
            if clipboard.startswith(("http://", "https://")):
                self.url_var.set(clipboard)
                self._auto_pasted = True
                self._log("📋 URL colado automaticamente do clipboard.", "info")
        except (tk.TclError, Exception):
            pass  # Ignora erros de clipboard vazio ou sem permissão de leitura

    def _reset_auto_paste(self, *_):
        """Reseta a flag de colagem automática ao detectar alteração manual no URL."""
        self._auto_pasted = False

    # --- Colagem Manual do Clipboard ---
    def _paste_from_clipboard(self):
        """Copia o conteúdo textual da área de transferência para o campo de link."""
        try:
            clipboard = self.root.clipboard_get().strip()
            if clipboard:
                self.url_var.set(clipboard)
                self._log("📋 URL colado do clipboard.", "info")
        except (tk.TclError, Exception):
            self._log("⚠ Clipboard vazio ou inacessível.", "warn")

    # --- Controle de Transição da Barra de Progresso ---
    def _set_phase(self, phase):
        """Controla a animação e o tipo de progresso com base na fase da tarefa."""
        if phase in ("connecting", "merging"):
            # Modo indeterminado: exibe animação cíclica durante conexão/conversão
            self.prog_bar.config(mode="indeterminate")
            self.prog_bar.start(15)
        elif phase == "downloading":
            # Modo determinado: exibe porcentagem numérica exata do download
            self.prog_bar.stop()
            self.prog_bar.config(mode="determinate")
        else:
            # Modo finalizado: zera o estado visual da barra
            self.prog_bar.stop()
            self.prog_bar.config(mode="determinate")

    # --- Carregamento de Detalhes e Miniaturas ---
    def _on_url_change(self, *_):
        """Inicia o processo de obtenção de metadados ao alterar a URL."""
        url = self.url_var.get().strip()
        self._thumbnail_job += 1
        current_job = self._thumbnail_job

        if not url or not url.startswith(("http://", "https://")):
            self._hide_thumbnail()
            return

        # Oculta a miniatura anterior antes de carregar o novo link
        self._hide_thumbnail()

        if not YT_DLP_AVAILABLE:
            return

        # Inicia a thread secundária para recuperação de metadados
        thread = threading.Thread(
            target=self._fetch_video_info,
            args=(url, current_job),
            daemon=True
        )
        thread.start()

    def _fetch_video_info(self, url, job_id):
        """Busca os metadados do vídeo em uma thread em segundo plano."""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'socket_timeout': 8,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Revalida se o link consultado ainda é o ativo na UI
            if job_id != self._thumbnail_job:
                return

            title = info.get("title", "Sem título")
            channel = info.get("uploader", info.get("channel", ""))
            duration = info.get("duration", 0)
            thumbnail_url = info.get("thumbnail", "")

            # Formatação do tempo de duração do vídeo (HH:MM:SS)
            if duration:
                mins, secs = divmod(int(duration), 60)
                hours, mins = divmod(mins, 60)
                if hours:
                    dur_str = f"{hours}:{mins:02d}:{secs:02d}"
                else:
                    dur_str = f"{mins}:{secs:02d}"
            else:
                dur_str = ""

            # Realiza o download da imagem caso a biblioteca Pillow esteja ativa
            thumb_img = None
            if PIL_AVAILABLE and thumbnail_url:
                try:
                    req = urllib.request.Request(thumbnail_url, headers={
                        'User-Agent': 'Mozilla/5.0'
                    })
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = resp.read()
                    img = Image.open(io.BytesIO(data))
                    img = img.resize((120, 68), Image.LANCZOS)
                    thumb_img = ImageTk.PhotoImage(img)
                except Exception:
                    pass

            # Segunda validação de concorrência antes de pintar na tela
            if job_id != self._thumbnail_job:
                return

            # Envia as atualizações visuais para execução na thread principal
            self.root.after(0, lambda: self._show_thumbnail(title, channel, dur_str, thumb_img))

        except Exception:
            # Oculta a miniatura em caso de falha de conexão ou erro do yt-dlp
            if job_id == self._thumbnail_job:
                self.root.after(0, self._hide_thumbnail)

    def _show_thumbnail(self, title, channel, duration, thumb_img):
        """Atualiza a interface para exibir os metadados e imagem extraídos."""
        self.thumb_title_label.config(text=title, fg=C["text"])
        self.thumb_channel_label.config(text=channel, fg=C["text_dim"])
        self.thumb_duration_label.config(text=f"⏱ {duration}" if duration else "")

        if thumb_img:
            self._thumbnail_image = thumb_img
            self.thumb_img_label.config(image=thumb_img, width=0, height=0) # Redefine as dimensões para exibir a imagem real
        else:
            self.thumb_img_label.config(image="", width=17, height=4)

    def _hide_thumbnail(self):
        """Restaura a visualização inicial da miniatura para modo placeholder."""
        if hasattr(self, 'thumb_title_label'):
            self.thumb_title_label.config(text="A aguardar link...", fg=C["text_dim"])
            self.thumb_channel_label.config(text="Insere um URL para ver os detalhes", fg=C["text_muted"])
            self.thumb_duration_label.config(text="")
            self.thumb_img_label.config(image="", width=17, height=4)
        self._thumbnail_image = None

    # --- Acesso Rápido ao Diretório ---
    def _open_download_folder(self):
        """Abre o diretório configurado de downloads usando o gerenciador de arquivos nativo."""
        path = self.download_path.get()
        if os.path.isdir(path):
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        else:
            messagebox.showwarning("Pasta não encontrada",
                                   f"A pasta não existe:\n{path}")

    # --- Atualização Dinâmica do yt-dlp ---
    def _update_ytdlp(self):
        """Inicia o procedimento de atualização da biblioteca yt-dlp."""
        if self.engine.is_downloading:
            messagebox.showwarning("Download em curso",
                                   "Espera que o download termine antes de atualizar.")
            return

        self.update_btn.config(state="disabled", text="A atualizar...", fg=C["warn"])
        self._log("🔄 A atualizar yt-dlp...", "info")
        self._set_status("A atualizar yt-dlp...", C["warn"])

        thread = threading.Thread(target=self._run_update_ytdlp, daemon=True)
        thread.start()

    def _run_update_ytdlp(self):
        """Executa a atualização do yt-dlp em segundo plano."""
        try:
            app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            local_ytdlp = os.path.join(app_dir, "yt-dlp.exe")

            if getattr(sys, 'frozen', False):
                # No modo compilado .exe, descarrega o yt-dlp.exe mais recente do GitHub
                self.root.after(0, lambda: self._log("📥 A descarregar yt-dlp.exe mais recente do GitHub...", "info"))
                self.root.after(0, lambda: self._set_status("A atualizar yt-dlp...", C["warn"]))

                import urllib.request
                url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
                temp_path = os.path.join(app_dir, "yt-dlp_temp.exe")
                
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=45) as response, open(temp_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)

                # Substituir o antigo pelo novo
                if os.path.exists(local_ytdlp):
                    try:
                        os.remove(local_ytdlp)
                    except OSError:
                        # Se estiver em uso, tenta renomear para remover no próximo arranque
                        if os.path.exists(local_ytdlp + ".bak"):
                            try:
                                os.remove(local_ytdlp + ".bak")
                            except Exception:
                                pass
                        os.rename(local_ytdlp, local_ytdlp + ".bak")
                
                os.rename(temp_path, local_ytdlp)
                
                # Apagar ficheiro .bak se existir
                try:
                    if os.path.exists(local_ytdlp + ".bak"):
                        os.remove(local_ytdlp + ".bak")
                except Exception:
                    pass

                self.root.after(0, lambda: self._log("✓ yt-dlp atualizado com sucesso!", "ok"))
                self.root.after(0, lambda: self._set_status("yt-dlp atualizado com sucesso!", C["success"]))
                self.root.after(0, lambda: messagebox.showinfo("Atualização Concluída", "O yt-dlp foi atualizado para a versão mais recente!"))
                return

            # No modo desenvolvimento script, executa pip install -U
            python_exe = sys.executable
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                [python_exe, "-m", "pip", "install", "-U", "yt-dlp"],
                capture_output=True, text=True, timeout=60,
                creationflags=creationflags
            )

            if result.returncode == 0:
                # Analisa o retorno do pip para exibir a mensagem correta
                if "already satisfied" in result.stdout.lower() or "already up-to-date" in result.stdout.lower():
                    self.root.after(0, lambda: self._log("✓ yt-dlp já está na versão mais recente.", "ok"))
                    self.root.after(0, lambda: self._set_status("yt-dlp atualizado!", C["success"]))
                else:
                    self.root.after(0, lambda: self._log("✓ yt-dlp atualizado com sucesso! Reinicia a app.", "ok"))
                    self.root.after(0, lambda: self._set_status("yt-dlp atualizado — reinicia a app!", C["success"]))
            else:
                error_msg = result.stderr[:100] if result.stderr else "Erro desconhecido"
                self.root.after(0, lambda: self._log(f"✗ Erro ao atualizar: {error_msg}", "err"))
                self.root.after(0, lambda: self._set_status("Erro ao atualizar yt-dlp", C["error"]))

        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: self._log("✗ Timeout ao atualizar yt-dlp.", "err"))
        except Exception as e:
            self.root.after(0, lambda: self._log(f"✗ Erro: {str(e)[:80]}", "err"))
        finally:
            self.root.after(0, lambda: self.update_btn.config(
                state="normal", text="🔄 Atualizar yt-dlp", fg=C["text_muted"]))

# --- Processamento Principal e Regras de Negócio ---

    def _detect_platform(self, *_):
        url = self.url_var.get()
        for name, info in PLATFORMS.items():
            if re.search(info["pattern"], url, re.I):
                self.detected_platform.set(f"{info['icon']} {name}")
                self.platform_badge.config(fg=C["success"])
                return
        if url:
            self.detected_platform.set("⚠ Desconhecida")
            self.platform_badge.config(fg=C["warn"])
        else:
            self.detected_platform.set("")

    def _browse_folder(self):
        path = filedialog.askdirectory(initialdir=self.download_path.get())
        if path:
            self.download_path.set(path)

    def _add_to_queue(self):
        url = self.url_var.get().strip()
        if not url:
            return
        if not self._validate_url(url):
            return
        self.queue.add(url, self.format_var.get())
        self.url_var.set("")
        self._render_queue()
        display_log = url[:60] + "..." if len(url) > 60 else url
        self._log(f"Adicionado à fila: {display_log}", "info")

    def _clear_queue(self):
        self.queue.clear()
        self._render_queue()

    def _render_queue(self):
        for widget in self.queue_container.winfo_children():
            widget.destroy()
            
        items = self.queue.items()
        self.queue_label.config(text=f"Fila  ({len(items)} itens)")
        
        for idx, item in enumerate(items):
            url = item["url"]
            display = url[:65] + "..." if len(url) > 65 else url
            
            row_frame = tk.Frame(self.queue_container, bg=C["surface"])
            row_frame.pack(fill="x", pady=1)
            
            lbl = tk.Label(row_frame, text=f" {idx + 1}.  {display}",
                           font=F_MONO, bg=C["surface"], fg=C["text_dim"], anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            
                # Botão de remoção (mostrado no hover)
            btn_rm = tk.Label(row_frame, text="✕", font=F_BOLD,
                              bg=C["surface"], fg=C["error"], cursor="hand2")
            
                # Define comportamento visual ao passar o mouse
            def on_enter(e, r=row_frame, l=lbl, b=btn_rm):
                r.config(bg=C["border"])
                l.config(bg=C["border"], fg=C["text"])
                b.config(bg=C["border"], fg="#ff8080")
                b.pack(side="right", padx=(0, 8))
            
            def on_leave(e, r=row_frame, l=lbl, b=btn_rm):
                r.config(bg=C["surface"])
                l.config(bg=C["surface"], fg=C["text_dim"])
                b.config(bg=C["surface"])
                b.pack_forget()
            
            row_frame.bind("<Enter>", on_enter)
            row_frame.bind("<Leave>", on_leave)
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)
            btn_rm.bind("<Enter>", on_enter)
            btn_rm.bind("<Leave>", on_leave)
            
            btn_rm.bind("<Button-1>", lambda e, i=idx: self._remove_from_queue(i))

    def _remove_from_queue(self, index):
        self.queue.remove(index)
        self._render_queue()

    def _validate_url(self, url):
        """Verifica a validade do protocolo de rede do link."""
        if not url.startswith(("http://", "https://")):
            messagebox.showwarning(
                "URL inválida",
                "Introduz um URL válido (deve começar com http:// ou https://)."
            )
            return False
        return True

    def _save_prefs(self, *_):
        """Salva as configurações atuais no arquivo de configuração."""
        self.config.set("download_path", self.download_path.get())
        self.config.set("format", self.format_var.get())
        self.config.save()

    def _check_dependencies(self):
        # Verificar se existe yt-dlp.exe local
        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        local_ytdlp = os.path.join(app_dir, "yt-dlp.exe")
        
        if os.path.exists(local_ytdlp):
            # Obter versão do local
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                res = subprocess.run([local_ytdlp, "--version"], capture_output=True, text=True, creationflags=creationflags)
                version = res.stdout.strip()
                self._log(f"yt-dlp (local exe) {version} pronto.", "ok")
            except Exception:
                self._log("yt-dlp (local exe) pronto.", "ok")
        elif not YT_DLP_AVAILABLE:
            self._log("⚠  yt-dlp não encontrado. Clica em 'Atualizar yt-dlp' para descarregar.", "err")
            self._set_status("⚠  yt-dlp em falta — clica em Atualizar yt-dlp", C["error"])
        else:
            self._log(f"yt-dlp (embutido) {yt_dlp.version.__version__} pronto.", "ok")

        if not self._is_ffmpeg_installed():
            self._log("⚠  FFmpeg NÃO ENCONTRADO! Audio/MP4 não vai juntar.", "warn")
        else:
            self._log("FFmpeg pronto.", "ok")

        if not HEIF_AVAILABLE:
            self._log("⚠  pillow-heif não encontrado! Conversões de HEIC (iPhone) não irão funcionar.", "warn")
        else:
            self._log("pillow-heif (suporte HEIC do iPhone) pronto.", "ok")

    def _is_ffmpeg_installed(self):
        """Verifica a presença da dependência FFmpeg no PATH ou localmente."""
        if shutil.which("ffmpeg") is not None:
            return True
        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        local_ffmpeg = os.path.join(app_dir, "ffmpeg.exe")
        return os.path.exists(local_ffmpeg)

    def _download_ffmpeg(self):
        """Faz o download e instalação automatizada do pacote FFmpeg compilado para Windows."""
        self.dl_btn.config(state="disabled")
        self._set_status("A descarregar FFmpeg (cerca de 100MB)...", C["warn"])
        self.prog_bar.config(mode="indeterminate")
        self.prog_bar.start(15)
        
        def run():
            temp_zip_path = ""
            try:
                import urllib.request
                import zipfile
                
                app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
                
                # Define diretório temporário para download do instalador compactado
                temp_zip_path = os.path.join(app_dir, "ffmpeg_temp.zip")
                
                self.root.after(0, lambda: self._log("📥 A descarregar FFmpeg de gyan.dev...", "info"))
                
                # Executa requisição do arquivo compactado configurando User-Agent
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as response, open(temp_zip_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                
                self.root.after(0, lambda: self._log("📦 A extrair ffmpeg.exe...", "info"))
                self.root.after(0, lambda: self._set_status("A extrair FFmpeg...", C["warn"]))
                
                # Extrai unicamente o executável ffmpeg.exe do arquivo compactado
                extracted = False
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    for file_info in zip_ref.infolist():
                        if file_info.filename.endswith("bin/ffmpeg.exe"):
                            # Grava o binário extraído no diretório principal da aplicação
                            with zip_ref.open(file_info) as source, open(os.path.join(app_dir, "ffmpeg.exe"), "wb") as target:
                                shutil.copyfileobj(source, target)
                            extracted = True
                            break
                
                # Exclui o instalador compactado temporário da máquina
                if temp_zip_path and os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)
                
                if extracted:
                    self.root.after(0, lambda: self._log("✓ FFmpeg descarregado e instalado com sucesso!", "ok"))
                    self.root.after(0, lambda: messagebox.showinfo("FFmpeg Instalado", "O FFmpeg foi descarregado e instalado com sucesso na pasta da app! Já podes começar a descarregar vídeos/músicas."))
                    self.root.after(0, lambda: self._set_status("FFmpeg instalado com sucesso.", C["success"]))
                else:
                    self.root.after(0, lambda: self._log("✗ Erro: Não foi possível encontrar ffmpeg.exe dentro do ficheiro descarregado.", "err"))
                    self.root.after(0, lambda: messagebox.showerror("Erro de Instalação", "O download foi concluído, mas o ffmpeg.exe não foi encontrado no arquivo."))
                    self.root.after(0, lambda: self._set_status("Erro ao instalar FFmpeg.", C["error"]))
                    
            except Exception as e:
                self.root.after(0, lambda: self._log(f"✗ Erro ao descarregar FFmpeg: {str(e)[:80]}", "err"))
                self.root.after(0, lambda: messagebox.showerror("Erro no download", f"Ocorreu um erro ao descarregar o FFmpeg:\n{str(e)[:120]}\n\nPodes descarregá-lo manualmente e colocá-lo na pasta da aplicação."))
                self.root.after(0, lambda: self._set_status("Falha no download do FFmpeg.", C["error"]))
                # Exclui o instalador compactado temporário da máquina se existir
                try:
                    if temp_zip_path and os.path.exists(temp_zip_path):
                        os.remove(temp_zip_path)
                except Exception:
                    pass
            finally:
                self.root.after(0, self._stop_ffmpeg_download_loading)

        threading.Thread(target=run, daemon=True).start()

    def _stop_ffmpeg_download_loading(self):
        self.prog_bar.stop()
        self.prog_bar.config(mode="determinate")
        self.progress_var.set(0)
        self.dl_btn.config(state="normal")

    def _start_download(self):
        # Age como interrupção se um processo de download já estiver em andamento
        if self.engine.is_downloading:
            self.engine.cancel()
            self.dl_btn.config(state="disabled", text="A cancelar...")
            self._set_status("A cancelar download...", C["warn"])
            return

        # Verifica se o yt-dlp está disponível (módulo Python ou executável local)
        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        local_ytdlp = os.path.join(app_dir, "yt-dlp.exe")
        if not YT_DLP_AVAILABLE and not os.path.exists(local_ytdlp):
            messagebox.showerror("Dependência em falta",
                                 "O yt-dlp não foi encontrado!\n\n"
                                 "Clica em '🔄 Atualizar yt-dlp' para descarregar automaticamente,\n"
                                 "ou instala manualmente com: pip install yt-dlp")
            return

        if not self._is_ffmpeg_installed():
            msg = (
                "O FFmpeg não foi encontrado localmente nem no teu computador!\n\n"
                "Ele é OBRIGATÓRIO para juntar vídeo/áudio e para converter para MP3.\n\n"
                "Queres descarregar e instalar o FFmpeg automaticamente agora?\n"
                "(Recomendado, cerca de 100 MB. Irá descarregar em segundo plano)"
            )
            if messagebox.askyesno("FFmpeg em falta", msg):
                self._download_ffmpeg()
                return
            
            # Confirmação caso o usuário decida rodar a aplicação sem o FFmpeg
            msg_continue = (
                "Se continuares sem FFmpeg, os downloads podem ficar sem som ou "
                "com áudio e vídeo separados.\n\nPretendes continuar mesmo assim?"
            )
            if not messagebox.askyesno("Continuar sem FFmpeg?", msg_continue):
                return

        url = self.url_var.get().strip()
        if not url and not self.queue:
            messagebox.showwarning("URL vazia", "Introduz um URL ou adiciona itens à fila.")
            return

        # Executa validação de formato no link inserido
        if url and not self._validate_url(url):
            return

        # Decide se processará o link individual ativo ou a fila de tarefas
        if url:
            jobs = [{"url": url, "format": self.format_var.get()}]
        else:
            jobs = self.queue.items()

        # Oculta o atalho do diretório ao iniciar novo download
        self.open_folder_btn.pack_forget()

        # Atualiza a interface gráfica para o estado de cancelamento
        self.dl_btn.config(text="■  CANCELAR", bg=C["error"])
        self.progress_var.set(0)

        self.engine.start(jobs, self.download_path.get())

    def _on_all_done(self, cancelled=False):
        self.dl_btn.config(state="normal", text="▼  DESCARREGAR", bg=C["accent"])

        if cancelled:
            self._set_status("Download cancelado.", C["warn"])
        else:
            self._set_status(
                f"Concluído! Ficheiros em: {self.download_path.get()}", C["success"]
            )
            # Habilita o atalho visual para a pasta de downloads
            self.open_folder_btn.pack(side="right")

            # Emite alerta sonoro de conclusão no Windows
            if WINSOUND_AVAILABLE:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

        if self.queue:
            n = len(self.queue)
            self._log(f"Fila limpa automaticamente ({n} itens).", "info")
            self._clear_queue()

    def _set_status(self, msg, color=None):
        self.status_var.set(msg)
        if color:
            self.status_label.config(fg=color)

    def _log(self, msg, tag="info"):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _on_close(self):
        """Executa rotinas de persistência e encerramento da interface."""
        self._save_prefs()
        self.root.destroy()


# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    # Trata as invocações de multiprocessamento nativas do yt-dlp no executável compilation
    if len(sys.argv) > 1 and sys.argv[1] == "--run-yt-dlp":
        sys.argv.pop(1)  # Remove o parâmetro interno para evitar conflitos no yt-dlp
        import yt_dlp
        sys.exit(yt_dlp.main())

    root = tk.Tk()

    # Carrega e define o ícone padrão da interface gráfica se disponível
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base, "assets", "icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    app = PulsarUI(root)
    root.mainloop()