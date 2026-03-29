"""
╔══════════════════════════════════════╗
║        SLAYER  DOWNLOADER          ║
║   YouTube · MP3 · MP4 · Expansível   ║
╚══════════════════════════════════════╝

Dependências (instalar uma vez):
    pip install yt-dlp

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


# ─────────────────────────────────────────────
#  CONFIG MANAGER — Persistência de preferências
# ─────────────────────────────────────────────
class ConfigManager:
    """Lê e guarda preferências do utilizador num ficheiro JSON."""

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

    def __init__(self, on_progress, on_log, on_status, on_done):
        self._on_progress = on_progress
        self._on_log = on_log
        self._on_status = on_status
        self._on_done = on_done
        self.cancel_requested = False
        self.is_downloading = False
        self._process = None  # referenciar o subprocesso atual
        self._last_progress_update = 0  # throttle de updates de progresso

    def start(self, jobs, dest):
        """Lança os downloads numa thread daemon."""
        self.cancel_requested = False
        self.is_downloading = True
        thread = threading.Thread(
            target=self._run_jobs, args=(jobs, dest), daemon=True
        )
        thread.start()

    def cancel(self):
        """Cancela imediatamente o subprocesso de download."""
        self.cancel_requested = True
        if self._process:
            try:
                # No Windows, kill funciona enviando CTRL+C se usarmos creationflags ou forçando término
                self._process.kill()
            except Exception:
                pass

    def _run_jobs(self, jobs, dest):
        total = len(jobs)
        for idx, job in enumerate(jobs, 1):
            if self.cancel_requested:
                self._on_log("⊘  Download cancelado pelo utilizador.", "warn")
                break
            self._on_status(f"[{idx}/{total}] A preparar...", C["text_dim"])
            self._download_subprocess(job["url"], job["format"], dest, idx, total)

        self.is_downloading = False
        self._on_done(cancelled=self.cancel_requested)

    def _download_subprocess(self, url, fmt_label, dest, idx, total):
        if self.cancel_requested:
            return

        fmt = FORMAT_OPTIONS[fmt_label]
        os.makedirs(dest, exist_ok=True)

        self._on_status(f"[{idx}/{total}] A ligar...", C["text_dim"])

        # Identificar o executável de forma segura para PyInstaller (Evita loop infinito)
        python_exe = sys.executable
        if getattr(sys, 'frozen', False):
            # Se for um .exe gerado pelo PyInstaller, chamamos o próprio .exe com uma flag secreta
            cmd = [python_exe, "--run-yt-dlp", "--no-warnings", "--socket-timeout", "15", "--newline"]
        else:
            # Se for script Python normal
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
                "--remux-video", fmt["ext"] # Garante que o ficheiro final é mesmo do formato pedido
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

            # Lendo a saída do subprocesso linha a linha (bloqueia até ao processo terminar)
            for line in iter(self._process.stdout.readline, ''):
                if self.cancel_requested:
                    self._process.kill()
                    break

                line = line.strip()
                self._parse_output(line)
                
            self._process.stdout.close()
            return_code = self._process.wait()

            if self.cancel_requested:
                return

            if return_code == 0:
                self._on_log(f"✓  Concluído: {url[:50]}...", "ok")
                self._on_status("A processar ficheiro...", C["warn"])
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

    def _parse_output(self, line):
        """Analisa a saída padrão do yt-dlp para extrair a percentagem e a velocidade."""
        # Exemplo de linha de download: [download]  15.3% of 50.00MiB at 3.00MiB/s ETA 00:15
        if line.startswith("[download]") and "%" in line:
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
                        
                        # Atualizar o status text
                        self._on_status(f"  {pct:.1f}%  •  {speed}  •  ETA {eta}", C["text_dim"])
                except ValueError:
                    pass
        elif "[Merger]" in line or "Merging formats into" in line:
             self._on_status("A juntar vídeo e áudio...", C["warn"])
             self._on_log("A juntar ficheiros com ffmpeg...", "info")
        elif "[ExtractAudio]" in line or "Destination:" in line and "audio" in line.lower():
             self._on_status("Processando media (FFmpeg)...", C["warn"])
        elif line.startswith("[youtube]") or line.startswith("[info]"):
             # Extrair titulo
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
        self.root.geometry("760x620")
        self.root.minsize(680, 560)
        self.root.configure(bg=C["bg"])

        # Managers
        self.config = ConfigManager()
        self.queue = QueueManager()
        self.engine = DownloadEngine(
            on_progress=self._safe_progress,
            on_log=self._safe_log,
            on_status=self._safe_status,
            on_done=self._safe_done,
        )

        # Estado da UI
        self.download_path = tk.StringVar(value=self.config.get("download_path"))
        self.url_var        = tk.StringVar()
        self.format_var     = tk.StringVar(value=self.config.get("format"))
        self.status_var     = tk.StringVar(value="Pronto para descarregar.")
        self.progress_var   = tk.DoubleVar(value=0)
        self.detected_platform = tk.StringVar(value="")

        # URL muda → detectar plataforma
        self.url_var.trace_add("write", self._detect_platform)

        # Guardar preferências ao mudar
        self.download_path.trace_add("write", self._save_prefs)
        self.format_var.trace_add("write", self._save_prefs)

        self._build_ui()
        self._check_dependencies()

        # Guardar preferências ao fechar
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── THREAD-SAFE CALLBACKS ────────────────
    # Estas funções são chamadas a partir da thread de download.
    # Usam root.after(0, ...) para delegar ao main thread do Tkinter.

    def _safe_progress(self, pct):
        self.root.after(0, lambda p=pct: self.progress_var.set(p))

    def _safe_log(self, msg, tag="info"):
        self.root.after(0, lambda m=msg, t=tag: self._log(m, t))

    def _safe_status(self, msg, color=None):
        self.root.after(0, lambda m=msg, c=color: self._set_status(m, c))

    def _safe_done(self, cancelled=False):
        self.root.after(0, lambda c=cancelled: self._on_all_done(c))

    # ── UI ──────────────────────────────────
    def _build_ui(self):
        self._style_ttk()

        # Título
        header = tk.Frame(self.root, bg=C["bg"], pady=16)
        header.pack(fill="x", padx=28)

        tk.Label(header, text="SLAYER", font=F_TITLE,
                 fg=C["accent"], bg=C["bg"]).pack(side="left")
        tk.Label(header, text="DOWNLOADER", font=("Calibri", 22),
                 fg=C["text_dim"], bg=C["bg"]).pack(side="left", padx=(6, 0))
        tk.Label(header, text="v1.1", font=F_SMALL,
                 fg=C["text_muted"], bg=C["bg"]).pack(side="left", padx=(10, 0), pady=(8, 0))

        # Separador
        self._sep()

        # Painel principal
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

        # — Formato —
        self._label(main, "Formato")
        fmt_row = tk.Frame(main, bg=C["bg"])
        fmt_row.pack(fill="x", pady=(4, 0))

        self.fmt_menu = ttk.Combobox(fmt_row, textvariable=self.format_var,
                                     values=list(FORMAT_OPTIONS.keys()),
                                     state="readonly", style="Pulsar.TCombobox",
                                     font=F_MAIN, takefocus=0)
        self.fmt_menu.pack(side="left", fill="x", expand=True)

        # Remover foco visual depois de selecionar (elimina a linha sublinhada)
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
        self.queue_list = tk.Listbox(self.queue_frame,
                                     font=F_MONO,
                                     bg=C["surface"], fg=C["text_dim"],
                                     selectbackground=C["accent"],
                                     selectforeground=C["text"],
                                     relief="flat", bd=0, height=4,
                                     activestyle="none")
        self.queue_list.pack(fill="x", padx=4, pady=4)

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

        # — Status —
        self.status_label = tk.Label(prog_frame, textvariable=self.status_var,
                                     font=F_BOLD,
                                     fg=C["text_dim"], bg=C["bg"],
                                     anchor="w")
        self.status_label.pack(fill="x", pady=(4, 0))

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
        self.log_container.pack(fill="x", side="bottom")

        # Cabeçalho do log (sempre visível)
        log_header = tk.Frame(self.log_container, bg=C["bg"], padx=28)
        log_header.pack(fill="x")
        
        self.log_toggle_btn = tk.Label(log_header, text="▼ Ocultar log" if self.show_log_var.get() else "▶ Mostrar log",
                                       font=F_SMALL,
                                       fg=C["text_muted"], bg=C["bg"], cursor="hand2")
        self.log_toggle_btn.pack(side="left", pady=(4, 4))
        self.log_toggle_btn.bind("<Button-1>", self._toggle_log)

        # Frame principal do log
        self.log_frame = tk.Frame(self.log_container, bg=C["surface"], height=80, padx=28, pady=8)
        self.log_frame.pack_propagate(False)

        self.log_text = tk.Text(self.log_frame, font=F_MONO,
                                bg=C["surface"], fg=C["text_dim"],
                                relief="flat", bd=0, state="disabled",
                                height=3, wrap="word")
        self.log_text.pack(fill="x")
        self.log_text.tag_config("ok",    foreground=C["success"])
        self.log_text.tag_config("err",   foreground=C["error"])
        self.log_text.tag_config("info",  foreground=C["text_dim"])
        self.log_text.tag_config("warn",  foreground=C["warn"])

        # Aplicar estado inicial do log
        if self.show_log_var.get():
            self.log_frame.pack(fill="x", pady=(0, 12))

    def _style_ttk(self):
        s = ttk.Style()
        s.theme_use("clam")

        # Remover o indicador de foco (sublinhado/pontilhado) do Combobox
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
            self.log_frame.pack(fill="x", pady=(0, 12))
        else:
            self.log_toggle_btn.config(text="▶ Mostrar log")
            self.log_frame.pack_forget()
            
        # Gravar a preferência no config
        self.config.set("show_log", self.show_log_var.get())
        self.config.save()

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
        display = url[:70] + "..." if len(url) > 70 else url
        self.queue_list.insert("end", f"  {len(self.queue)}.  {display}")
        self.url_var.set("")
        self.queue_label.config(text=f"Fila  ({len(self.queue)} itens)")
        display_log = url[:60] + "..." if len(url) > 60 else url
        self._log(f"Adicionado à fila: {display_log}", "info")

    def _clear_queue(self):
        self.queue.clear()
        self.queue_list.delete(0, "end")
        self.queue_label.config(text="Fila  (0 itens)")

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