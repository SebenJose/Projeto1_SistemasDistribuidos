import base64
import queue
import threading
import tkinter as tk
from io import BytesIO
from tkinter import messagebox, scrolledtext

import Pyro5.api
from PIL import Image, ImageTk

from events import ClientEvents

DISABLED_BG = "#9e9e9e"


class GameGUI:
    def __init__(self, root, player_name, server_uri="PYRO:GameServer@localhost:9090"):
        self.root = root
        self.player_name = player_name
        self.server = Pyro5.api.Proxy(server_uri)
        self.root.title(f"Adivinhação - Jogador: {player_name}")
        self.root.geometry("950x700")
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
        self.frame_left = tk.Frame(self.root, width=300, bg="gray20")
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(
            self.frame_left,
            text="Seu Objeto Secreto",
            fg="white",
            bg="gray20",
            font=("Arial", 12, "bold"),
        ).pack(pady=10)

        self.lbl_image = tk.Label(
            self.frame_left,
            text="Aguardando\ninício do jogo...",
            bg="gray30",
            fg="white",
            width=35,
            height=15,
        )
        self.lbl_image.pack(padx=10, pady=5)

        tk.Label(
            self.frame_left,
            text="Placar",
            fg="white",
            bg="gray20",
            font=("Arial", 11, "bold"),
        ).pack(pady=(10, 0))
        self.txt_scores = tk.Text(
            self.frame_left,
            state="disabled",
            height=8,
            bg="gray25",
            fg="white",
            relief=tk.FLAT,
            font=("Courier", 10),
        )
        self.txt_scores.pack(fill=tk.X, padx=10, pady=(0, 5))

        tk.Label(
            self.frame_left,
            text="Dicas Descobertas",
            fg="white",
            bg="gray20",
            font=("Arial", 11, "bold"),
        ).pack(pady=(10, 0))
        self.txt_hints_history = tk.Text(
            self.frame_left,
            state="disabled",
            height=8,
            bg="gray25",
            fg="#90EE90",
            relief=tk.FLAT,
            font=("Courier", 10),
        )
        self.txt_hints_history.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.frame_mid = tk.Frame(self.root, width=250)
        self.frame_mid.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.btn_iniciar = tk.Button(
            self.frame_mid,
            text="▶ Iniciar Partida",
            command=self.cmd_iniciar,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.btn_iniciar.pack(fill=tk.X, pady=10)

        tk.Label(self.frame_mid, text="Dica Pública:").pack(anchor=tk.W, pady=(10, 0))
        self.entry_dica = tk.Entry(self.frame_mid)
        self.entry_dica.pack(fill=tk.X, ipady=3)
        self.btn_dica = tk.Button(
            self.frame_mid, text="Enviar Dica", command=self.cmd_dica
        )
        self.btn_dica.pack(fill=tk.X, pady=2)

        tk.Label(self.frame_mid, text="Adivinhar (Jogador Alvo):").pack(
            anchor=tk.W, pady=(10, 0)
        )
        self.val_alvo = tk.StringVar(self.root)
        self.opt_alvo = tk.OptionMenu(self.frame_mid, self.val_alvo, "")
        self.opt_alvo.pack(fill=tk.X)

        tk.Label(self.frame_mid, text="Adivinhar (Palpite):").pack(anchor=tk.W)
        self.entry_palpite = tk.Entry(self.frame_mid)
        self.entry_palpite.pack(fill=tk.X, ipady=3)
        self.btn_adivinhar = tk.Button(
            self.frame_mid, text="Enviar Palpite", command=self.cmd_adivinhar
        )
        self.btn_adivinhar.pack(fill=tk.X, pady=2)

        tk.Label(self.frame_mid, text="Trocar Dica:").pack(anchor=tk.W, pady=(10, 0))
        self.val_trade_alvo = tk.StringVar(self.root)
        self.opt_trade_alvo = tk.OptionMenu(self.frame_mid, self.val_trade_alvo, "")
        self.opt_trade_alvo.pack(fill=tk.X)

        self.entry_trade_dica = tk.Entry(self.frame_mid)
        self.entry_trade_dica.pack(fill=tk.X, ipady=3)
        self.entry_trade_dica.insert(0, "")
        self.btn_trade_solicitar = tk.Button(
            self.frame_mid, text="Solicitar Troca", command=self.cmd_trade_solicitar
        )
        self.btn_trade_solicitar.pack(fill=tk.X, pady=2)

        self.frame_trade_resp = tk.Frame(
            self.frame_mid, relief=tk.GROOVE, bd=2, bg="#fff8e1"
        )
        self.lbl_trade_resp = tk.Label(
            self.frame_trade_resp,
            text="",
            wraplength=220,
            bg="#fff8e1",
            font=("Arial", 9, "bold"),
        )
        self.lbl_trade_resp.pack(anchor=tk.W, padx=5, pady=2)
        tk.Label(self.frame_trade_resp, text="Sua dica em troca:", bg="#fff8e1").pack(
            anchor=tk.W, padx=5
        )
        self.entry_trade_resp_dica = tk.Entry(self.frame_trade_resp)
        self.entry_trade_resp_dica.pack(fill=tk.X, padx=5, ipady=3)
        self.btn_aceitar = tk.Button(
            self.frame_trade_resp,
            text="Aceitar Troca",
            command=self.cmd_aceitar_troca,
            bg="#4CAF50",
            fg="white",
        )
        self.btn_aceitar.pack(fill=tk.X, padx=5, pady=2)
        self.btn_recusar = tk.Button(
            self.frame_trade_resp,
            text="Recusar Troca",
            command=self.cmd_recusar_troca,
            bg="#f44336",
            fg="white",
        )
        self.btn_recusar.pack(fill=tk.X, padx=5, pady=2)

        self.btn_pronto = tk.Button(
            self.frame_mid,
            text="Pronto (Encerrar meu Turno)",
            command=self.cmd_pronto,
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.btn_pronto.pack(fill=tk.X, pady=(10, 2))

        self.btn_continuar = tk.Button(
            self.frame_mid,
            text="Continuar Jogo",
            command=self.cmd_continuar,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.btn_continuar.pack(fill=tk.X, pady=2)
        self.btn_encerrar_jogo = tk.Button(
            self.frame_mid,
            text="Encerrar Jogo",
            command=self.cmd_encerrar_jogo,
            bg="#9C27B0",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.btn_encerrar_jogo.pack(fill=tk.X, pady=2)

        self.btn_votar = tk.Button(
            self.frame_mid, text="Votar para Reiniciar Jogo", command=self.cmd_votar
        )
        self.btn_votar.pack(fill=tk.X, pady=5)

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

        self.frame_right = tk.Frame(self.root)
        self.frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.frame_manual = tk.Frame(
            self.frame_right, bg="#eee", relief=tk.SUNKEN, bd=1
        )
        self.frame_manual.pack(fill=tk.X, pady=(0, 5))
        tk.Label(
            self.frame_manual,
            text="MANUAL RÁPIDO",
            font=("Arial", 10, "bold"),
            bg="#eee",
        ).pack()
        self.txt_manual = tk.Text(
            self.frame_manual, height=6, font=("Arial", 9), bg="#eee", relief=tk.FLAT
        )
        self.txt_manual.pack(fill=tk.X, padx=5)
        self._fill_manual_text()

        tk.Label(
            self.frame_right, text="Histórico de Jogo", font=("Arial", 12, "bold")
        ).pack(anchor=tk.W)

        self.txt_log = scrolledtext.ScrolledText(
            self.frame_right, state="disabled", wrap=tk.WORD, bg="#f4f4f4", height=12
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        tk.Label(self.frame_right, text="Chat Global", font=("Arial", 12, "bold")).pack(
            anchor=tk.W
        )

        self.txt_chat = scrolledtext.ScrolledText(
            self.frame_right, state="disabled", wrap=tk.WORD, bg="#ffffff", height=10
        )
        self.txt_chat.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.frame_chat = tk.Frame(self.frame_right)
        self.frame_chat.pack(fill=tk.X, pady=5)
        self.entry_chat = tk.Entry(self.frame_chat)
        self.entry_chat.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.entry_chat.bind("<Return>", lambda e: self.cmd_chat())
        tk.Button(
            self.frame_chat, text="Enviar Chat", command=self.cmd_chat, width=15
        ).pack(side=tk.RIGHT, padx=(5, 0), ipady=2)

    def _fill_manual_text(self):
        manual = (
            " CONTROLES DE JOGO\n"
            " " + "—" * 25 + "\n"
            " Iniciar       : Comeca a partida (LOBBY).\n"
            " Dica Publica  : Palavra unica sobre seu objeto.\n"
            " Adivinhar     : Escolha o alvo e mande seu palpite.\n"
            " Trocar        : Troca privada de dicas (1x/turno).\n"
            " Pronto        : Encerra suas acoes no turno.\n"
            " " + "—" * 25 + "\n"
            " Dica: Use o chat apenas para conversar!"
        )
        self.txt_manual.config(state="normal")
        self.txt_manual.insert(tk.END, manual)
        self.txt_manual.config(state="disabled")

    def log_hint(self, hint_msg):
        self.txt_hints_history.config(state="normal")
        self.txt_hints_history.insert(tk.END, hint_msg + "\n")
        self.txt_hints_history.see(tk.END)
        self.txt_hints_history.config(state="disabled")

    def _set_state(self, widgets, enabled):
        state = "normal" if enabled else "disabled"
        for w in widgets:
            w.config(state=state)
            if isinstance(w, tk.Button) and w in self._btn_colors:
                w.config(bg=self._btn_colors[w] if enabled else DISABLED_BG)

    def log_message(self, msg):
        self.txt_log.config(state="normal")
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    def log_chat(self, sender, msg):
        self.txt_chat.config(state="normal")
        self.txt_chat.insert(tk.END, f"[{sender}]: {msg}\n")
        self.txt_chat.see(tk.END)
        self.txt_chat.config(state="disabled")

    def log_hint(self, hint_msg):
        self.txt_hints_history.config(state="normal")
        self.txt_hints_history.insert(tk.END, hint_msg + "\n")
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

    def process_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                event = msg[0]
                if event == "chat":
                    self.log_chat(msg[1], msg[2])
                elif event == "log":
                    if any(
                        x in msg[1]
                        for x in ["[DICA PÚBLICA]", "[TROCA CONCLUÍDA]", "[ESPIONAGEM]"]
                    ):
                        self.log_hint(msg[1])
                    else:
                        self.log_message(msg[1])
                elif event == "phase":
                    new_phase, message = msg[1], msg[2]
                    self.log_message(
                        f"\n--- FASE ALTERADA: {new_phase} ---\n-> {message}"
                    )
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
                        f"[TROCA] {sender} enviou um pedido de troca. Responda no painel de ações."
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
            image = image.resize((260, 260), resample_filter)
            photo = ImageTk.PhotoImage(image)
            self.lbl_image.config(
                image=photo, text="", bg="black", width=260, height=260
            )
            self.lbl_image.image = photo
            self.log_message("*** Imagem carregada e exibida na interface! ***")
        except Exception as e:
            self.log_message(f"[ERRO] Falha ao carregar imagem: {e}")

    def ask_judgment(self, guesser, guess_word):
        resposta = messagebox.askyesno(
            "Julgamento Necessário!",
            f"O jogador {guesser} tentou adivinhar que o seu objeto é '{guess_word}'.\n\nEsse palpite está CORRETO?",
        )
        try:
            ok, msg = self.server.judge_guess(self.player_name, guesser, resposta)
            if ok:
                self.log_message(
                    f"-> Você informou ao servidor que o palpite de {guesser} estava {'CORRETO' if resposta else 'ERRADO'}."
                )
            else:
                self.log_message(f"-> Falha ao registrar julgamento: {msg}")
        except Exception as e:
            self.log_message(f"[ERRO] Falha ao enviar julgamento: {e}")

    def send_action(self, action_func, *args):
        try:
            res = action_func(*args)
            if isinstance(res, tuple) and len(res) == 2:
                ok, msg = res
            else:
                ok, msg = True, res
            if msg:
                self.log_message(f"-> {msg}")
            return ok
        except Exception as e:
            self.log_message(f"[ERRO DE REDE] {e}")
            return False

    def cmd_iniciar(self):
        self.send_action(self.server.start_game, self.player_name)

    def cmd_dica(self):
        dica = self.entry_dica.get().strip()
        if not dica:
            return
        if len(dica.split()) != 1:
            self.log_message("-> Erro: a dica deve ser uma única palavra.")
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
            self.log_message("-> Erro: informe o jogador alvo e a dica.")
            return
        if len(dica.split()) != 1:
            self.log_message("-> Erro: a dica deve ser uma única palavra.")
            return
        ok = self.send_action(self.server.request_trade, self.player_name, alvo, dica)
        if ok:
            self.entry_trade_dica.delete(0, tk.END)

    def cmd_aceitar_troca(self):
        dica = self.entry_trade_resp_dica.get().strip()
        if not dica:
            self.log_message("-> Erro: informe sua dica para aceitar a troca.")
            return
        if len(dica.split()) != 1:
            self.log_message("-> Erro: a dica deve ser uma única palavra.")
            return
        if not self.pending_trade_from:
            self.log_message("-> Erro: nenhum pedido de troca pendente.")
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
            self.log_message("-> Erro: nenhum pedido de troca pendente.")
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
