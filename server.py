import base64
import random
import threading
import unicodedata

import Pyro5.api


def remove_accents(s):
    return (
        "".join(
            c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
        )
        .lower()
        .strip()
    )


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
        self.possible_objects = [
            "Cachorro",
            "Carro",
            "Maca",
            "Bicicleta",
            "Computador",
            "Violao",
            "Livro",
            "Relogio",
            "Aviao",
            "Cadeira",
        ]
        self.pending_trades = {}
        self.trade_history = {}
        self.restart_votes = set()
        self.continue_votes = {}
        self.turn_count = 1
        self.MAX_TURNS = 3
        self.pending_guesses = {}

    def _find_player(self, name):
        name_lower = name.strip().lower()
        for key in self.player_states:
            if key.lower() == name_lower:
                return key
        return None

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

    def _broadcast_scores(self):
        scores = {name: state["score"] for name, state in self.player_states.items()}
        self._broadcast_event("scores_updated", scores)

    def register_client(self, name, callback_uri):
        with self._lock:
            if name in self.clients:
                return False, "Nome já em uso. Escolha outro."
            if self.phase != "LOBBY":
                return False, "Partida já em andamento. Aguarde."
            self.clients[name] = callback_uri
        self.broadcast_chat("Sistema", f"'{name}' entrou na sala.")
        self._broadcast_event(
            "phase_changed",
            self.phase,
            f"Estamos no LOBBY. Jogadores conectados: {len(self.clients)}",
        )
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
            self.restart_votes.clear()
            self.continue_votes.clear()
            self.pending_trades.clear()
            self.trade_history.clear()
            objects = random.sample(self.possible_objects, len(self.clients))
            for idx, name in enumerate(self.clients.keys()):
                current_score = self.player_states.get(name, {}).get("score", 0)
                self.player_states[name] = {
                    "object": objects[idx],
                    "score": current_score,
                    "public_hint": None,
                    "guessers": [],
                    "is_ready": False,
                    "has_traded": False,
                }
            self.pending_guesses = {name: [] for name in self.clients.keys()}

        for name, state in self.player_states.items():
            img_base64 = ""
            try:
                with open(f"objects_images/{state['object']}.png", "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                print(f"[Aviso] Imagem não encontrada para {state['object']}: {e}")
            try:
                with Pyro5.api.Proxy(self.clients[name]) as proxy:
                    proxy.game_started(state["object"], img_base64)
            except Exception:
                pass

        self._broadcast_scores()
        self._broadcast_event(
            "phase_changed",
            "WAITING_HINTS",
            f"Turno {self.turn_count}/{self.MAX_TURNS} iniciado! O jogo começou! Todos devem enviar sua dica pública.",
        )
        return True, "Jogo iniciado."

    def send_public_hint(self, sender, hint):
        all_hints = False
        with self._lock:
            if self.phase != "WAITING_HINTS":
                return False, "Não estamos na fase de aguardar dicas."
            if self.player_states[sender]["public_hint"] is not None:
                return False, "Você já enviou sua dica pública."
            if len(hint.split()) != 1:
                return False, "A dica deve ser uma única palavra."
            self.player_states[sender]["public_hint"] = hint
            all_hints = all(
                s["public_hint"] is not None for s in self.player_states.values()
            )
            if all_hints:
                self.phase = "ACTION_PHASE"
        self._broadcast_event("receive_public_hint", sender, hint)
        if all_hints:
            self._broadcast_event(
                "phase_changed",
                "ACTION_PHASE",
                "Fase de Ações liberada! Façam seus palpites, trocas e espionagens. Quando terminar, encerre seu turno.",
            )
        return True, "Dica recebida."

    def request_trade(self, sender, target, hint):
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Apenas na ACTION_PHASE."
            target = self._find_player(target) or target
            if target not in self.player_states or sender == target:
                return False, "Jogador não encontrado."
            if self.player_states[sender]["has_traded"]:
                return False, "Você já realizou ou aceitou uma troca nesta rodada."
            if target in self.pending_trades:
                return False, "Alvo já possui pedido pendente."
            if self.player_states[sender]["is_ready"]:
                return (
                    False,
                    "Você já está marcado como pronto. Aguarde o fim do turno.",
                )
            if len(hint.split()) != 1:
                return False, "A dica deve ser uma única palavra."
            self.pending_trades[target] = {"sender": sender, "hint": hint}
        try:
            with Pyro5.api.Proxy(self.clients[target]) as proxy:
                proxy.receive_trade_request(sender)
        except Exception as e:
            return False, f"Falha ao contactar alvo: {e}"
        return True, f"Pedido enviado para {target}."

    def respond_trade(self, target, sender, accept, target_hint=None):
        with self._lock:
            if (
                target not in self.pending_trades
                or self.pending_trades[target]["sender"] != sender
            ):
                return False, "Nenhum pedido pendente deste jogador."
            if accept and (target_hint is None or len(target_hint.split()) != 1):
                return False, "A dica deve ser uma única palavra."
            pending = self.pending_trades.pop(target)
            sender_hint = pending["hint"]
            if not accept:
                try:
                    with Pyro5.api.Proxy(self.clients[sender]) as proxy:
                        proxy.trade_rejected(target)
                except Exception:
                    pass
                return True, "Troca recusada."
            self.trade_history[frozenset([sender, target])] = (sender_hint, target_hint)
            self.player_states[sender]["has_traded"] = True
            self.player_states[target]["has_traded"] = True
        try:
            with Pyro5.api.Proxy(self.clients[sender]) as proxy:
                proxy.trade_completed(target, target_hint)
        except Exception:
            pass
        try:
            with Pyro5.api.Proxy(self.clients[target]) as proxy:
                proxy.trade_completed(sender, sender_hint)
        except Exception:
            pass
        self._broadcast_event("trade_occurred_public", sender, target)
        return True, "Troca efetivada!"

    def spy_on_trade(self, spy_name, player_a, player_b):
        fail = None
        hints = None
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Apenas na ACTION_PHASE."
            if spy_name in (player_a, player_b):
                return False, "Você não pode espiar a si mesmo."
            if self.player_states[spy_name]["is_ready"]:
                return False, "Você já está marcado como pronto."
            trade_key = frozenset([player_a, player_b])
            if trade_key not in self.trade_history:
                return False, "Troca inexistente."
            if random.random() < 0.30:
                self.player_states[spy_name]["score"] -= 10
                fail = True
            else:
                self.player_states[spy_name]["score"] += 5
                fail = False
            hints = self.trade_history[trade_key]
        self._broadcast_scores()
        if fail:
            self._broadcast_event("spy_result", spy_name, player_a, player_b, False)
            return True, "FALHA: Você foi pego e perdeu 10 pontos."
        self._broadcast_event("spy_result", spy_name, player_a, player_b, True)
        return True, f"SUCESSO: Dicas trocadas foram: '{hints[0]}' e '{hints[1]}'"

    def guess_object(self, guesser, target, guess_word):
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Apenas na ACTION_PHASE."
            target = self._find_player(target) or target
            if target not in self.player_states or guesser == target:
                return False, "Jogador não encontrado."
            if guesser in self.player_states[target]["guessers"]:
                return False, "Você já acertou o objeto deste jogador."
            if self.player_states[guesser]["is_ready"]:
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
            found = next((p for p in pending if p[0] == guesser), None)
            if not found:
                return False, "Nenhum palpite pendente deste jogador."
            guess_word = found[1]
            self.pending_guesses[judge_player].remove(found)
            if is_correct:
                self.player_states[judge_player]["guessers"].append(guesser)
            else:
                self.player_states[guesser]["score"] -= 5

        if is_correct:
            self._broadcast_event(
                "guess_result", guesser, judge_player, guess_word, True
            )
        else:
            self._broadcast_scores()
            self._broadcast_event(
                "guess_result", guesser, judge_player, guess_word, False
            )

        with self._lock:
            if self.phase == "ACTION_PHASE":
                all_players = set(self.player_states.keys())
                guessers_set = {
                    g for s in self.player_states.values() for g in s["guessers"]
                }
                if all_players == guessers_set:
                    self._calculate_scores_and_end_game()
                    return (
                        True,
                        "Julgamento registrado. Todos adivinharam — jogo encerrado!",
                    )

        return True, "Julgamento registrado."

    def player_ready(self, player):
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Você só pode encerrar o turno na ACTION_PHASE."
            if self.player_states[player]["is_ready"]:
                return False, "Você já está pronto."
            self.player_states[player]["is_ready"] = True
            self.broadcast_chat("Sistema", f"'{player}' declarou que está PRONTO.")
            all_ready = all(s["is_ready"] for s in self.player_states.values())
            if all_ready:
                self.continue_votes = {}
                self.phase = "VOTE_CONTINUE"
                self._broadcast_event(
                    "phase_changed",
                    "VOTE_CONTINUE",
                    f"Turno {self.turn_count}/{self.MAX_TURNS} concluído! Votem se desejam continuar ou encerrar o jogo.",
                )
        return True, "Você encerrou suas ações para este turno."

    def vote_continue(self, player, wants_continue):
        action = None
        next_turn_msg = ""
        with self._lock:
            if self.phase != "VOTE_CONTINUE":
                return (
                    False,
                    "Votação de continuação só permitida na fase VOTE_CONTINUE.",
                )
            if player not in self.player_states:
                return False, "Jogador não reconhecido."
            if player in self.continue_votes:
                return False, "Você já votou nesta rodada."
            self.continue_votes[player] = wants_continue
            if len(self.continue_votes) < len(self.player_states):
                return True, "Voto registrado. Aguardando os outros jogadores."
            votes_for = sum(1 for v in self.continue_votes.values() if v)
            if (
                votes_for > len(self.player_states) / 2
                and self.turn_count < self.MAX_TURNS
            ):
                self.turn_count += 1
                for name in self.player_states:
                    self.player_states[name]["is_ready"] = False
                    self.player_states[name]["public_hint"] = None
                    self.player_states[name]["has_traded"] = False
                self.pending_trades.clear()
                self.trade_history.clear()
                self.pending_guesses = {name: [] for name in self.player_states}
                self.phase = "WAITING_HINTS"
                action = "next_turn"
                next_turn_msg = f"Turno {self.turn_count}/{self.MAX_TURNS} iniciado! Mandem novas dicas públicas."
            else:
                action = "end_game"
        if action == "next_turn":
            self._broadcast_event("phase_changed", "WAITING_HINTS", next_turn_msg)
        elif action == "end_game":
            self._calculate_scores_and_end_game()
        return True, "Voto registrado."

    def _calculate_scores_and_end_game(self):
        with self._lock:
            if self.phase == "END_GAME":
                return
            self.phase = "END_GAME"

        total = len(self.player_states)
        for target, state in self.player_states.items():
            guessers = state["guessers"]
            n = len(guessers)
            if n > 0:
                self.player_states[guessers[0]]["score"] += 20 + (10 if n == 1 else 0)
                for g in guessers[1:]:
                    self.player_states[g]["score"] += 10
            if n == 1:
                state["score"] += 30
            elif 1 < n < total - 1:
                state["score"] += 15
            elif n >= total - 1:
                state["score"] -= 20

        lines = ["\n===== FIM DA RODADA =====", "OBJETOS SECRETOS:"]
        for p, s in self.player_states.items():
            lines.append(
                f" - {p}: {s['object']} (Adivinhado por {len(s['guessers'])} jogadores)"
            )
        lines.append("\nPLACAR FINAL:")
        for p, s in sorted(
            self.player_states.items(), key=lambda x: x[1]["score"], reverse=True
        ):
            lines.append(f" - {p}: {s['score']} pts")
        lines.append("=========================\nVote para jogar novamente.")
        self._broadcast_scores()
        self._broadcast_event("phase_changed", "END_GAME", "\n".join(lines))

    def vote_restart(self, player):
        with self._lock:
            if self.phase != "END_GAME":
                return False, "Votação só permitida no fim do jogo."
            self.restart_votes.add(player)
            if len(self.restart_votes) >= len(self.clients):
                self.restart_votes.clear()
                self.phase = "LOBBY"
                self._broadcast_event(
                    "phase_changed",
                    "LOBBY",
                    "Todos votaram! De volta ao lobby. Alguém deve iniciar a nova partida.",
                )
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
