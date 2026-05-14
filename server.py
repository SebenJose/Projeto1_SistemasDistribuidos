import Pyro5.api
import threading
import random
import unicodedata
import base64

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower().strip()

class ChatSystem:
    def __init__(self):
        self.history = []
    def add_message(self, sender, message):
        self.history.append((sender, message))

@Pyro5.api.expose
@Pyro5.api.behavior(instance_mode="single")
class GameServer:
    def __init__(self):
        self.chat_system = ChatSystem()
        self.clients = {}  
        self._lock = threading.RLock()
        
        self.phase = "LOBBY"
        self.player_states = {}
        
        # Dicionário e Sinônimos
        self.possible_objects = ["Cachorro", "Carro", "Maca", "Bicicleta", "Computador", "Violao", "Livro", "Relogio", "Aviao", "Cadeira"]
        self.object_synonyms = {
            "cachorro": ["cao", "dog", "cachorrinho", "cadela"],
            "carro": ["automovel", "veiculo", "caranga", "auto"],
            "maca": ["apple", "fruta"],
            "bicicleta": ["bike", "magrela", "bici"],
            "computador": ["pc", "notebook", "laptop", "computador"],
            "violao": ["guitarra", "violaozinho", "viola"],
            "livro": ["obra", "livrinho", "book"],
            "relogio": ["despertador", "watch"],
            "aviao": ["aeronave", "jatinho", "airplane"],
            "cadeira": ["assento", "poltrona", "banco"]
        }
        
        self.pending_trades = {}
        self.trade_history = {}
        self.restart_votes = set()
        
        self.turn_count = 1
        self.MAX_TURNS = 3
        self.pending_guesses = {}

    def _check_guess(self, correct_obj, guess_word):
        # Este método não é mais utilizado para arbitração, 
        # mas fica mantido como fallback ou por referência.
        c_clean = remove_accents(correct_obj)
        g_clean = remove_accents(guess_word)
        if c_clean == g_clean:
            return True
        synonyms = self.object_synonyms.get(c_clean, [])
        return g_clean in [remove_accents(s) for s in synonyms]

    def _broadcast_event(self, method_name, *args):
        disconnected = []
        with self._lock:
            for name, uri in list(self.clients.items()):
                try:
                    with Pyro5.api.Proxy(uri) as proxy:
                        getattr(proxy, method_name)(*args)
                except Exception as e:
                    print(f"[Servidor] Falha ao notificar '{name}': {e}")
                    disconnected.append(name)
            
            for name in disconnected:
                del self.clients[name]
                if name in self.player_states:
                    del self.player_states[name]

    def register_client(self, name, callback_uri):
        with self._lock:
            if name in self.clients:
                return False, "Nome já em uso. Escolha outro."
            if self.phase != "LOBBY":
                return False, "Partida já em andamento. Aguarde."
            
            self.clients[name] = callback_uri

        self.broadcast_chat("Sistema", f"'{name}' entrou na sala.")
        self._broadcast_event("phase_changed", self.phase, f"Estamos no LOBBY. Jogadores conectados: {len(self.clients)}")
        return True, "Registrado com sucesso!"

    def send_chat_message(self, sender, message):
        self.chat_system.add_message(sender, message)
        self.broadcast_chat(sender, message)

    def broadcast_chat(self, sender, message):
        self._broadcast_event("receive_chat_message", sender, message)

    def start_game(self, initiator):
        with self._lock:
            if self.phase != "LOBBY":
                return False, "O jogo já iniciou."
            if len(self.clients) < 2:
                return False, "Necessário pelo menos 2 jogadores."
            
            self.phase = "WAITING_HINTS"
            self.turn_count = 1
            objects = random.sample(self.possible_objects, len(self.clients))
            for idx, name in enumerate(self.clients.keys()):
                current_score = self.player_states.get(name, {}).get('score', 0)
                self.player_states[name] = {
                    'object': objects[idx],
                    'score': current_score,
                    'public_hint': None,
                    'guessers': [], # Lista de quem acertou
                    'is_ready': False, # Controle do /pronto
                    'has_traded': False # Limite de troca
                }
                
            self.restart_votes.clear()
            self.pending_trades.clear()
            self.trade_history.clear()
            self.pending_guesses = {name: [] for name in self.clients.keys()}
            
        for name, state in self.player_states.items():
            obj_name = state['object']
            img_base64 = ""
            try:
                with open(f"objects_images/{obj_name}.png", "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"[Aviso] Imagem não encontrada para {obj_name}: {e}")
                
            try:
                with Pyro5.api.Proxy(self.clients[name]) as proxy:
                    proxy.game_started(state['object'], img_base64)
            except:
                pass
                
        self._broadcast_event("phase_changed", "WAITING_HINTS", f"Turno {self.turn_count}/{self.MAX_TURNS} iniciado! O jogo começou! Todos devem enviar sua dica pública.")
        return True, "Jogo iniciado."

    def send_public_hint(self, sender, hint):
        with self._lock:
            if self.phase != "WAITING_HINTS":
                return False, "Não estamos na fase de aguardar dicas."
            if self.player_states[sender]['public_hint'] is not None:
                return False, "Você já enviou sua dica pública."
                
            self.player_states[sender]['public_hint'] = hint
            all_hints = all(state['public_hint'] is not None for state in self.player_states.values())
            if all_hints:
                self.phase = "ACTION_PHASE"
        
        self._broadcast_event("receive_public_hint", sender, hint)
        if all_hints:
            self._broadcast_event("phase_changed", "ACTION_PHASE", "Fase de Ações liberada! Façam seus palpites, trocas e espionagens. Quando terminar, encerre seu turno.")
            
        return True, "Dica recebida."

    def request_trade(self, sender, target, hint):
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Apenas na ACTION_PHASE."
            if target not in self.player_states or sender == target:
                return False, "Alvo inválido."
            if self.player_states[sender]['has_traded']:
                return False, "Você já realizou ou aceitou uma troca nesta rodada."
            if target in self.pending_trades:
                return False, "Alvo já possui pedido pendente."
            if self.player_states[sender]['is_ready']:
                return False, "Você já está marcado como pronto. Aguarde o fim do turno."
                
            self.pending_trades[target] = {'sender': sender, 'hint': hint}
            
        try:
            with Pyro5.api.Proxy(self.clients[target]) as proxy:
                proxy.receive_trade_request(sender)
        except Exception as e:
            return False, f"Falha ao contactar alvo: {e}"
        return True, f"Pedido enviado para {target}."

    def respond_trade(self, target, sender, accept, target_hint=None):
        with self._lock:
            if target not in self.pending_trades or self.pending_trades[target]['sender'] != sender:
                return False, "Nenhum pedido pendente deste jogador."
                
            pending = self.pending_trades.pop(target)
            sender_hint = pending['hint']
            
            if not accept:
                try:
                    with Pyro5.api.Proxy(self.clients[sender]) as proxy:
                        proxy.trade_rejected(target)
                except:
                    pass
                return True, "Troca recusada."
                
            self.trade_history[frozenset([sender, target])] = (sender_hint, target_hint)
            self.player_states[sender]['has_traded'] = True
            self.player_states[target]['has_traded'] = True
            
        try:
            with Pyro5.api.Proxy(self.clients[sender]) as proxy:
                proxy.trade_completed(target, target_hint)
        except: pass
        try:
            with Pyro5.api.Proxy(self.clients[target]) as proxy:
                proxy.trade_completed(sender, sender_hint)
        except: pass
            
        self._broadcast_event("trade_occurred_public", sender, target)
        return True, "Troca efetivada!"

    def spy_on_trade(self, spy_name, player_a, player_b):
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Apenas na ACTION_PHASE."
            if spy_name in (player_a, player_b):
                return False, "Você não pode espiar a si mesmo."
            if self.player_states[spy_name]['is_ready']:
                return False, "Você já está marcado como pronto."
            
            trade_key = frozenset([player_a, player_b])
            if trade_key not in self.trade_history:
                return False, "Troca inexistente."
                
            if random.random() < 0.30:
                self.player_states[spy_name]['score'] -= 10
                fail = True
            else:
                self.player_states[spy_name]['score'] += 5
                fail = False
            
            hints = self.trade_history[trade_key]

        if fail:
            self._broadcast_event("spy_result", spy_name, player_a, player_b, False)
            return True, "FALHA: Você foi pego e perdeu 10 pontos."
        else:
            self._broadcast_event("spy_result", spy_name, player_a, player_b, True)
            return True, f"SUCESSO: Dicas trocadas foram: '{hints[0]}' e '{hints[1]}'"

    def guess_object(self, guesser, target, guess_word):
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Apenas na ACTION_PHASE."
            if target not in self.player_states or guesser == target:
                return False, "Alvo inválido."
            if guesser in self.player_states[target]['guessers']:
                return False, "Você já acertou o objeto deste jogador."
            if self.player_states[guesser]['is_ready']:
                return False, "Você já está pronto e não pode mais adivinhar."
                
            self.pending_guesses[target].append((guesser, guess_word))

        try:
            with Pyro5.api.Proxy(self.clients[target]) as proxy:
                proxy.request_judgment(guesser, guess_word)
        except Exception as e:
            return False, f"Falha ao enviar para arbitração: {e}"
            
        return True, "Palpite enviado ao dono do objeto para julgamento. Aguarde."

    def judge_guess(self, judge_player, guesser, is_correct):
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Apenas na ACTION_PHASE."
                
            pending = self.pending_guesses.get(judge_player, [])
            found_guess = None
            for p in pending:
                if p[0] == guesser:
                    found_guess = p
                    break
            
            if not found_guess:
                return False, "Nenhum palpite pendente deste jogador."
            
            guess_word = found_guess[1]
            self.pending_guesses[judge_player].remove(found_guess)
            
            if is_correct:
                self.player_states[judge_player]['guessers'].append(guesser)
            else:
                self.player_states[guesser]['score'] -= 5

        if is_correct:
            self._broadcast_event("guess_result", guesser, judge_player, guess_word, True)
        else:
            self._broadcast_event("guess_result", guesser, judge_player, guess_word, False)
            
        return True, "Julgamento registrado."
            
        return True, "Palpite registrado."

    def player_ready(self, player):
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Você só pode encerrar o turno na ACTION_PHASE."
            if self.player_states[player]['is_ready']:
                return False, "Você já está pronto."
                
            self.player_states[player]['is_ready'] = True
            self.broadcast_chat("Sistema", f"'{player}' declarou que está PRONTO.")
            
            all_ready = all(state['is_ready'] for state in self.player_states.values())
            if all_ready:
                if self.turn_count < self.MAX_TURNS:
                    self.turn_count += 1
                    for name in self.player_states:
                        self.player_states[name]['is_ready'] = False
                        self.player_states[name]['public_hint'] = None
                    self.phase = "WAITING_HINTS"
                    self._broadcast_event("phase_changed", "WAITING_HINTS", f"Turno {self.turn_count}/{self.MAX_TURNS} iniciado! Mandem novas dicas públicas.")
                else:
                    self._calculate_scores_and_end_game()
                
        return True, "Você encerrou suas ações para este turno."

    def _calculate_scores_and_end_game(self):
        total_players = len(self.player_states)
        
        # Para cada objeto, distribuímos os pontos
        for target, state in self.player_states.items():
            guessers = state['guessers']
            num_guessers = len(guessers)
            
            # Pontuação Adivinhadores
            if num_guessers > 0:
                first_guesser = guessers[0]
                self.player_states[first_guesser]['score'] += 20
                for other_guesser in guessers[1:]:
                    self.player_states[other_guesser]['score'] += 10
                    
                # Bônus isolado
                if num_guessers == 1:
                    self.player_states[first_guesser]['score'] += 10
            
            # Pontuação Dono do Objeto
            if num_guessers == 1:
                state['score'] += 30
            elif 1 < num_guessers < (total_players - 1):
                state['score'] += 15
            elif num_guessers == 0:
                state['score'] += 0
            elif num_guessers >= (total_players - 1):
                state['score'] -= 20
                
        self.phase = "END_GAME"
        
        # Montar placar e revelações
        lines = ["\n===== FIM DA RODADA =====", "OBJETOS SECRETOS:"]
        for p, s in self.player_states.items():
            lines.append(f" - {p}: {s['object']} (Adivinhado por {len(s['guessers'])} jogadores)")
            
        lines.append("\nPLACAR FINAL:")
        for p, s in sorted(self.player_states.items(), key=lambda x: x[1]['score'], reverse=True):
            lines.append(f" - {p}: {s['score']} pts")
            
        lines.append("=========================")
        lines.append("Vote para jogar novamente.")
        
        final_message = "\n".join(lines)
        self._broadcast_event("phase_changed", "END_GAME", final_message)

    def vote_restart(self, player):
        with self._lock:
            if self.phase != "END_GAME":
                return False, "Votação só permitida no fim do jogo."
            self.restart_votes.add(player)
            if len(self.restart_votes) >= len(self.clients):
                self.phase = "LOBBY"
                self._broadcast_event("phase_changed", "LOBBY", "Todos votaram! De volta ao lobby. Alguém deve iniciar a nova partida.")
        return True, "Voto computado."

def main():
    print("Iniciando o Servidor (GameServer)...")
    daemon = Pyro5.api.Daemon(host="localhost", port=9090)
    uri = daemon.register(GameServer, objectId="GameServer")
    print(f"[Servidor] Escutando em: {uri}")
    print("[Servidor] Aguardando clientes...\n")
    daemon.requestLoop()

if __name__ == "__main__":
    main()
