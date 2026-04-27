"""
╔══════════════════════════════════════╗
║        SLAYER  DOWNLOADER          ║
║   YouTube · MP3 · MP4 · Expansível   ║
╚══════════════════════════════════════╝

Dependências (instalar uma vez):
    pip install yt-dlp Pillow

Opcional (para conversão de áudio):
    Instalar ffmpeg: https://ffmpeg.org/download.html
    (No Windows: adicionar ao PATH)
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

# Sons do Windows
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

# Thumbnails (Pillow)
try:
    from PIL import Image, ImageTk
    import urllib.request
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ─────────────────────────────────────────────
#  TENTAR IMPORTAR YT-DLP
# ─────────────────────────────────────────────
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False


# ─────────────────────────────────────────────
#  PALETA DE CORES E ESTILOS
# ─────────────────────────────────────────────
C = {
    "bg":        "#0c1222",   # Azul escuro profundo
    "surface":   "#131d33",   # Azul marinho subtil
    "surface2":  "#1a2744",   # Azul para painéis
    "border":    "#263758",   # Borda azul suave
    "accent":    "#3b82f6",   # Azul vibrante (principal)
    "accent2":   "#2563eb",   # Azul mais escuro (hover)
    "text":      "#f0f4ff",   # Branco suave azulado
    "text_dim":  "#94a3c8",   # Cinza azulado claro
    "text_muted":"#566b90",   # Cinza azulado
    "success":   "#34d399",   # Verde suave
    "warn":      "#fbbf24",   # Amarelo quente
    "error":     "#f87171",   # Vermelho suave
    "entry_bg":  "#0e1629",   # Fundo de inputs
}

# Configurações de Fontes
F_MAIN = ("Calibri", 12)
F_BOLD = ("Calibri", 10, "bold")
F_TITLE = ("Calibri", 24, "bold")
F_SMALL = ("Calibri", 9)
F_MONO = ("Consolas", 10)

# Plataformas suportadas (expansível — basta adicionar aqui)
PLATFORMS = {
    "YouTube":  {"pattern": r"youtube\.com|youtu\.be",  "icon": "▶"},
    "Twitter":  {"pattern": r"twitter\.com|x\.com",     "icon": "✕"},
    "Instagram":{"pattern": r"instagram\.com",           "icon": "◉"},
    "TikTok":   {"pattern": r"tiktok\.com",              "icon": "♪"},
    "Vimeo":    {"pattern": r"vimeo\.com",               "icon": "◈"},
    "SoundCloud":{"pattern":r"soundcloud\.com",          "icon": "☁"},
}

# Formatos disponíveis — simples e direto
FORMAT_OPTIONS = {
    "🎵  Só Áudio (MP3)":          {"type": "audio", "ext": "mp3",  "quality": "320"},
    "🎬  Vídeo 720p":              {"type": "video", "ext": "mp4",  "quality": "720"},
    "🎬  Vídeo 1080p":             {"type": "video", "ext": "mp4",  "quality": "1080"},
    "⭐  Vídeo Melhor Qualidade":  {"type": "video", "ext": "mp4",  "quality": "best"},
}

# Caminho do ficheiro de configuração (junto ao script)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Máximo de itens no histórico
MAX_HISTORY = 15


# ─────────────────────────────────────────────
#  CONFIG MANAGER — Persistência de preferências
# ─────────────────────────────────────────────
class ConfigManager:
    """Lê e guarda preferências do utilizador num ficheiro JSON."""

    DEFAULTS = {
        "download_path": os.path.expanduser("~/Downloads"),
        "format": list(FORMAT_OPTIONS.keys())[0],
        "show_log": True,
        "history": [],
    }

    def __init__(self, path=CONFIG_PATH):
        self._path = path
        self._data = dict(self.DEFAULTS)
        self._data["history"] = list(self.DEFAULTS["history"])
        self._load()

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Só aceitar chaves conhecidas
            for key in self.DEFAULTS:
                if key in saved:
                    self._data[key] = saved[key]
        except (FileNotFoundError, json.JSONDecodeError):
            pass  # usa defaults

    def save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass  # falha silenciosa (permissões, disco cheio, etc.)

    def get(self, key):
        return self._data.get(key, self.DEFAULTS.get(key))

    def set(self, key, value):
        self._data[key] = value

    def add_history(self, url, fmt_label):
        """Adiciona um URL ao histórico de downloads."""
        entry = {
            "url": url,
            "format": fmt_label,
            "date": datetime.now().strftime("%d/%m %H:%M"),
        }
        # Remover duplicado se existir
        self._data["history"] = [
            h for h in self._data["history"] if h["url"] != url
        ]
        self._data["history"].insert(0, entry)
        # Limitar tamanho
        self._data["history"] = self._data["history"][:MAX_HISTORY]
        self.save()


# ─────────────────────────────────────────────
#  QUEUE MANAGER — Gestão de fila de downloads
# ─────────────────────────────────────────────
class QueueManager:
    """Gere a fila de URLs pendentes para download."""

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


# ─────────────────────────────────────────────
#  DOWNLOAD ENGINE — Lógica de download via subprocess
# ─────────────────────────────────────────────
class DownloadEngine:
    """Executa downloads em subprocessos separados, com suporte fiável a cancelamento."""

    # Padrões de erros de rede conhecidos
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
        """Lança os downloads numa thread daemon."""
        self.cancel_requested = False
        self.is_downloading = True
        self._last_activity_time = time.time()
        thread = threading.Thread(
            target=self._run_jobs, args=(jobs, dest), daemon=True
        )
        thread.start()

    def cancel(self):
        """Cancela imediatamente o subprocesso de download."""
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

        # Identificar o executável de forma segura para PyInstaller
        python_exe = sys.executable
        if getattr(sys, 'frozen', False):
            cmd = [python_exe, "--run-yt-dlp", "--no-warnings", "--socket-timeout", "15", "--newline"]
        else:
            cmd = [python_exe, "-m", "yt_dlp", "--no-warnings", "--socket-timeout", "15", "--newline"]

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
            # Esconde janela de consola preta no windows
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=creationflags
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
        """Verifica padrões de erros de rede conhecidos na saída do yt-dlp."""
        line_lower = line.lower()
        for pattern, message in self.NETWORK_ERRORS.items():
            if pattern in line_lower:
                self._on_log(f"✗  {message}", "err")
                self._on_status(message, C["error"])
                return True
        return False

    def _parse_output(self, line):
        """Analisa a saída padrão do yt-dlp para extrair a percentagem e a velocidade."""
        if line.startswith("[download]") and "%" in line:
            self._on_phase("downloading")
            parts = line.split()
            pct_str = next((p for p in parts if "%" in p), None)
            if pct_str:
                try:
                    pct = float(pct_str.replace('%', ''))

                    # Throttle: só atualizar a cada 0.3s para não sobrecarregar a UI
                    now = time.time()
                    if pct >= 100 or (now - self._last_progress_update) > 0.3:
                        self._last_progress_update = now
                        self._on_progress(pct)

                        # Extrair o resto da info de velocidade e ETA
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


# ─────────────────────────────────────────────
#  CLASSE PRINCIPAL — UI
# ─────────────────────────────────────────────
class PulsarUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SlayerDownloader")
        self.root.geometry("760x700")
        self.root.minsize(680, 600)
        self.root.configure(bg=C["bg"])

        # Managers
        self.config = ConfigManager()
        self.queue = QueueManager()
        self.engine = DownloadEngine(
            on_progress=self._safe_progress,
            on_log=self._safe_log,
            on_status=self._safe_status,
            on_done=self._safe_done,
            on_phase=self._safe_phase,
        )

        # Estado da UI
        self.download_path = tk.StringVar(value=self.config.get("download_path"))
        self.url_var        = tk.StringVar()
        self.format_var     = tk.StringVar(value=self.config.get("format"))
        self.status_var     = tk.StringVar(value="Pronto para descarregar.")
        self.progress_var   = tk.DoubleVar(value=0)
        self.detected_platform = tk.StringVar(value="")

        # Thumbnail state
        self._thumbnail_image = None   # Manter referência para evitar GC
        self._thumbnail_job = 0        # ID do job atual (para cancelar jobs antigos)

        # Auto-paste control
        self._auto_pasted = False

        # URL muda → detectar plataforma + buscar thumbnail
        self.url_var.trace_add("write", self._detect_platform)
        self.url_var.trace_add("write", self._on_url_change)

        # Guardar preferências ao mudar
        self.download_path.trace_add("write", self._save_prefs)
        self.format_var.trace_add("write", self._save_prefs)

        self._build_ui()
        self._check_dependencies()

        # Auto-paste ao focar a janela
        self.root.bind("<FocusIn>", self._on_focus_in)

        # Guardar preferências ao fechar
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── THREAD-SAFE CALLBACKS ────────────────
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

    # ── UI ──────────────────────────────────
    def _build_ui(self):
        self._style_ttk()

        # ── HEADER ──
        header = tk.Frame(self.root, bg=C["bg"], pady=16)
        header.pack(fill="x", padx=28)

        tk.Label(header, text="SLAYER", font=F_TITLE,
                 fg=C["accent"], bg=C["bg"]).pack(side="left")
        tk.Label(header, text="DOWNLOADER", font=("Calibri", 22),
                 fg=C["text_dim"], bg=C["bg"]).pack(side="left", padx=(6, 0))
        tk.Label(header, text="v2.0", font=F_SMALL,
                 fg=C["text_muted"], bg=C["bg"]).pack(side="left", padx=(10, 0), pady=(8, 0))

        # Botão atualizar yt-dlp (direita do header)
        self.update_btn = tk.Button(header, text="🔄 Atualizar yt-dlp",
                                     font=F_SMALL,
                                     bg=C["surface2"], fg=C["text_muted"],
                                     activebackground=C["accent"], activeforeground="#fff",
                                     relief="flat", bd=0, cursor="hand2",
                                     command=self._update_ytdlp,
                                     padx=8, pady=4)
        self.update_btn.pack(side="right")

        self._sep()

        # ── PAINEL PRINCIPAL ──
        main = tk.Frame(self.root, bg=C["bg"], padx=28)
        main.pack(fill="both", expand=True)

        # — URL —
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

        # Botão "Adicionar à fila"
        queue_btn = self._btn(url_row, "+ Fila", self._add_to_queue,
                              color=C["border"], fg=C["text_dim"])
        queue_btn.pack(side="left", padx=(4, 0))

        # — Thumbnail Container —
        self.thumb_container = tk.Frame(main, bg=C["bg"])
        self.thumb_container.pack(fill="x")
        
        # — Thumbnail preview —
        self.thumb_frame = tk.Frame(self.thumb_container, bg=C["surface"], bd=0,
                                    highlightthickness=1,
                                    highlightbackground=C["border"])
        # Inicialmente escondido
        self.thumb_img_label = tk.Label(self.thumb_frame, bg=C["surface"])
        self.thumb_img_label.pack(side="left", padx=(8, 10), pady=8)

        self.thumb_info_frame = tk.Frame(self.thumb_frame, bg=C["surface"])
        self.thumb_info_frame.pack(side="left", fill="both", expand=True, pady=8, padx=(0, 8))

        self.thumb_title_label = tk.Label(self.thumb_info_frame, text="",
                                          font=F_BOLD, fg=C["text"], bg=C["surface"],
                                          wraplength=450, justify="left", anchor="nw")
        self.thumb_title_label.pack(fill="x", anchor="w")

        self.thumb_channel_label = tk.Label(self.thumb_info_frame, text="",
                                             font=F_SMALL, fg=C["text_dim"], bg=C["surface"],
                                             anchor="w")
        self.thumb_channel_label.pack(fill="x", anchor="w", pady=(2, 0))

        self.thumb_duration_label = tk.Label(self.thumb_info_frame, text="",
                                              font=F_SMALL, fg=C["text_muted"], bg=C["surface"],
                                              anchor="w")
        self.thumb_duration_label.pack(fill="x", anchor="w")

        # — Histórico —
        self._build_history_section(main)

        # — Formato —
        self._label(main, "Formato")
        fmt_row = tk.Frame(main, bg=C["bg"])
        fmt_row.pack(fill="x", pady=(4, 0))

        self.fmt_menu = ttk.Combobox(fmt_row, textvariable=self.format_var,
                                     values=list(FORMAT_OPTIONS.keys()),
                                     state="readonly", style="Pulsar.TCombobox",
                                     font=F_MAIN, takefocus=0)
        self.fmt_menu.pack(side="left", fill="x", expand=True)
        self.fmt_menu.bind("<<ComboboxSelected>>", lambda e: self.root.focus_set())

        # Estilizar o dropdown
        self.root.option_add('*TCombobox*Listbox.selectBackground', C["accent"])
        self.root.option_add('*TCombobox*Listbox.selectForeground', C["text"])
        self.root.option_add('*TCombobox*Listbox.background', C["surface2"])
        self.root.option_add('*TCombobox*Listbox.foreground', C["text"])
        self.root.option_add('*TCombobox*Listbox.font', F_MAIN)

        # — Pasta destino —
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

        # — Fila de downloads —
        self._label(main, "Fila  (0 itens)", attr="queue_label")
        self.queue_frame = tk.Frame(main, bg=C["surface"], bd=0,
                                    highlightthickness=1,
                                    highlightbackground=C["border"])
        self.queue_frame.pack(fill="x", pady=(4, 0))
        
        self.queue_canvas = tk.Canvas(self.queue_frame, bg=C["surface"], highlightthickness=0, height=80)
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

        # — Barra de progresso —
        self._sep(pady=12)
        prog_frame = tk.Frame(self.root, bg=C["bg"], padx=28)
        prog_frame.pack(fill="x")

        self.prog_bar = ttk.Progressbar(prog_frame, variable=self.progress_var,
                                        maximum=100, style="Pulsar.Horizontal.TProgressbar")
        self.prog_bar.pack(fill="x", ipady=3)

        # — Status + Abrir Pasta —
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
        # Escondido inicialmente — aparece depois do download

        # — Botão principal (DESCARREGAR / CANCELAR) —
        btn_frame = tk.Frame(self.root, bg=C["bg"], padx=28, pady=16)
        btn_frame.pack(fill="x")

        self.dl_btn = tk.Button(btn_frame,
                                text="▼  DESCARREGAR",
                                font=("Segoe UI", 16, "bold"),
                                bg=C["accent"], fg="#ffffff",
                                activebackground=C["accent2"],
                                activeforeground="#ffffff",
                                relief="flat", bd=0,
                                cursor="hand2",
                                command=self._start_download,
                                padx=24, pady=16)
        self.dl_btn.pack(fill="x")

        # hover
        self.dl_btn.bind("<Enter>", lambda e: self._btn_hover_enter())
        self.dl_btn.bind("<Leave>", lambda e: self._btn_hover_leave())

        # Toggle Log
        self.show_log_var = tk.BooleanVar(value=bool(self.config.get("show_log")))

        # — Log de histórico —
        self._sep(pady=4)

        self.log_container = tk.Frame(self.root, bg=C["bg"])
        self.log_container.pack(fill="both", expand=True, side="bottom")

        # Cabeçalho do log (sempre visível)
        log_header = tk.Frame(self.log_container, bg=C["bg"], padx=28)
        log_header.pack(fill="x")

        self.log_toggle_btn = tk.Label(log_header, text="▼ Ocultar log" if self.show_log_var.get() else "▶ Mostrar log",
                                       font=F_SMALL,
                                       fg=C["text_muted"], bg=C["bg"], cursor="hand2")
        self.log_toggle_btn.pack(side="left", pady=(4, 4))
        self.log_toggle_btn.bind("<Button-1>", self._toggle_log)

        # Frame principal do log
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

        # Aplicar estado inicial do log
        if self.show_log_var.get():
            self.log_frame.pack(fill="both", expand=True, pady=(0, 12))

    def _build_history_section(self, parent):
        """Constrói a secção de histórico se houver itens."""
        history = self.config.get("history")
        if not history:
            self.hist_frame = None
            return

        self.hist_frame = tk.Frame(parent, bg=C["bg"])

        hist_header = tk.Frame(self.hist_frame, bg=C["bg"])
        hist_header.pack(fill="x")

        self._label(hist_header, "Histórico")

        clear_hist = tk.Label(hist_header, text="limpar",
                              font=F_SMALL,
                              fg=C["text_muted"], bg=C["bg"],
                              cursor="hand2")
        clear_hist.pack(side="right", pady=(12, 0))
        clear_hist.bind("<Button-1>", lambda e: self._clear_history())

        hist_row = tk.Frame(self.hist_frame, bg=C["bg"])
        hist_row.pack(fill="x", pady=(4, 0))

        hist_values = []
        for h in history:
            url_short = h['url'][:55] + "..." if len(h['url']) > 55 else h['url']
            hist_values.append(f"{h['date']}  ·  {url_short}")

        self.hist_var = tk.StringVar(value="")
        self.hist_menu = ttk.Combobox(hist_row, textvariable=self.hist_var,
                                      values=hist_values,
                                      state="readonly", style="Pulsar.TCombobox",
                                      font=F_SMALL, takefocus=0)
        self.hist_menu.pack(side="left", fill="x", expand=True)
        self.hist_menu.bind("<<ComboboxSelected>>", self._on_history_select)

        self.hist_frame.pack(fill="x")

    def _style_ttk(self):
        s = ttk.Style()
        s.theme_use("clam")

        # Remover o indicador de foco do Combobox
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

    def _sep(self, pady=8):
        f = tk.Frame(self.root, bg=C["border"], height=1)
        f.pack(fill="x", padx=28, pady=pady)

    # ── HOVER DO BOTÃO ──────────────────────
    def _btn_hover_enter(self):
        if self.engine.is_downloading:
            self.dl_btn.config(bg="#dc2626")  # vermelho hover
        else:
            self.dl_btn.config(bg=C["accent2"])

    def _btn_hover_leave(self):
        if self.engine.is_downloading:
            self.dl_btn.config(bg=C["error"])
        else:
            self.dl_btn.config(bg=C["accent"])

    # ── LOG TOGGLE ──────────────────────────
    def _toggle_log(self, *_):
        is_visible = self.show_log_var.get()
        self.show_log_var.set(not is_visible)

        if self.show_log_var.get():
            self.log_toggle_btn.config(text="▼ Ocultar log")
            self.log_frame.pack(fill="both", expand=True, pady=(0, 12))
        else:
            self.log_toggle_btn.config(text="▶ Mostrar log")
            self.log_frame.pack_forget()

        # Gravar a preferência no config
        self.config.set("show_log", self.show_log_var.get())
        self.config.save()

    # ── AUTO-PASTE ──────────────────────────
    def _on_focus_in(self, event):
        """Ao focar a janela, colar URL do clipboard se o campo estiver vazio."""
        # Só reagir ao foco da janela principal, não de widgets filhos
        if event.widget != self.root:
            return
        if self.url_var.get().strip():
            return  # campo já tem conteúdo
        if self._auto_pasted:
            return  # já colou nesta sessão de foco

        try:
            clipboard = self.root.clipboard_get().strip()
            if clipboard.startswith(("http://", "https://")):
                self.url_var.set(clipboard)
                self._auto_pasted = True
                self._log("📋 URL colado automaticamente do clipboard.", "info")
        except (tk.TclError, Exception):
            pass  # clipboard vazio ou inacessível

    def _reset_auto_paste(self, *_):
        """Reset auto-paste flag quando o URL muda manualmente."""
        self._auto_pasted = False

    # ── COLAR DO CLIPBOARD ──────────────────
    def _paste_from_clipboard(self):
        """Cola URL do clipboard para o campo de URL."""
        try:
            clipboard = self.root.clipboard_get().strip()
            if clipboard:
                self.url_var.set(clipboard)
                self._log("📋 URL colado do clipboard.", "info")
        except (tk.TclError, Exception):
            self._log("⚠ Clipboard vazio ou inacessível.", "warn")

    # ── PROGRESS BAR INDETERMINADA ──────────
    def _set_phase(self, phase):
        """Alterna entre barra de progresso determinada e indeterminada."""
        if phase in ("connecting", "merging"):
            # Modo indeterminado — animação de loading
            self.prog_bar.config(mode="indeterminate")
            self.prog_bar.start(15)
        elif phase == "downloading":
            # Modo determinado — mostra percentagem real
            self.prog_bar.stop()
            self.prog_bar.config(mode="determinate")
        else:
            # None — download acabou
            self.prog_bar.stop()
            self.prog_bar.config(mode="determinate")

    # ── THUMBNAIL PREVIEW ───────────────────
    def _on_url_change(self, *_):
        """Quando o URL muda, tentar obter thumbnail."""
        url = self.url_var.get().strip()
        self._thumbnail_job += 1
        current_job = self._thumbnail_job

        if not url or not url.startswith(("http://", "https://")):
            self._hide_thumbnail()
            return

        # Esconde a thumbnail antiga enquanto carrega a nova
        self._hide_thumbnail()

        if not YT_DLP_AVAILABLE:
            return

        # Lançar thread para obter info do vídeo
        thread = threading.Thread(
            target=self._fetch_video_info,
            args=(url, current_job),
            daemon=True
        )
        thread.start()

    def _fetch_video_info(self, url, job_id):
        """Obtém informações do vídeo numa thread separada."""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'socket_timeout': 8,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Verificar se este job ainda é relevante
            if job_id != self._thumbnail_job:
                return

            title = info.get("title", "Sem título")
            channel = info.get("uploader", info.get("channel", ""))
            duration = info.get("duration", 0)
            thumbnail_url = info.get("thumbnail", "")

            # Formatar duração
            if duration:
                mins, secs = divmod(int(duration), 60)
                hours, mins = divmod(mins, 60)
                if hours:
                    dur_str = f"{hours}:{mins:02d}:{secs:02d}"
                else:
                    dur_str = f"{mins}:{secs:02d}"
            else:
                dur_str = ""

            # Descarregar thumbnail se Pillow estiver disponível
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

            # Verificar novamente se o job ainda é relevante
            if job_id != self._thumbnail_job:
                return

            # Atualizar UI no main thread
            self.root.after(0, lambda: self._show_thumbnail(title, channel, dur_str, thumb_img))

        except Exception:
            # Falha silenciosa — não mostrar thumbnail
            if job_id == self._thumbnail_job:
                self.root.after(0, self._hide_thumbnail)

    def _show_thumbnail(self, title, channel, duration, thumb_img):
        """Mostra a secção de thumbnail com info do vídeo."""
        self.thumb_title_label.config(text=title)
        self.thumb_channel_label.config(text=channel)
        self.thumb_duration_label.config(text=f"⏱ {duration}" if duration else "")

        if thumb_img:
            self._thumbnail_image = thumb_img
            self.thumb_img_label.config(image=thumb_img)
        else:
            self.thumb_img_label.config(image="")

        self.thumb_frame.pack(fill="x", pady=(8, 0))

    def _hide_thumbnail(self):
        """Esconde a secção de thumbnail."""
        if hasattr(self, 'thumb_frame'):
            self.thumb_frame.pack_forget()
        self._thumbnail_image = None

    # ── HISTÓRICO ───────────────────────────
    def _on_history_select(self, event):
        """Quando um item do histórico é selecionado, preencher URL e formato."""
        idx = self.hist_menu.current()
        history = self.config.get("history")
        if 0 <= idx < len(history):
            item = history[idx]
            self.url_var.set(item["url"])
            # Restaurar formato se ainda existir
            if item.get("format") in FORMAT_OPTIONS:
                self.format_var.set(item["format"])
            self._log(f"Histórico: {item['url'][:50]}...", "info")
        # Limpar seleção
        self.root.after(50, lambda: self.hist_var.set(""))

    def _clear_history(self):
        """Limpa todo o histórico."""
        self.config.set("history", [])
        self.config.save()
        if self.hist_frame:
            self.hist_frame.pack_forget()
            self.hist_frame.destroy()
            self.hist_frame = None
        self._log("Histórico limpo.", "info")

    # ── ABRIR PASTA ─────────────────────────
    def _open_download_folder(self):
        """Abre a pasta de downloads no Explorador de Ficheiros."""
        path = self.download_path.get()
        if os.path.isdir(path):
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        else:
            messagebox.showwarning("Pasta não encontrada",
                                   f"A pasta não existe:\n{path}")

    # ── ATUALIZAR YT-DLP ────────────────────
    def _update_ytdlp(self):
        """Atualiza o yt-dlp para a versão mais recente."""
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
        """Executa a atualização do yt-dlp numa thread."""
        try:
            python_exe = sys.executable
            if getattr(sys, 'frozen', False):
                # Em modo .exe, não podemos usar pip
                self.root.after(0, lambda: self._log("⚠ Não é possível atualizar no modo .exe", "warn"))
                self.root.after(0, lambda: self._set_status("Atualização não disponível em .exe", C["warn"]))
                return

            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                [python_exe, "-m", "pip", "install", "-U", "yt-dlp"],
                capture_output=True, text=True, timeout=60,
                creationflags=creationflags
            )

            if result.returncode == 0:
                # Verificar se houve atualização
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

    # ── LÓGICA ──────────────────────────────

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
            
            # Hover button
            btn_rm = tk.Label(row_frame, text="✕", font=F_BOLD,
                              bg=C["surface"], fg=C["error"], cursor="hand2")
            
            # Hover effects
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
        """Verifica se a URL começa com http:// ou https://."""
        if not url.startswith(("http://", "https://")):
            messagebox.showwarning(
                "URL inválida",
                "Introduz um URL válido (deve começar com http:// ou https://)."
            )
            return False
        return True

    def _save_prefs(self, *_):
        """Guarda preferências sempre que download_path ou format mudam."""
        self.config.set("download_path", self.download_path.get())
        self.config.set("format", self.format_var.get())
        self.config.save()

    def _check_dependencies(self):
        if not YT_DLP_AVAILABLE:
            self._log("yt-dlp não encontrado. Instala com:  pip install yt-dlp", "err")
            self._set_status("⚠  Dependência em falta — ver log", C["error"])
        else:
            self._log(f"yt-dlp {yt_dlp.version.__version__} pronto.", "ok")

        if not self._is_ffmpeg_installed():
            self._log("⚠  FFmpeg NÃO ENCONTRADO! Audio/MP4 não vai juntar.", "warn")
        else:
            self._log("FFmpeg pronto.", "ok")

    def _is_ffmpeg_installed(self):
        """Verifica se o executável ffmpeg existe no sistema/PATH."""
        return shutil.which("ffmpeg") is not None

    def _start_download(self):
        # Se já está a descarregar, o botão funciona como CANCELAR
        if self.engine.is_downloading:
            self.engine.cancel()
            self.dl_btn.config(state="disabled", text="A cancelar...")
            self._set_status("A cancelar download...", C["warn"])
            return

        if not YT_DLP_AVAILABLE:
            messagebox.showerror("Dependência em falta",
                                 "Instala o yt-dlp primeiro:\n\npip install yt-dlp")
            return

        if not self._is_ffmpeg_installed():
            msg = (
                "O FFmpeg não foi encontrado no teu computador!\n\n"
                "Para criares MP4s num único ficheiro e converteres para MP3, o FFmpeg é OBRIGATÓRIO. "
                "Sem ele, os vídeos vão ficar com áudio e imagem separados (.webm e .m4a).\n\n"
                "Queres continuar mesmo assim?"
            )
            if not messagebox.askyesno("FFmpeg em falta", msg):
                return

        url = self.url_var.get().strip()
        if not url and not self.queue:
            messagebox.showwarning("URL vazia", "Introduz um URL ou adiciona itens à fila.")
            return

        # Validar URL do campo
        if url and not self._validate_url(url):
            return

        # Se há URL no campo, usar só esse; se fila, usar fila
        if url:
            jobs = [{"url": url, "format": self.format_var.get()}]
        else:
            jobs = self.queue.items()

        # Guardar no histórico
        for job in jobs:
            self.config.add_history(job["url"], job["format"])

        # Esconder botão "Abrir pasta"
        self.open_folder_btn.pack_forget()

        # Trocar botão para modo CANCELAR
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
            # Mostrar botão "Abrir pasta"
            self.open_folder_btn.pack(side="right")

            # Notificação sonora
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
        """Guardar configurações e fechar a aplicação."""
        self._save_prefs()
        self.root.destroy()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    # Interceta as chamadas recursivas do subprocesso quando compilado em .exe
    if len(sys.argv) > 1 and sys.argv[1] == "--run-yt-dlp":
        sys.argv.pop(1)  # Remove a flag para o yt-dlp não se queixar
        import yt_dlp
        sys.exit(yt_dlp.main())

    root = tk.Tk()

    # Ícone (ignora se não existir)
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base, "assets", "icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    app = PulsarUI(root)
    root.mainloop()