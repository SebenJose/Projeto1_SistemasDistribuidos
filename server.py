import base64
import random
import threading

import Pyro5.api

from constants import (
    MAX_TURNS,
    OBJECT_SYNONYMS,
    POSSIBLE_OBJECTS,
    SERVER_HOST,
    SERVER_PORT,
    remove_accents,
)
from score import ScoreCalculator


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

        self.pending_trades = {}
        self.trade_history = {}
        self.restart_votes = set()
        self.continue_votes = {}
        self.turn_count = 1
        self.pending_guesses = {}
        self.failed_guesses = {}
        self.guesses_this_turn = set()
        self.round_scored = False

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
                except Exception:
                    disconnected.append(name)
            for name in disconnected:
                del self.clients[name]
                if name in self.player_states:
                    del self.player_states[name]

    def _broadcast_scores(self):
        scores_data = {}
        correct_guesses_made = {name: 0 for name in self.player_states}
        for state in self.player_states.values():
            for guesser in state["guessers"]:
                if guesser in correct_guesses_made:
                    correct_guesses_made[guesser] += 1

        for name, state in self.player_states.items():
            scores_data[name] = {
                "score": state["score"],
                "correct_guesses_made": correct_guesses_made[name],
                "object_guessed_by": len(state["guessers"]),
                "is_ready": state["is_ready"],
            }
        self._broadcast_event("scores_updated", scores_data)

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

    def _start_round(self, is_first=False):
        self.turn_count = 1
        self.round_scored = False
        self.pending_trades.clear()
        self.trade_history.clear()
        self.failed_guesses.clear()
        self.guesses_this_turn.clear()
        self.continue_votes.clear()

        objects = random.sample(POSSIBLE_OBJECTS, len(self.clients))
        for idx, name in enumerate(self.clients.keys()):
            if is_first:
                self.player_states[name] = {"score": 0}

            self.player_states[name].update(
                {
                    "object": objects[idx],
                    "public_hint": None,
                    "guessers": [],
                    "is_ready": False,
                    "has_traded": False,
                    "has_spied": False,
                }
            )
        self.pending_guesses = {name: [] for name in self.clients.keys()}

        for name, state in self.player_states.items():
            img_b64 = ""
            try:
                with open(f"objects_images/{state['object']}.png", "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass

            try:
                with Pyro5.api.Proxy(self.clients[name]) as proxy:
                    proxy.game_started(state["object"], img_b64)
            except Exception:
                pass

        self._broadcast_scores()
        self._broadcast_event(
            "phase_changed",
            "WAITING_HINTS",
            f"Rodada Iniciada! Mandem sua dica publica.",
        )

    def start_game(self, initiator):
        with self._lock:
            if self.phase != "LOBBY":
                return False, "O jogo ja iniciou."
            if len(self.clients) < 2:
                return False, "Minimo 2 jogadores."
            self.phase = "WAITING_HINTS"
            self._start_round(is_first=True)
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
                "Fase de Ações liberada! Façam seus palpites e trocas.",
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
                return False, "Você já realizou uma troca nesta rodada."
            if target in self.pending_trades:
                return False, "Alvo já possui pedido pendente."
            if self.player_states[sender]["is_ready"]:
                return False, "Você já está marcado como pronto."
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
            if self.player_states[spy_name]["has_spied"]:
                return False, "Você já realizou uma espionagem neste turno."
            trade_key = frozenset([player_a, player_b])
            if trade_key not in self.trade_history:
                return False, "Troca inexistente."

            self.player_states[spy_name]["has_spied"] = True
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
            if guesser in self.guesses_this_turn:
                return False, "Você já enviou um palpite neste turno."
            if guesser in self.player_states[target]["guessers"]:
                return False, "Você já acertou o objeto deste jogador."
            if (guesser, target) in self.failed_guesses:
                return False, "Você já errou o objeto deste jogador neste turno."
            if self.player_states[guesser]["is_ready"]:
                return False, "Você já está pronto."
            self.pending_guesses[target].append((guesser, guess_word))
            self.guesses_this_turn.add(guesser)
        try:
            with Pyro5.api.Proxy(self.clients[target]) as proxy:
                proxy.request_judgment(guesser, guess_word)
        except Exception as e:
            with self._lock:
                pending = self.pending_guesses.get(target, [])
                found = next(
                    (
                        p
                        for p in pending
                        if p[0] == guesser and p[1] == guess_word
                    ),
                    None,
                )
                if found:
                    pending.remove(found)
                self.guesses_this_turn.discard(guesser)
            return False, f"Falha ao enviar: {e}"
        return True, "Palpite enviado para julgamento."

    def judge_guess(self, judge_player, guesser, is_correct):
        should_finish_action_phase = False
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Apenas na ACTION_PHASE."
            pending = self.pending_guesses.get(judge_player, [])
            found = next((p for p in pending if p[0] == guesser), None)
            if not found:
                return False, "Nenhum palpite pendente."
            guess_word = found[1]
            self.pending_guesses[judge_player].remove(found)
            if is_correct:
                ScoreCalculator.apply_correct_guess(
                    self.player_states, judge_player, guesser
                )
                self.player_states[judge_player]["guessers"].append(guesser)
            else:
                self.player_states[guesser]["score"] -= 5
                self.failed_guesses[(guesser, judge_player)] = True
            should_finish_action_phase = self._should_finish_action_phase_locked()

        self._broadcast_scores()
        self._broadcast_event(
            "guess_result", guesser, judge_player, guess_word, is_correct
        )

        with self._lock:
            all_players = set(self.player_states.keys())
            guessers_set = {
                g for s in self.player_states.values() for g in s["guessers"]
            }
            if all_players == guessers_set:
                self._calculate_scores_and_end_game()
                return True, "Todos adivinharam — jogo encerrado!"

        if should_finish_action_phase:
            self._finish_action_phase()

        return True, "Julgamento registrado."

    def player_ready(self, player):
        should_finish_action_phase = False
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False, "Apenas na ACTION_PHASE."
            if self.player_states[player]["is_ready"]:
                return False, "Voce ja esta pronto."
            self.player_states[player]["is_ready"] = True
            self.broadcast_chat("Sistema", f"'{player}' esta PRONTO.")
            self._broadcast_scores()
            should_finish_action_phase = self._should_finish_action_phase_locked()

        if should_finish_action_phase:
            self._finish_action_phase()
        elif self._all_ready_with_pending_guesses():
            self._broadcast_event(
                "phase_changed",
                "ACTION_PHASE",
                "Todos estao prontos. Aguardando julgamentos de palpites pendentes.",
            )
        return True, "Turno encerrado."

    def _pending_guess_count_locked(self):
        return sum(len(pending) for pending in self.pending_guesses.values())

    def _should_finish_action_phase_locked(self):
        if self.phase != "ACTION_PHASE":
            return False
        all_ready = all(s["is_ready"] for s in self.player_states.values())
        return all_ready and self._pending_guess_count_locked() == 0

    def _all_ready_with_pending_guesses(self):
        with self._lock:
            if self.phase != "ACTION_PHASE":
                return False
            all_ready = all(s["is_ready"] for s in self.player_states.values())
            return all_ready and self._pending_guess_count_locked() > 0

    def _score_round_if_needed_locked(self):
        if self.round_scored:
            return
        self.player_states = ScoreCalculator.calculate_round_end(self.player_states)
        self.round_scored = True

    def _finish_action_phase(self):
        with self._lock:
            if not self._should_finish_action_phase_locked():
                return

            if self.turn_count < MAX_TURNS:
                self.turn_count += 1
                for name in self.player_states:
                    self.player_states[name].update(
                        {
                            "is_ready": False,
                            "public_hint": None,
                            "has_traded": False,
                            "has_spied": False,
                        }
                    )
                self.pending_trades.clear()
                self.trade_history.clear()
                self.failed_guesses.clear()
                self.guesses_this_turn.clear()
                self.pending_guesses = {name: [] for name in self.player_states}
                self.phase = "WAITING_HINTS"
                next_phase = "WAITING_HINTS"
                message = (
                    f"Turno {self.turn_count}/{MAX_TURNS} iniciado! "
                    "Mandem novas dicas."
                )
            else:
                self._score_round_if_needed_locked()
                self.phase = "VOTE_CONTINUE"
                next_phase = "VOTE_CONTINUE"
                message = (
                    "Rodada concluida e pontuada! "
                    "Votem para continuar com novos objetos ou encerrar."
                )

        self._broadcast_scores()
        self._broadcast_event("phase_changed", next_phase, message)

    def vote_continue(self, player, wants_continue):
        action = None
        with self._lock:
            if self.phase != "VOTE_CONTINUE":
                return False, "Apenas na fase VOTE_CONTINUE."
            self.continue_votes[player] = wants_continue
            if len(self.continue_votes) < len(self.player_states):
                return True, "Voto registrado."

            votes_for = sum(1 for v in self.continue_votes.values() if v)
            if votes_for > len(self.player_states) / 2:
                action = "next_round"
                self.phase = "WAITING_HINTS"
            else:
                action = "end_game"

        if action == "next_round":
            with self._lock:
                self._start_round()
        elif action == "end_game":
            self._calculate_scores_and_end_game()
        return True, "Voto registrado."

    def _calculate_scores_and_end_game(self):
        with self._lock:
            if self.phase == "END_GAME":
                return
            self._score_round_if_needed_locked()
            self.phase = "END_GAME"

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
                return False, "Apenas no fim do jogo."
            self.restart_votes.add(player)
            if len(self.restart_votes) >= len(self.clients):
                self.restart_votes.clear()
                self.phase = "LOBBY"
                self._broadcast_event(
                    "phase_changed", "LOBBY", "Todos votaram! De volta ao lobby."
                )
        return True, "Voto computado."


def main():
    daemon = Pyro5.api.Daemon(host=SERVER_HOST, port=SERVER_PORT)
    uri = daemon.register(GameServer, objectId="GameServer")
    print(f"[Servidor] Rodando em: {uri}")
    daemon.requestLoop()


if __name__ == "__main__":
    main()
