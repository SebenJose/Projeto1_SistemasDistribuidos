import sys
import threading
import Pyro5.api
import base64
import os
import webbrowser

@Pyro5.api.expose
class ClientEvents:
    def __init__(self):
        # Usamos uma lock de impressão apenas para não embaralhar sys.stdout
        self.print_lock = threading.Lock()

    def _safe_print(self, text):
        with self.print_lock:
            sys.stdout.write("\r" + " " * 50 + "\r") # Limpa a linha
            sys.stdout.write(text + "\n")
            sys.stdout.write("Comando/Chat: ")
            sys.stdout.flush()

    @Pyro5.api.oneway
    def receive_chat_message(self, sender, message):
        self._safe_print(f"[CHAT] {sender}: {message}")

    @Pyro5.api.oneway
    def phase_changed(self, new_phase, message):
        self._safe_print(f"\n--- FASE ALTERADA: {new_phase} ---")
        self._safe_print(f"-> {message}")

    @Pyro5.api.oneway
    def game_started(self, secret_object, img_base64=""):
        self._safe_print(f"\n*** O JOGO COMEÇOU! ***")
        self._safe_print(f"*** SEU OBJETO SECRETO É: [{secret_object}] ***")
        if img_base64:
            try:
                img_data = base64.b64decode(img_base64)
                filepath = os.path.abspath(f"meu_objeto_{os.getpid()}.png")
                with open(filepath, "wb") as f:
                    f.write(img_data)
                self._safe_print(f"*** Abrindo imagem do objeto... ***")
                webbrowser.open(f"file://{filepath}")
            except Exception as e:
                self._safe_print(f"*** Erro ao carregar imagem: {e} ***")

    @Pyro5.api.oneway
    def receive_public_hint(self, sender, hint):
        self._safe_print(f"[DICA PÚBLICA] {sender} diz: A dica é '{hint}'")

    @Pyro5.api.oneway
    def receive_trade_request(self, sender):
        self._safe_print(f"[TROCA] O jogador {sender} quer trocar dicas com você!")
        self._safe_print(f"-> Use: /aceitar {sender} <sua_dica>  OU  /recusar {sender}")

    @Pyro5.api.oneway
    def trade_rejected(self, partner):
        self._safe_print(f"[TROCA] {partner} recusou o seu pedido de troca.")

    @Pyro5.api.oneway
    def trade_completed(self, partner, partner_hint):
        self._safe_print(f"[TROCA CONCLUÍDA] A dica de {partner} é: '{partner_hint}'")

    @Pyro5.api.oneway
    def trade_occurred_public(self, player_a, player_b):
        self._safe_print(f"[ALERTA] {player_a} e {player_b} efetuaram uma troca privada!")
        self._safe_print(f"-> Alguém quer tentar /espiar {player_a} {player_b} ?")

    @Pyro5.api.oneway
    def spy_result(self, spy_name, player_a, player_b, success):
        if success:
            self._safe_print(f"[ESPIONAGEM] {spy_name} espiou a troca de {player_a} e {player_b} e saiu impune!")
        else:
            self._safe_print(f"[ESPIONAGEM FALHOU] {spy_name} tentou espiar {player_a} e {player_b} e foi pego! Perdeu 10 pontos!")

    @Pyro5.api.oneway
    def guess_result(self, guesser, target, guess_word, is_correct):
        if is_correct:
            self._safe_print(f"[PALPITE] {guesser} ACERTOU que o objeto de {target} era '{guess_word}'!")
        else:
            self._safe_print(f"[PALPITE] {guesser} errou ao dizer que o objeto de {target} era '{guess_word}'.")

    @Pyro5.api.oneway
    def request_judgment(self, guesser, guess_word):
        self._safe_print(f"\n[JULGAMENTO NECESSÁRIO] O jogador {guesser} acha que seu objeto é '{guess_word}'!")
        self._safe_print(f"-> Use: /julgar {guesser} sim   OU   /julgar {guesser} nao")


def run_daemon(daemon):
    daemon.requestLoop()

def print_help():
    print("\n--- COMANDOS DISPONÍVEIS ---")
    print("/chat <msg>                 - Envia mensagem no chat global")
    print("/iniciar                    - Inicia a partida (no LOBBY)")
    print("/dica <palavra>             - Envia sua dica pública (WAITING_HINTS)")
    print("/trocar <jogador> <dica>    - Pede para trocar com alguém (ACTION_PHASE)")
    print("/aceitar <jogador> <dica>   - Aceita pedido de troca pendente")
    print("/recusar <jogador>          - Recusa pedido de troca")
    print("/espiar <jog_a> <jog_b>     - Tenta espiar troca de 2 jogadores")
    print("/adivinhar <jog> <objeto>   - Tenta adivinhar o objeto de alguém")
    print("/julgar <jog> sim|nao       - Confirma ou rejeita o palpite de alguém sobre seu objeto")
    print("/pronto                     - Encerra suas ações e aguarda os outros (Fim de turno)")
    print("/votar                      - Vota para jogar de novo (END_GAME)")
    print("/ajuda                      - Mostra este menu")
    print("/sair                       - Fecha o jogo")
    print("----------------------------\n")

def process_command(server, player_name, text):
    parts = text.split()
    cmd = parts[0].lower()
    
    try:
        if cmd == '/chat':
            msg = " ".join(parts[1:])
            server.send_chat_message(player_name, msg)
            return True, ""
        elif cmd == '/iniciar':
            return server.start_game(player_name)
        elif cmd == '/dica':
            if len(parts) < 2: return False, "Uso: /dica <palavra>"
            return server.send_public_hint(player_name, parts[1])
        elif cmd == '/trocar':
            if len(parts) < 3: return False, "Uso: /trocar <jogador> <sua_dica>"
            return server.request_trade(player_name, parts[1], parts[2])
        elif cmd == '/aceitar':
            if len(parts) < 3: return False, "Uso: /aceitar <jogador> <sua_dica>"
            return server.respond_trade(player_name, parts[1], True, parts[2])
        elif cmd == '/recusar':
            if len(parts) < 2: return False, "Uso: /recusar <jogador>"
            return server.respond_trade(player_name, parts[1], False)
        elif cmd == '/espiar':
            if len(parts) < 3: return False, "Uso: /espiar <jogadorA> <jogadorB>"
            return server.spy_on_trade(player_name, parts[1], parts[2])
        elif cmd == '/adivinhar':
            if len(parts) < 3: return False, "Uso: /adivinhar <jogador> <palavra>"
            return server.guess_object(player_name, parts[1], parts[2])
        elif cmd == '/julgar':
            if len(parts) < 3: return False, "Uso: /julgar <jogador> sim/nao"
            is_correct = parts[2].lower() in ['sim', 's', 'true', 'yes']
            return server.judge_guess(player_name, parts[1], is_correct)
        elif cmd == '/pronto':
            return server.player_ready(player_name)
        elif cmd == '/votar':
            return server.vote_restart(player_name)
        else:
            return False, "Comando desconhecido. Digite /ajuda"
    except Exception as e:
        return False, f"Erro de rede/servidor: {e}"

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 client.py <seu_nome>")
        sys.exit(1)
        
    player_name = sys.argv[1]
    
    client_daemon = Pyro5.api.Daemon()
    client_events_obj = ClientEvents()
    callback_uri = client_daemon.register(client_events_obj)
    
    daemon_thread = threading.Thread(target=run_daemon, args=(client_daemon,), daemon=True)
    daemon_thread.start()
    
    server_uri = "PYRO:GameServer@localhost:9090"
    server = Pyro5.api.Proxy(server_uri)
    
    try:
        success, msg = server.register_client(player_name, callback_uri)
        if not success:
            print(f"Erro ao registrar: {msg}")
            sys.exit(1)
            
        print_help()
        
        while True:
            try:
                user_input = input("Comando/Chat: ").strip()
                if not user_input:
                    continue
                    
                if user_input.lower() in ('/sair', '/quit', '/exit'):
                    break
                elif user_input.lower() == '/ajuda':
                    print_help()
                    continue
                
                if user_input.startswith('/'):
                    ok, result_msg = process_command(server, player_name, user_input)
                    if result_msg:
                        print(f"-> {result_msg}")
                else:
                    # Se não usar /chat, enviamos pro chat mesmo assim por conveniência
                    server.send_chat_message(player_name, user_input)
            
            except EOFError:
                break
                
    except Pyro5.errors.CommunicationError:
        print("Erro: Não foi possível se conectar ao Servidor.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        client_daemon.shutdown()
        daemon_thread.join(timeout=1.0)

if __name__ == "__main__":
    main()
