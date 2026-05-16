import Pyro5.api


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
        self.msg_queue.put(("notice", "success", "Partida iniciada. Boa sorte!"))
        self.msg_queue.put(("notice", "system", f"Seu objeto secreto: {secret_object}"))
        if img_base64:
            self.msg_queue.put(("image", img_base64))

    @Pyro5.api.oneway
    def receive_public_hint(self, sender, hint):
        self.msg_queue.put(("hint", f"Dica pública | {sender}: {hint}", "hint"))

    @Pyro5.api.oneway
    def receive_trade_request(self, sender):
        self.msg_queue.put(("trade_request", sender))

    @Pyro5.api.oneway
    def trade_rejected(self, partner):
        self.msg_queue.put(("notice", "warning", f"{partner} recusou sua troca privada."))

    @Pyro5.api.oneway
    def trade_completed(self, partner, partner_hint):
        self.msg_queue.put(
            (
                "hint",
                f"Dica privada | {partner}: {partner_hint}",
                "private",
            )
        )

    @Pyro5.api.oneway
    def trade_occurred_public(self, player_a, player_b):
        self.msg_queue.put(
            ("notice", "trade", f"{player_a} e {player_b} realizaram uma troca privada.")
        )
        self.msg_queue.put(("trade_notification", player_a, player_b))

    @Pyro5.api.oneway
    def spy_result(self, spy_name, player_a, player_b, success):
        if success:
            self.msg_queue.put(
                (
                    "hint",
                    f"Espionagem | {spy_name} viu a troca de {player_a} e {player_b}.",
                    "spy",
                )
            )
        else:
            self.msg_queue.put(
                (
                    "notice",
                    "danger",
                    f"{spy_name} foi pego tentando espiar {player_a} e {player_b}. Perdeu 10 pontos.",
                )
            )

    @Pyro5.api.oneway
    def guess_result(self, guesser, target, guess_word, is_correct):
        if is_correct:
            self.msg_queue.put(
                (
                    "notice",
                    "success",
                    f"{guesser} acertou o objeto de {target}: {guess_word}.",
                )
            )
        else:
            self.msg_queue.put(
                (
                    "notice",
                    "warning",
                    f"{guesser} errou o palpite para {target}: {guess_word}.",
                )
            )

    @Pyro5.api.oneway
    def request_judgment(self, guesser, guess_word):
        self.msg_queue.put(("judgment", guesser, guess_word))

    @Pyro5.api.oneway
    def scores_updated(self, scores_data):
        self.msg_queue.put(("scores", scores_data))
