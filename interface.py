import base64
import queue
import threading
import tkinter as tk
from datetime import datetime
from io import BytesIO
from tkinter import messagebox, scrolledtext

import Pyro5.api
from PIL import Image, ImageTk, ImageOps

from events import ClientEvents

APP_BG = "#eef2f7"
PANEL_BG = "#ffffff"
SIDEBAR_BG = "#17212f"
SIDEBAR_CARD = "#223044"
TEXT_DARK = "#1f2937"
TEXT_MUTED = "#64748b"
ACCENT = "#2563eb"
SUCCESS = "#16a34a"
WARNING = "#f59e0b"
DANGER = "#dc2626"
PURPLE = "#7c3aed"
DISABLED_BG = "#cbd5e1"
DISABLED_FG = "#64748b"


class GameGUI:
    def __init__(self, root, player_name, server_uri="PYRO:GameServer@localhost:9090"):
        self.root = root
        self.player_name = player_name
        self.server = Pyro5.api.Proxy(server_uri)
        self.root.title(f"Adivinhação - Jogador: {player_name}")
        self.root.geometry("1480x820")
        self.root.minsize(1320, 720)
        self.root.configure(bg=APP_BG)
        self.msg_queue = queue.Queue()
        self._btn_colors = {}
        self.player_list = []

        self.current_phase = "LOBBY"
        self.hint_sent = False
        self.is_ready = False
        self.pending_trade_from = None
        self.continue_votes_cast = False

        self.client_daemon = Pyro5.api.Daemon()
        self.client_events = ClientEvents(self.msg_queue)
        self.callback_uri = self.client_daemon.register(self.client_events)
        self.daemon_thread = threading.Thread(
            target=self.client_daemon.requestLoop, daemon=True
        )
        self.daemon_thread.start()

        self.setup_ui()

        try:
            success, msg = self.server.register_client(
                self.player_name, self.callback_uri
            )
            if not success:
                messagebox.showerror("Erro de Conexão", msg)
                self.root.destroy()
                return
            self.log_message(f"Conectado ao servidor: {msg}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível conectar ao Servidor: {e}")
            self.root.destroy()
            return

        self.root.after(100, self.process_queue)

    def setup_ui(self):
        self.frame_left = tk.Frame(self.root, width=620, bg=SIDEBAR_BG)
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y)
        self.frame_left.pack_propagate(False)

        tk.Label(
            self.frame_left,
            text="Seu Objeto Secreto",
            fg="#f8fafc",
            bg=SIDEBAR_BG,
            font=("Arial", 14, "bold"),
        ).pack(pady=(18, 10))

        self.lbl_image = tk.Label(
            self.frame_left,
            text="Aguardando\ninício do jogo...",
            bg=SIDEBAR_CARD,
            fg="#cbd5e1",
            width=68,
            height=18,
            relief=tk.FLAT,
            font=("Arial", 10, "bold"),
        )
        self.lbl_image.pack(padx=18, pady=4)

        tk.Label(
            self.frame_left,
            text="Placar",
            fg="#f8fafc",
            bg=SIDEBAR_BG,
            font=("Arial", 12, "bold"),
        ).pack(pady=(18, 6))
        self.txt_scores = tk.Text(
            self.frame_left,
            state="disabled",
            height=8,
            bg=SIDEBAR_CARD,
            fg="#f8fafc",
            relief=tk.FLAT,
            font=("Courier", 10),
            padx=8,
            pady=8,
            insertbackground="#f8fafc",
        )
        self.txt_scores.pack(fill=tk.X, padx=18, pady=(0, 5))

        tk.Label(
            self.frame_left,
            text="Dicas Descobertas",
            fg="#f8fafc",
            bg=SIDEBAR_BG,
            font=("Arial", 12, "bold"),
        ).pack(pady=(16, 6))
        self.txt_hints_history = tk.Text(
            self.frame_left,
            state="disabled",
            height=8,
            bg=SIDEBAR_CARD,
            fg="#bbf7d0",
            relief=tk.FLAT,
            font=("Courier", 10),
            padx=8,
            pady=8,
            insertbackground="#f8fafc",
        )
        self.txt_hints_history.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 14))

        self.frame_mid = tk.Frame(self.root, width=380, bg=PANEL_BG)
        self.frame_mid.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0), pady=12)
        self.frame_mid.pack_propagate(False)

        self.btn_iniciar = tk.Button(
            self.frame_mid,
            text="Iniciar Partida",
            command=self.cmd_iniciar,
            bg=SUCCESS,
            fg="#ffffff",
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            activebackground="#15803d",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_iniciar.pack(fill=tk.X, padx=12, pady=(14, 10), ipady=5)

        tk.Label(
            self.frame_mid,
            text="Dica Pública",
            bg=PANEL_BG,
            fg=TEXT_DARK,
            font=("Arial", 9, "bold"),
        ).pack(anchor=tk.W, padx=12, pady=(10, 3))
        self.entry_dica = tk.Entry(self.frame_mid, relief=tk.FLAT, bg="#f8fafc")
        self.entry_dica.pack(fill=tk.X, padx=12, ipady=6)
        self.btn_dica = tk.Button(
            self.frame_mid,
            text="Enviar Dica",
            command=self.cmd_dica,
            bg=ACCENT,
            fg="#ffffff",
            relief=tk.FLAT,
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_dica.pack(fill=tk.X, padx=12, pady=(4, 8), ipady=4)

        tk.Label(
            self.frame_mid,
            text="Adivinhar",
            bg=PANEL_BG,
            fg=TEXT_DARK,
            font=("Arial", 10, "bold"),
        ).pack(anchor=tk.W, padx=12, pady=(10, 3))
        tk.Label(
            self.frame_mid,
            text="Jogador alvo",
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Arial", 9),
        ).pack(anchor=tk.W, padx=12)
        self.val_alvo = tk.StringVar(self.root)
        self.opt_alvo = tk.OptionMenu(self.frame_mid, self.val_alvo, "")
        self.opt_alvo.config(bg="#f8fafc", fg=TEXT_DARK, relief=tk.FLAT, highlightthickness=0)
        self.opt_alvo.pack(fill=tk.X, padx=12, pady=(2, 5))

        tk.Label(
            self.frame_mid,
            text="Palpite",
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Arial", 9),
        ).pack(anchor=tk.W, padx=12)
        self.entry_palpite = tk.Entry(self.frame_mid, relief=tk.FLAT, bg="#f8fafc")
        self.entry_palpite.pack(fill=tk.X, padx=12, ipady=6)
        self.btn_adivinhar = tk.Button(
            self.frame_mid,
            text="Enviar Palpite",
            command=self.cmd_adivinhar,
            bg=ACCENT,
            fg="#ffffff",
            relief=tk.FLAT,
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_adivinhar.pack(fill=tk.X, padx=12, pady=(4, 8), ipady=4)

        tk.Label(
            self.frame_mid,
            text="Troca Privada",
            bg=PANEL_BG,
            fg=TEXT_DARK,
            font=("Arial", 10, "bold"),
        ).pack(anchor=tk.W, padx=12, pady=(10, 3))
        self.val_trade_alvo = tk.StringVar(self.root)
        self.opt_trade_alvo = tk.OptionMenu(self.frame_mid, self.val_trade_alvo, "")
        self.opt_trade_alvo.config(bg="#f8fafc", fg=TEXT_DARK, relief=tk.FLAT, highlightthickness=0)
        self.opt_trade_alvo.pack(fill=tk.X, padx=12, pady=(2, 5))

        self.entry_trade_dica = tk.Entry(self.frame_mid, relief=tk.FLAT, bg="#f8fafc")
        self.entry_trade_dica.pack(fill=tk.X, padx=12, ipady=6)
        self.entry_trade_dica.insert(0, "")
        self.btn_trade_solicitar = tk.Button(
            self.frame_mid,
            text="Solicitar Troca",
            command=self.cmd_trade_solicitar,
            bg=PURPLE,
            fg="#ffffff",
            relief=tk.FLAT,
            activebackground="#6d28d9",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_trade_solicitar.pack(fill=tk.X, padx=12, pady=(4, 8), ipady=4)

        self.frame_trade_resp = tk.Frame(
            self.frame_mid, relief=tk.FLAT, bd=0, bg="#fff7ed"
        )
        self.lbl_trade_resp = tk.Label(
            self.frame_trade_resp,
            text="",
            wraplength=356,
            bg="#fff7ed",
            fg="#9a3412",
            font=("Arial", 9, "bold"),
        )
        self.lbl_trade_resp.pack(anchor=tk.W, padx=8, pady=(8, 2))
        tk.Label(
            self.frame_trade_resp,
            text="Sua dica em troca",
            bg="#fff7ed",
            fg="#9a3412",
            font=("Arial", 9),
        ).pack(
            anchor=tk.W, padx=8
        )
        self.entry_trade_resp_dica = tk.Entry(self.frame_trade_resp, relief=tk.FLAT, bg="#fffbeb")
        self.entry_trade_resp_dica.pack(fill=tk.X, padx=8, pady=(2, 4), ipady=5)
        self.btn_aceitar = tk.Button(
            self.frame_trade_resp,
            text="Aceitar Troca",
            command=self.cmd_aceitar_troca,
            bg=SUCCESS,
            fg="white",
            relief=tk.FLAT,
            activebackground="#15803d",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_aceitar.pack(fill=tk.X, padx=8, pady=2, ipady=3)
        self.btn_recusar = tk.Button(
            self.frame_trade_resp,
            text="Recusar Troca",
            command=self.cmd_recusar_troca,
            bg=DANGER,
            fg="white",
            relief=tk.FLAT,
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_recusar.pack(fill=tk.X, padx=8, pady=(2, 8), ipady=3)

        self.btn_pronto = tk.Button(
            self.frame_mid,
            text="Pronto",
            command=self.cmd_pronto,
            bg=WARNING,
            fg="white",
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            activebackground="#d97706",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_pronto.pack(fill=tk.X, padx=12, pady=(12, 4), ipady=5)

        self.btn_continuar = tk.Button(
            self.frame_mid,
            text="Continuar Jogo",
            command=self.cmd_continuar,
            bg=ACCENT,
            fg="white",
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_continuar.pack(fill=tk.X, padx=12, pady=3, ipady=4)
        self.btn_encerrar_jogo = tk.Button(
            self.frame_mid,
            text="Encerrar Jogo",
            command=self.cmd_encerrar_jogo,
            bg=PURPLE,
            fg="white",
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            activebackground="#6d28d9",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_encerrar_jogo.pack(fill=tk.X, padx=12, pady=3, ipady=4)

        self.btn_votar = tk.Button(
            self.frame_mid,
            text="Votar para Reiniciar",
            command=self.cmd_votar,
            bg=ACCENT,
            fg="#ffffff",
            relief=tk.FLAT,
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_votar.pack(fill=tk.X, padx=12, pady=(4, 12), ipady=4)

        for btn in [
            self.btn_iniciar,
            self.btn_dica,
            self.btn_adivinhar,
            self.btn_trade_solicitar,
            self.btn_pronto,
            self.btn_continuar,
            self.btn_encerrar_jogo,
            self.btn_votar,
            self.btn_aceitar,
            self.btn_recusar,
        ]:
            self._btn_colors[btn] = btn.cget("bg")

        self.update_ui_state()

        self.frame_right = tk.Frame(self.root, bg=APP_BG)
        self.frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.frame_manual = tk.Frame(
            self.frame_right, bg=PANEL_BG, relief=tk.FLAT, bd=0
        )
        self.frame_manual.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            self.frame_manual,
            text="MANUAL RÁPIDO",
            font=("Arial", 10, "bold"),
            fg=TEXT_DARK,
            bg=PANEL_BG,
        ).pack(anchor=tk.W, padx=12, pady=(10, 0))
        self.txt_manual = tk.Text(
            self.frame_manual,
            height=4,
            font=("Arial", 9),
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            relief=tk.FLAT,
            padx=10,
            pady=6,
        )
        self.txt_manual.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._fill_manual_text()

        self.frame_activity = tk.Frame(self.frame_right, bg=APP_BG)
        self.frame_activity.pack(fill=tk.BOTH, expand=True)
        self.frame_activity.columnconfigure(0, weight=4, uniform="activity")
        self.frame_activity.columnconfigure(1, weight=3, uniform="activity")
        self.frame_activity.rowconfigure(1, weight=1)

        tk.Label(
            self.frame_activity,
            text="Histórico de Jogo",
            font=("Arial", 12, "bold"),
            bg=APP_BG,
            fg=TEXT_DARK,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.txt_log = scrolledtext.ScrolledText(
            self.frame_activity,
            state="disabled",
            wrap=tk.WORD,
            bg=PANEL_BG,
            fg=TEXT_DARK,
            height=9,
            relief=tk.FLAT,
            padx=10,
            pady=8,
            font=("Arial", 10),
        )
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=(0, 12))

        tk.Label(
            self.frame_activity,
            text="Chat Global",
            font=("Arial", 12, "bold"),
            bg=APP_BG,
            fg=TEXT_DARK,
        ).grid(row=0, column=1, sticky="w", pady=(0, 4))

        self.frame_chat_panel = tk.Frame(self.frame_activity, bg=APP_BG)
        self.frame_chat_panel.grid(row=1, column=1, sticky="nsew")
        self.frame_chat_panel.rowconfigure(0, weight=1)
        self.frame_chat_panel.columnconfigure(0, weight=1)

        self.txt_chat = scrolledtext.ScrolledText(
            self.frame_chat_panel,
            state="disabled",
            wrap=tk.WORD,
            bg=PANEL_BG,
            fg=TEXT_DARK,
            height=8,
            relief=tk.FLAT,
            padx=10,
            pady=8,
            font=("Arial", 10),
        )
        self.txt_chat.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        self.frame_chat = tk.Frame(self.frame_chat_panel, bg=APP_BG)
        self.frame_chat.grid(row=1, column=0, sticky="ew")
        self.frame_chat.columnconfigure(0, weight=1)
        self.entry_chat = tk.Entry(self.frame_chat, relief=tk.FLAT, bg=PANEL_BG, fg=TEXT_DARK)
        self.entry_chat.grid(row=0, column=0, sticky="ew", ipady=8)
        self.entry_chat.bind("<Return>", lambda e: self.cmd_chat())
        tk.Button(
            self.frame_chat,
            text="Enviar Chat",
            command=self.cmd_chat,
            width=15,
            bg=ACCENT,
            fg="#ffffff",
            relief=tk.FLAT,
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            cursor="hand2",
        ).grid(row=0, column=1, sticky="e", padx=(8, 0), ipady=6)

        self._configure_text_tags()

    def _fill_manual_text(self):
        manual = (
            "Fluxo: envie sua dica pública, faça uma ação ou marque pronto.\n"
            "Dicas e trocas aceitam uma única palavra. Palpites são julgados pelo dono do objeto.\n"
            "Trocas privadas geram alerta de espionagem para terceiros. O chat global é somente conversa."
        )
        self.txt_manual.config(state="normal")
        self.txt_manual.insert(tk.END, manual)
        self.txt_manual.config(state="disabled")

    def _configure_text_tags(self):
        self.txt_log.tag_config("system", foreground=ACCENT, spacing1=3, spacing3=3)
        self.txt_log.tag_config("success", foreground=SUCCESS, spacing1=3, spacing3=3)
        self.txt_log.tag_config("warning", foreground=WARNING, spacing1=3, spacing3=3)
        self.txt_log.tag_config("danger", foreground=DANGER, spacing1=3, spacing3=3)
        self.txt_log.tag_config("guess", foreground="#0f766e", spacing1=3, spacing3=3)
        self.txt_log.tag_config("trade", foreground=PURPLE, spacing1=3, spacing3=3)
        self.txt_log.tag_config("muted", foreground=TEXT_MUTED, spacing1=3, spacing3=3)
        self.txt_chat.tag_config("sender", foreground=ACCENT, font=("Arial", 10, "bold"))
        self.txt_chat.tag_config("time", foreground=TEXT_MUTED)
        self.txt_hints_history.tag_config("hint", foreground="#bbf7d0")
        self.txt_hints_history.tag_config("private", foreground="#fde68a")
        self.txt_hints_history.tag_config("spy", foreground="#93c5fd")

    def _set_state(self, widgets, enabled):
        state = "normal" if enabled else "disabled"
        for w in widgets:
            w.config(state=state)
            if isinstance(w, tk.Button) and w in self._btn_colors:
                if enabled:
                    w.config(bg=self._btn_colors[w], fg="#ffffff", cursor="hand2")
                else:
                    w.config(bg=DISABLED_BG, fg=DISABLED_FG, cursor="")

    def log_message(self, msg, tag="muted"):
        self.txt_log.config(state="normal")
        self.txt_log.insert(tk.END, msg + "\n", tag)
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    def log_chat(self, sender, msg):
        now = datetime.now().strftime("%H:%M")
        self.txt_chat.config(state="normal")
        self.txt_chat.insert(tk.END, f"{now}  ", "time")
        self.txt_chat.insert(tk.END, f"{sender}: ", "sender")
        self.txt_chat.insert(tk.END, f"{msg}\n")
        self.txt_chat.see(tk.END)
        self.txt_chat.config(state="disabled")

    def log_hint(self, hint_msg, tag="hint"):
        self.txt_hints_history.config(state="normal")
        self.txt_hints_history.insert(tk.END, hint_msg + "\n", tag)
        self.txt_hints_history.see(tk.END)
        self.txt_hints_history.config(state="disabled")

    def _update_option_menus(self):
        menu_configs = [
            (self.opt_alvo, self.val_alvo),
            (self.opt_trade_alvo, self.val_trade_alvo),
        ]

        others = [p for p in self.player_list if p != self.player_name]

        for opt_menu, val_var in menu_configs:
            menu = opt_menu["menu"]
            menu.delete(0, "end")

            choices = others

            for choice in choices:
                menu.add_command(
                    label=choice, command=lambda c=choice, v=val_var: v.set(c)
                )

            if choices:
                if val_var.get() not in choices:
                    val_var.set(choices[0])
            else:
                val_var.set("")

    def update_scoreboard(self, scores_data):
        self.txt_scores.config(state="normal")
        self.txt_scores.delete("1.0", tk.END)

        current_players = list(scores_data.keys())
        if sorted(current_players) != sorted(self.player_list):
            self.player_list = current_players
            self._update_option_menus()

        for name, info in sorted(
            scores_data.items(), key=lambda x: x[1]["score"], reverse=True
        ):
            status_parts = []
            if info.get("is_ready"):
                status_parts.append("PRONTO")
            correct_guesses = info.get("correct_guesses_made", 0)
            object_guessed_by = info.get(
                "object_guessed_by", info.get("guesses_made", 0)
            )
            if correct_guesses > 0:
                status_parts.append(f"acertou {correct_guesses}")
            if object_guessed_by > 0:
                status_parts.append(f"objeto acertado por {object_guessed_by}")

            status = f" [{' | '.join(status_parts)}]" if status_parts else ""
            self.txt_scores.insert(tk.END, f"{name}: {info['score']} pts{status}\n")
        self.txt_scores.config(state="disabled")

    def update_ui_state(self):
        phase = self.current_phase
        all_widgets = [
            self.btn_iniciar,
            self.entry_dica,
            self.btn_dica,
            self.opt_alvo,
            self.entry_palpite,
            self.btn_adivinhar,
            self.opt_trade_alvo,
            self.entry_trade_dica,
            self.btn_trade_solicitar,
            self.btn_pronto,
            self.btn_continuar,
            self.btn_encerrar_jogo,
            self.btn_votar,
        ]
        self._set_state(all_widgets, False)
        self.frame_trade_resp.pack_forget()

        if phase == "LOBBY":
            self._set_state([self.btn_iniciar], True)
        elif phase == "WAITING_HINTS":
            if not self.hint_sent:
                self._set_state([self.entry_dica, self.btn_dica], True)
        elif phase == "ACTION_PHASE":
            if not self.is_ready:
                self._set_state(
                    [
                        self.opt_alvo,
                        self.entry_palpite,
                        self.btn_adivinhar,
                        self.opt_trade_alvo,
                        self.entry_trade_dica,
                        self.btn_trade_solicitar,
                        self.btn_pronto,
                    ],
                    True,
                )
                if self.pending_trade_from:
                    self.frame_trade_resp.pack(fill=tk.X, pady=5)
        elif phase == "VOTE_CONTINUE":
            if not self.continue_votes_cast:
                self._set_state([self.btn_continuar, self.btn_encerrar_jogo], True)
        elif phase == "END_GAME":
            self._set_state([self.btn_votar], True)

    def _phase_label(self, phase):
        labels = {
            "LOBBY": "Lobby",
            "WAITING_HINTS": "Dicas públicas",
            "ACTION_PHASE": "Fase de ações",
            "VOTE_CONTINUE": "Votação",
            "END_GAME": "Fim de jogo",
        }
        return labels.get(phase, phase)

    def process_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                event = msg[0]
                if event == "chat":
                    self.log_chat(msg[1], msg[2])
                elif event == "notice":
                    self.log_message(msg[2], msg[1])
                elif event == "hint":
                    tag = msg[2] if len(msg) > 2 else "hint"
                    self.log_hint(msg[1], tag)
                elif event == "log":
                    if any(
                        x in msg[1]
                        for x in ["[DICA PÚBLICA]", "[TROCA CONCLUÍDA]", "[ESPIONAGEM]"]
                    ):
                        self.log_hint(msg[1])
                    else:
                        self.log_message(msg[1], "muted")
                elif event == "phase":
                    new_phase, message = msg[1], msg[2]
                    self.log_message(f"{self._phase_label(new_phase)} | {message}", "system")
                    self.current_phase = new_phase
                    if new_phase in ("WAITING_HINTS", "LOBBY"):
                        self.hint_sent = False
                        self.is_ready = False
                        self.pending_trade_from = None
                    elif new_phase == "VOTE_CONTINUE":
                        self.continue_votes_cast = False
                    self.update_ui_state()
                elif event == "image":
                    self.display_image(msg[1])
                elif event == "judgment":
                    self.ask_judgment(msg[1], msg[2])
                elif event == "trade_request":
                    sender = msg[1]
                    self.pending_trade_from = sender
                    self.lbl_trade_resp.config(
                        text=f"{sender} quer trocar dicas com você!"
                    )
                    self.frame_trade_resp.pack(fill=tk.X, pady=5)
                    self.log_message(
                        f"{sender} enviou um pedido de troca. Responda no painel de ações.",
                        "trade",
                    )
                elif event == "trade_notification":
                    p_a, p_b = msg[1], msg[2]
                    self.ask_spy(p_a, p_b)
                elif event == "scores":
                    self.update_scoreboard(msg[1])
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def display_image(self, b64):
        try:
            img_data = base64.b64decode(b64)
            image = Image.open(BytesIO(img_data))
            resample_filter = getattr(
                Image, "LANCZOS", getattr(Image, "ANTIALIAS", None)
            )
            if hasattr(Image, "Resampling"):
                resample_filter = Image.Resampling.LANCZOS
            image = ImageOps.contain(image, (560, 320), resample_filter)
            photo = ImageTk.PhotoImage(image)
            self.lbl_image.config(
                image=photo, text="", bg="black", width=560, height=320
            )
            self.lbl_image.image = photo
            self.log_message("Imagem do objeto carregada.", "success")
        except Exception as e:
            self.log_message(f"Falha ao carregar imagem: {e}", "danger")

    def ask_judgment(self, guesser, guess_word):
        resposta = messagebox.askyesno(
            "Julgamento Necessário!",
            f"O jogador {guesser} tentou adivinhar que o seu objeto é '{guess_word}'.\n\nEsse palpite está CORRETO?",
        )
        try:
            ok, msg = self.server.judge_guess(self.player_name, guesser, resposta)
            if ok:
                self.log_message(
                    f"Julgamento enviado: palpite de {guesser} marcado como {'correto' if resposta else 'errado'}.",
                    "guess",
                )
            else:
                self.log_message(f"Falha ao registrar julgamento: {msg}", "warning")
        except Exception as e:
            self.log_message(f"Falha ao enviar julgamento: {e}", "danger")

    def send_action(self, action_func, *args):
        try:
            res = action_func(*args)
            if isinstance(res, tuple) and len(res) == 2:
                ok, msg = res
            else:
                ok, msg = True, res
            if msg:
                self.log_message(msg, "success" if ok else "warning")
            return ok
        except Exception as e:
            self.log_message(f"Erro de rede: {e}", "danger")
            return False

    def cmd_iniciar(self):
        self.send_action(self.server.start_game, self.player_name)

    def cmd_dica(self):
        dica = self.entry_dica.get().strip()
        if not dica:
            return
        if len(dica.split()) != 1:
            self.log_message("A dica deve ser uma única palavra.", "warning")
            return
        ok = self.send_action(self.server.send_public_hint, self.player_name, dica)
        if ok:
            self.entry_dica.delete(0, tk.END)
            self.hint_sent = True
            self.update_ui_state()

    def cmd_adivinhar(self):
        alvo = self.val_alvo.get().strip()
        palpite = self.entry_palpite.get().strip()
        if alvo and palpite:
            self.send_action(self.server.guess_object, self.player_name, alvo, palpite)
            self.entry_palpite.delete(0, tk.END)

    def ask_spy(self, p_a, p_b):
        if self.player_name in (p_a, p_b):
            return

        resp = messagebox.askyesno(
            "Alerta de Troca!",
            f"Os jogadores {p_a} e {p_b} acabaram de realizar uma troca!\n\nDeseja gastar sua ação do turno para ESPIAR esta troca?",
        )
        if resp:
            self.send_action(self.server.spy_on_trade, self.player_name, p_a, p_b)

    def cmd_trade_solicitar(self):
        alvo = self.val_trade_alvo.get().strip()
        dica = self.entry_trade_dica.get().strip()
        if not alvo or not dica:
            self.log_message("Informe o jogador alvo e a dica.", "warning")
            return
        if len(dica.split()) != 1:
            self.log_message("A dica deve ser uma única palavra.", "warning")
            return
        ok = self.send_action(self.server.request_trade, self.player_name, alvo, dica)
        if ok:
            self.entry_trade_dica.delete(0, tk.END)

    def cmd_aceitar_troca(self):
        dica = self.entry_trade_resp_dica.get().strip()
        if not dica:
            self.log_message("Informe sua dica para aceitar a troca.", "warning")
            return
        if len(dica.split()) != 1:
            self.log_message("A dica deve ser uma única palavra.", "warning")
            return
        if not self.pending_trade_from:
            self.log_message("Nenhum pedido de troca pendente.", "warning")
            return
        ok = self.send_action(
            self.server.respond_trade,
            self.player_name,
            self.pending_trade_from,
            True,
            dica,
        )
        if ok:
            self.entry_trade_resp_dica.delete(0, tk.END)
            self.pending_trade_from = None
            self.frame_trade_resp.pack_forget()

    def cmd_recusar_troca(self):
        if not self.pending_trade_from:
            self.log_message("Nenhum pedido de troca pendente.", "warning")
            return
        ok = self.send_action(
            self.server.respond_trade, self.player_name, self.pending_trade_from, False
        )
        if ok:
            self.pending_trade_from = None
            self.frame_trade_resp.pack_forget()

    def cmd_continuar(self):
        ok = self.send_action(self.server.vote_continue, self.player_name, True)
        if ok:
            self.continue_votes_cast = True
            self.update_ui_state()

    def cmd_encerrar_jogo(self):
        ok = self.send_action(self.server.vote_continue, self.player_name, False)
        if ok:
            self.continue_votes_cast = True
            self.update_ui_state()

    def cmd_pronto(self):
        ok = self.send_action(self.server.player_ready, self.player_name)
        if ok:
            self.is_ready = True
            self.update_ui_state()

    def cmd_votar(self):
        self.send_action(self.server.vote_restart, self.player_name)

    def cmd_chat(self):
        texto = self.entry_chat.get().strip()
        if not texto:
            return
        self.entry_chat.delete(0, tk.END)
        self.send_action(self.server.send_chat_message, self.player_name, texto)
