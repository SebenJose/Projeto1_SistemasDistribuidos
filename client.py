import sys
import threading
import queue
import Pyro5.api
import base64
import tkinter as tk
from tkinter import scrolledtext, messagebox
from PIL import Image, ImageTk
from io import BytesIO

DISABLED_BG = "#9e9e9e"


@Pyro5.api.expose
class ClientEvents:
    def __init__(self, msg_queue):
        self.msg_queue = msg_queue

    @Pyro5.api.oneway
    def receive_chat_message(self, sender, message):
        self.msg_queue.put(("chat", sender, message))

    @Pyro5.api.oneway
    def phase_changed(self, new_phase, message):
        self.msg_queue.put(("phase", new_phase, message))

    @Pyro5.api.oneway
    def game_started(self, secret_object, img_base64=""):
        self.msg_queue.put(("log", f"\n*** O JOGO COMEÇOU! ***\n*** SEU OBJETO SECRETO É: [{secret_object}] ***"))
        if img_base64:
            self.msg_queue.put(("image", img_base64))

    @Pyro5.api.oneway
    def receive_public_hint(self, sender, hint):
        self.msg_queue.put(("log", f"[DICA PÚBLICA] {sender} diz: A dica é '{hint}'"))

    @Pyro5.api.oneway
    def receive_trade_request(self, sender):
        self.msg_queue.put(("trade_request", sender))

    @Pyro5.api.oneway
    def trade_rejected(self, partner):
        self.msg_queue.put(("log", f"[TROCA] {partner} recusou o seu pedido de troca."))

    @Pyro5.api.oneway
    def trade_completed(self, partner, partner_hint):
        self.msg_queue.put(("log", f"[TROCA CONCLUÍDA] A dica secreta de {partner} é: '{partner_hint}'"))

    @Pyro5.api.oneway
    def trade_occurred_public(self, player_a, player_b):
        self.msg_queue.put(("log", f"[ALERTA] {player_a} e {player_b} efetuaram uma troca privada!\n-> Use o painel 'Espiar Troca' para tentar ver as dicas trocadas."))

    @Pyro5.api.oneway
    def spy_result(self, spy_name, player_a, player_b, success):
        if success:
            self.msg_queue.put(("log", f"[ESPIONAGEM] {spy_name} espiou a troca de {player_a} e {player_b} e saiu impune!"))
        else:
            self.msg_queue.put(("log", f"[ESPIONAGEM FALHOU] {spy_name} tentou espiar {player_a} e {player_b} e foi pego! Perdeu 10 pontos!"))

    @Pyro5.api.oneway
    def guess_result(self, guesser, target, guess_word, is_correct):
        if is_correct:
            self.msg_queue.put(("log", f"[PALPITE] {guesser} ACERTOU que o objeto de {target} era '{guess_word}'!"))
        else:
            self.msg_queue.put(("log", f"[PALPITE] {guesser} errou ao dizer que o objeto de {target} era '{guess_word}'."))

    @Pyro5.api.oneway
    def request_judgment(self, guesser, guess_word):
        self.msg_queue.put(("judgment", guesser, guess_word))

    @Pyro5.api.oneway
    def scores_updated(self, scores):
        self.msg_queue.put(("scores", scores))


class GameGUI:
    def __init__(self, root, player_name, server_uri="PYRO:GameServer@localhost:9090"):
        self.root = root
        self.player_name = player_name
        self.server = Pyro5.api.Proxy(server_uri)
        self.root.title(f"Adivinhação - Jogador: {player_name}")
        self.root.geometry("950x700")
        self.msg_queue = queue.Queue()
        self._btn_colors = {}

        self.current_phase = "LOBBY"
        self.hint_sent = False
        self.is_ready = False
        self.pending_trade_from = None
        self.continue_votes_cast = False

        self.client_daemon = Pyro5.api.Daemon()
        self.client_events = ClientEvents(self.msg_queue)
        self.callback_uri = self.client_daemon.register(self.client_events)
        self.daemon_thread = threading.Thread(target=self.client_daemon.requestLoop, daemon=True)
        self.daemon_thread.start()

        self.setup_ui()

        try:
            success, msg = self.server.register_client(self.player_name, self.callback_uri)
            if not success:
                messagebox.showerror("Erro de Conexão", msg)
                self.root.destroy()
                return
            self.log_message(f"Conectado ao servidor: {msg}")
            self._log_manual()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível conectar ao Servidor: {e}")
            self.root.destroy()
            return

        self.root.after(100, self.process_queue)

    def _log_manual(self):
        lines = [
            "\n=== MANUAL DA INTERFACE ===",
            "▶ Iniciar Partida    : inicia o jogo no LOBBY (mín. 2 jogadores).",
            "Dica Pública         : envie uma palavra descrevendo seu objeto secreto.",
            "Adivinhar            : informe o jogador alvo e seu palpite do objeto dele.",
            "Espiar Troca         : veja a dica trocada entre dois jogadores (30% risco: -10 pts / sucesso: +5 pts).",
            "Trocar Dica          : solicite troca de dica secreta com outro jogador (uma vez por turno).",
            "Pronto               : encerra suas ações no turno atual e aguarda os demais.",
            "Continuar / Encerrar : vote ao fim de cada turno se a partida continua ou termina.",
            "Votar para Reiniciar : no fim do jogo, vote para iniciar uma nova partida.",
            "Chat                 : campo inferior direito — comunicação livre entre jogadores.",
            "===========================\n",
        ]
        for line in lines:
            self.log_message(line)

    def setup_ui(self):
        self.frame_left = tk.Frame(self.root, width=300, bg="gray20")
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(self.frame_left, text="Seu Objeto Secreto", fg="white", bg="gray20",
                 font=("Arial", 12, "bold")).pack(pady=10)

        self.lbl_image = tk.Label(self.frame_left, text="Aguardando\ninício do jogo...",
                                  bg="gray30", fg="white", width=35, height=15)
        self.lbl_image.pack(padx=10, pady=5)

        tk.Label(self.frame_left, text="Placar", fg="white", bg="gray20",
                 font=("Arial", 11, "bold")).pack(pady=(10, 0))
        self.txt_scores = tk.Text(self.frame_left, state='disabled', height=8,
                                  bg="gray25", fg="white", relief=tk.FLAT, font=("Courier", 10))
        self.txt_scores.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.frame_mid = tk.Frame(self.root, width=250)
        self.frame_mid.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.btn_iniciar = tk.Button(self.frame_mid, text="▶ Iniciar Partida", command=self.cmd_iniciar,
                                     bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_iniciar.pack(fill=tk.X, pady=10)

        tk.Label(self.frame_mid, text="Dica Pública:").pack(anchor=tk.W, pady=(10, 0))
        self.entry_dica = tk.Entry(self.frame_mid)
        self.entry_dica.pack(fill=tk.X, ipady=3)
        self.btn_dica = tk.Button(self.frame_mid, text="Enviar Dica", command=self.cmd_dica)
        self.btn_dica.pack(fill=tk.X, pady=2)

        tk.Label(self.frame_mid, text="Adivinhar (Jogador Alvo):").pack(anchor=tk.W, pady=(10, 0))
        self.entry_alvo = tk.Entry(self.frame_mid)
        self.entry_alvo.pack(fill=tk.X, ipady=3)
        tk.Label(self.frame_mid, text="Adivinhar (Palpite):").pack(anchor=tk.W)
        self.entry_palpite = tk.Entry(self.frame_mid)
        self.entry_palpite.pack(fill=tk.X, ipady=3)
        self.btn_adivinhar = tk.Button(self.frame_mid, text="Enviar Palpite", command=self.cmd_adivinhar)
        self.btn_adivinhar.pack(fill=tk.X, pady=2)

        tk.Label(self.frame_mid, text="Espiar Troca:").pack(anchor=tk.W, pady=(10, 0))
        self.entry_espiar_j1 = tk.Entry(self.frame_mid)
        self.entry_espiar_j1.pack(fill=tk.X, ipady=3)
        self.entry_espiar_j1.insert(0, "Jogador 1")
        self.entry_espiar_j2 = tk.Entry(self.frame_mid)
        self.entry_espiar_j2.pack(fill=tk.X, ipady=3)
        self.entry_espiar_j2.insert(0, "Jogador 2")
        self.btn_espiar = tk.Button(self.frame_mid, text="Espiar Troca", command=self.cmd_espiar)
        self.btn_espiar.pack(fill=tk.X, pady=2)

        tk.Label(self.frame_mid, text="Trocar Dica:").pack(anchor=tk.W, pady=(10, 0))
        self.entry_trade_alvo = tk.Entry(self.frame_mid)
        self.entry_trade_alvo.pack(fill=tk.X, ipady=3)
        self.entry_trade_alvo.insert(0, "Jogador Alvo")
        self.entry_trade_dica = tk.Entry(self.frame_mid)
        self.entry_trade_dica.pack(fill=tk.X, ipady=3)
        self.entry_trade_dica.insert(0, "Sua dica")
        self.btn_trade_solicitar = tk.Button(self.frame_mid, text="Solicitar Troca",
                                             command=self.cmd_trade_solicitar)
        self.btn_trade_solicitar.pack(fill=tk.X, pady=2)

        self.frame_trade_resp = tk.Frame(self.frame_mid, relief=tk.GROOVE, bd=2, bg="#fff8e1")
        self.lbl_trade_resp = tk.Label(self.frame_trade_resp, text="", wraplength=220,
                                       bg="#fff8e1", font=("Arial", 9, "bold"))
        self.lbl_trade_resp.pack(anchor=tk.W, padx=5, pady=2)
        tk.Label(self.frame_trade_resp, text="Sua dica em troca:", bg="#fff8e1").pack(anchor=tk.W, padx=5)
        self.entry_trade_resp_dica = tk.Entry(self.frame_trade_resp)
        self.entry_trade_resp_dica.pack(fill=tk.X, padx=5, ipady=3)
        self.btn_aceitar = tk.Button(self.frame_trade_resp, text="Aceitar Troca",
                                     command=self.cmd_aceitar_troca, bg="#4CAF50", fg="white")
        self.btn_aceitar.pack(fill=tk.X, padx=5, pady=2)
        self.btn_recusar = tk.Button(self.frame_trade_resp, text="Recusar Troca",
                                     command=self.cmd_recusar_troca, bg="#f44336", fg="white")
        self.btn_recusar.pack(fill=tk.X, padx=5, pady=2)

        self.btn_pronto = tk.Button(self.frame_mid, text="Pronto (Encerrar meu Turno)",
                                    command=self.cmd_pronto, bg="#FF9800", fg="white",
                                    font=("Arial", 10, "bold"))
        self.btn_pronto.pack(fill=tk.X, pady=(10, 2))

        self.btn_continuar = tk.Button(self.frame_mid, text="Continuar Jogo",
                                       command=self.cmd_continuar, bg="#2196F3", fg="white",
                                       font=("Arial", 10, "bold"))
        self.btn_continuar.pack(fill=tk.X, pady=2)
        self.btn_encerrar_jogo = tk.Button(self.frame_mid, text="Encerrar Jogo",
                                           command=self.cmd_encerrar_jogo, bg="#9C27B0", fg="white",
                                           font=("Arial", 10, "bold"))
        self.btn_encerrar_jogo.pack(fill=tk.X, pady=2)

        self.btn_votar = tk.Button(self.frame_mid, text="Votar para Reiniciar Jogo",
                                   command=self.cmd_votar)
        self.btn_votar.pack(fill=tk.X, pady=5)

        for btn in [self.btn_iniciar, self.btn_dica, self.btn_adivinhar, self.btn_espiar,
                    self.btn_trade_solicitar, self.btn_pronto, self.btn_continuar,
                    self.btn_encerrar_jogo, self.btn_votar, self.btn_aceitar, self.btn_recusar]:
            self._btn_colors[btn] = btn.cget('bg')

        self.update_ui_state()

        self.frame_right = tk.Frame(self.root)
        self.frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(self.frame_right, text="Histórico / Chat Global",
                 font=("Arial", 12, "bold")).pack(anchor=tk.W)

        self.txt_log = scrolledtext.ScrolledText(self.frame_right, state='disabled',
                                                  wrap=tk.WORD, bg="#f4f4f4")
        self.txt_log.pack(fill=tk.BOTH, expand=True, pady=5)

        self.frame_chat = tk.Frame(self.frame_right)
        self.frame_chat.pack(fill=tk.X, pady=5)
        self.entry_chat = tk.Entry(self.frame_chat)
        self.entry_chat.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.entry_chat.bind("<Return>", lambda e: self.cmd_chat())
        tk.Button(self.frame_chat, text="Enviar / Comando", command=self.cmd_chat,
                  width=15).pack(side=tk.RIGHT, padx=(5, 0), ipady=2)

    def _set_state(self, widgets, enabled):
        state = 'normal' if enabled else 'disabled'
        for w in widgets:
            w.config(state=state)
            if isinstance(w, tk.Button) and w in self._btn_colors:
                w.config(bg=self._btn_colors[w] if enabled else DISABLED_BG)

    def log_message(self, msg):
        self.txt_log.config(state='normal')
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state='disabled')

    def update_scoreboard(self, scores):
        self.txt_scores.config(state='normal')
        self.txt_scores.delete('1.0', tk.END)
        for name, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            self.txt_scores.insert(tk.END, f"{name}: {score} pts\n")
        self.txt_scores.config(state='disabled')

    def update_ui_state(self):
        phase = self.current_phase
        all_widgets = [
            self.btn_iniciar,
            self.entry_dica, self.btn_dica,
            self.entry_alvo, self.entry_palpite, self.btn_adivinhar,
            self.entry_espiar_j1, self.entry_espiar_j2, self.btn_espiar,
            self.entry_trade_alvo, self.entry_trade_dica, self.btn_trade_solicitar,
            self.btn_pronto,
            self.btn_continuar, self.btn_encerrar_jogo,
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
                self._set_state([
                    self.entry_alvo, self.entry_palpite, self.btn_adivinhar,
                    self.entry_espiar_j1, self.entry_espiar_j2, self.btn_espiar,
                    self.entry_trade_alvo, self.entry_trade_dica, self.btn_trade_solicitar,
                    self.btn_pronto,
                ], True)
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
                    self.log_message(f"[{msg[1]}]: {msg[2]}")
                elif event == "log":
                    self.log_message(msg[1])
                elif event == "phase":
                    new_phase, message = msg[1], msg[2]
                    self.log_message(f"\n--- FASE ALTERADA: {new_phase} ---\n-> {message}")
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
                    self.lbl_trade_resp.config(text=f"{sender} quer trocar dicas com você!")
                    self.frame_trade_resp.pack(fill=tk.X, pady=5)
                    self.log_message(f"[TROCA] {sender} enviou um pedido de troca. Responda no painel de ações.")
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
            image = image.resize((260, 260), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            self.lbl_image.config(image=photo, text="", bg="black", width=260, height=260)
            self.lbl_image.image = photo
            self.log_message("*** Imagem carregada e exibida na interface! ***")
        except Exception as e:
            self.log_message(f"[ERRO] Falha ao carregar imagem: {e}")

    def ask_judgment(self, guesser, guess_word):
        resposta = messagebox.askyesno(
            "Julgamento Necessário!",
            f"O jogador {guesser} tentou adivinhar que o seu objeto é '{guess_word}'.\n\nEsse palpite está CORRETO?"
        )
        try:
            self.server.judge_guess(self.player_name, guesser, resposta)
            self.log_message(f"-> Você informou ao servidor que o palpite de {guesser} estava {'CORRETO' if resposta else 'ERRADO'}.")
        except Exception as e:
            self.log_message(f"[ERRO] Falha ao enviar julgamento: {e}")

    def send_action(self, action_func, *args):
        try:
            ok, msg = action_func(*args)
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
        alvo = self.entry_alvo.get().strip()
        palpite = self.entry_palpite.get().strip()
        if alvo and palpite:
            self.send_action(self.server.guess_object, self.player_name, alvo, palpite)
            self.entry_palpite.delete(0, tk.END)

    def cmd_espiar(self):
        j1 = self.entry_espiar_j1.get().strip()
        j2 = self.entry_espiar_j2.get().strip()
        if j1 and j2:
            self.send_action(self.server.spy_on_trade, self.player_name, j1, j2)
            self.entry_espiar_j1.delete(0, tk.END)
            self.entry_espiar_j2.delete(0, tk.END)

    def cmd_trade_solicitar(self):
        alvo = self.entry_trade_alvo.get().strip()
        dica = self.entry_trade_dica.get().strip()
        if not alvo or not dica:
            self.log_message("-> Erro: informe o jogador alvo e a dica.")
            return
        if len(dica.split()) != 1:
            self.log_message("-> Erro: a dica deve ser uma única palavra.")
            return
        ok = self.send_action(self.server.request_trade, self.player_name, alvo, dica)
        if ok:
            self.entry_trade_alvo.delete(0, tk.END)
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
        ok = self.send_action(self.server.respond_trade,
                              self.player_name, self.pending_trade_from, True, dica)
        if ok:
            self.entry_trade_resp_dica.delete(0, tk.END)
            self.pending_trade_from = None
            self.frame_trade_resp.pack_forget()

    def cmd_recusar_troca(self):
        if not self.pending_trade_from:
            self.log_message("-> Erro: nenhum pedido de troca pendente.")
            return
        ok = self.send_action(self.server.respond_trade,
                              self.player_name, self.pending_trade_from, False)
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
        if texto.startswith('/'):
            parts = texto.split()
            cmd = parts[0].lower()
            if cmd == '/espiar' and len(parts) >= 3:
                self.send_action(self.server.spy_on_trade, self.player_name, parts[1], parts[2])
            else:
                self.log_message("-> Comando não reconhecido. Use o painel de ações ou /espiar J1 J2.")
        else:
            self.send_action(self.server.send_chat_message, self.player_name, texto)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python client.py <seu_nome>")
        sys.exit(1)

    root = tk.Tk()
    app = GameGUI(root, sys.argv[1])
    root.mainloop()
