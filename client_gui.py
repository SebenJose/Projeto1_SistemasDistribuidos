import sys
import threading
import queue
import Pyro5.api
import base64
import os
import tkinter as tk
from tkinter import scrolledtext, messagebox
from PIL import Image, ImageTk
from io import BytesIO

@Pyro5.api.expose
class ClientEvents:
    def __init__(self, msg_queue):
        self.msg_queue = msg_queue

    @Pyro5.api.oneway
    def receive_chat_message(self, sender, message):
        self.msg_queue.put(("chat", sender, message))

    @Pyro5.api.oneway
    def phase_changed(self, new_phase, message):
        self.msg_queue.put(("log", f"\n--- FASE ALTERADA: {new_phase} ---\n-> {message}"))

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
        self.msg_queue.put(("log", f"[TROCA] O jogador {sender} quer trocar dicas com você!\n-> Digite /aceitar {sender} <sua_dica> ou /recusar {sender} no campo abaixo."))

    @Pyro5.api.oneway
    def trade_rejected(self, partner):
        self.msg_queue.put(("log", f"[TROCA] {partner} recusou o seu pedido de troca."))

    @Pyro5.api.oneway
    def trade_completed(self, partner, partner_hint):
        self.msg_queue.put(("log", f"[TROCA CONCLUÍDA] A dica secreta de {partner} é: '{partner_hint}'"))

    @Pyro5.api.oneway
    def trade_occurred_public(self, player_a, player_b):
        self.msg_queue.put(("log", f"[ALERTA] {player_a} e {player_b} efetuaram uma troca privada!\n-> Você pode digitar /espiar {player_a} {player_b} no campo abaixo se quiser arriscar."))

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


class GameGUI:
    def __init__(self, root, player_name, server_uri="PYRO:GameServer@localhost:9090"):
        self.root = root
        self.player_name = player_name
        self.server = Pyro5.api.Proxy(server_uri)
        
        self.root.title(f"Adivinhação - Jogador: {player_name}")
        self.root.geometry("900x600")
        
        self.msg_queue = queue.Queue()
        
        # Iniciar thread do Pyro Daemon
        self.client_daemon = Pyro5.api.Daemon()
        self.client_events = ClientEvents(self.msg_queue)
        self.callback_uri = self.client_daemon.register(self.client_events)
        
        self.daemon_thread = threading.Thread(target=self.client_daemon.requestLoop, daemon=True)
        self.daemon_thread.start()
        
        self.setup_ui()
        
        # Registrar cliente no Servidor
        try:
            success, msg = self.server.register_client(self.player_name, self.callback_uri)
            if not success:
                messagebox.showerror("Erro de Conexão", msg)
                self.root.destroy()
                return
            self.log_message(f"Conectado ao servidor: {msg}")
            self.log_message("Para iniciar a partida, clique no botão 'Iniciar Partida'.")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível conectar ao Servidor: {e}")
            self.root.destroy()
            return
            
        # Inicia loop de verificação da fila (Thread-Safe)
        self.root.after(100, self.process_queue)

    def setup_ui(self):
        # Frame Esquerdo: Imagem
        self.frame_left = tk.Frame(self.root, width=300, bg="gray20")
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        tk.Label(self.frame_left, text="Seu Objeto Secreto", fg="white", bg="gray20", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.lbl_image = tk.Label(self.frame_left, text="Aguardando\ninício do jogo...", bg="gray30", fg="white", width=35, height=15)
        self.lbl_image.pack(padx=10, pady=10)
        
        # Frame Central: Ações
        self.frame_mid = tk.Frame(self.root, width=250)
        self.frame_mid.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        tk.Button(self.frame_mid, text="▶ Iniciar Partida", command=self.cmd_iniciar, bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(fill=tk.X, pady=10)
        
        tk.Label(self.frame_mid, text="Dica Pública:").pack(anchor=tk.W, pady=(10, 0))
        self.entry_dica = tk.Entry(self.frame_mid)
        self.entry_dica.pack(fill=tk.X, ipady=3)
        tk.Button(self.frame_mid, text="Enviar Dica", command=self.cmd_dica).pack(fill=tk.X, pady=2)
        
        tk.Label(self.frame_mid, text="Adivinhar (Jogador Alvo):").pack(anchor=tk.W, pady=(20,0))
        self.entry_alvo = tk.Entry(self.frame_mid)
        self.entry_alvo.pack(fill=tk.X, ipady=3)
        tk.Label(self.frame_mid, text="Adivinhar (Palpite):").pack(anchor=tk.W)
        self.entry_palpite = tk.Entry(self.frame_mid)
        self.entry_palpite.pack(fill=tk.X, ipady=3)
        tk.Button(self.frame_mid, text="Enviar Palpite", command=self.cmd_adivinhar).pack(fill=tk.X, pady=2)
        
        tk.Button(self.frame_mid, text="Pronto (Encerrar meu Turno)", command=self.cmd_pronto, bg="#FF9800", fg="white", font=("Arial", 10, "bold")).pack(fill=tk.X, pady=20)
        tk.Button(self.frame_mid, text="Votar para Reiniciar Jogo", command=self.cmd_votar).pack(fill=tk.X, pady=5)
        
        # Frame Direito: Logs e Chat
        self.frame_right = tk.Frame(self.root)
        self.frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(self.frame_right, text="Histórico / Chat Global", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        self.txt_log = scrolledtext.ScrolledText(self.frame_right, state='disabled', wrap=tk.WORD, bg="#f4f4f4")
        self.txt_log.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.frame_chat = tk.Frame(self.frame_right)
        self.frame_chat.pack(fill=tk.X, pady=5)
        self.entry_chat = tk.Entry(self.frame_chat)
        self.entry_chat.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.entry_chat.bind("<Return>", lambda e: self.cmd_chat())
        tk.Button(self.frame_chat, text="Enviar / Comando", command=self.cmd_chat, width=15).pack(side=tk.RIGHT, padx=(5,0), ipady=2)

    def log_message(self, msg):
        self.txt_log.config(state='normal')
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state='disabled')

    def process_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                event = msg[0]
                if event == "chat":
                    self.log_message(f"[{msg[1]}]: {msg[2]}")
                elif event == "log":
                    self.log_message(msg[1])
                elif event == "image":
                    self.display_image(msg[1])
                elif event == "judgment":
                    self.ask_judgment(msg[1], msg[2])
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
            self.lbl_image.image = photo  # Manter a referência para evitar GC
            self.log_message("*** Imagem carregada e exibida na interface! ***")
        except Exception as e:
            self.log_message(f"[ERRO] Falha ao carregar imagem: {e}")

    def ask_judgment(self, guesser, guess_word):
        # Esta função exibe um PopUp travando o usuário até ele responder
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
        except Exception as e:
            self.log_message(f"[ERRO DE REDE] {e}")

    def cmd_iniciar(self):
        self.send_action(self.server.start_game, self.player_name)
        
    def cmd_dica(self):
        dica = self.entry_dica.get().strip()
        if dica:
            self.send_action(self.server.send_public_hint, self.player_name, dica)
            self.entry_dica.delete(0, tk.END)
            
    def cmd_adivinhar(self):
        alvo = self.entry_alvo.get().strip()
        palpite = self.entry_palpite.get().strip()
        if alvo and palpite:
            self.send_action(self.server.guess_object, self.player_name, alvo, palpite)
            self.entry_palpite.delete(0, tk.END)

    def cmd_pronto(self):
        self.send_action(self.server.player_ready, self.player_name)
        
    def cmd_votar(self):
        self.send_action(self.server.vote_restart, self.player_name)
        
    def cmd_chat(self):
        texto = self.entry_chat.get().strip()
        if not texto: return
        self.entry_chat.delete(0, tk.END)
        
        # Permitir suporte a comandos legados com "/" (para trocar e espiar, que não ganharam botões próprios)
        if texto.startswith('/'):
            parts = texto.split()
            cmd = parts[0].lower()
            if cmd == '/trocar' and len(parts) >= 3:
                self.send_action(self.server.request_trade, self.player_name, parts[1], parts[2])
            elif cmd == '/aceitar' and len(parts) >= 3:
                self.send_action(self.server.respond_trade, self.player_name, parts[1], True, parts[2])
            elif cmd == '/recusar' and len(parts) >= 2:
                self.send_action(self.server.respond_trade, self.player_name, parts[1], False)
            elif cmd == '/espiar' and len(parts) >= 3:
                self.send_action(self.server.spy_on_trade, self.player_name, parts[1], parts[2])
            else:
                self.log_message("-> Comando não reconhecido ou incompleto.")
        else:
            self.send_action(self.server.send_chat_message, self.player_name, texto)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 client_gui.py <seu_nome>")
        sys.exit(1)
        
    root = tk.Tk()
    app = GameGUI(root, sys.argv[1])
    root.mainloop()
