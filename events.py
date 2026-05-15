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
        self.msg_queue.put(
            (
                "log",
                f"\n*** O JOGO COMEÇOU! ***\n*** SEU OBJETO SECRETO É: [{secret_object}] ***",
            )
        )
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
        self.msg_queue.put(
            (
                "log",
                f"[TROCA CONCLUÍDA] A dica secreta de {partner} é: '{partner_hint}'",
            )
        )

    @Pyro5.api.oneway
    def trade_occurred_public(self, player_a, player_b):
        self.msg_queue.put(
            ("log", f"[ALERTA] {player_a} e {player_b} efetuaram uma troca privada!")
        )
        self.msg_queue.put(("trade_notification", player_a, player_b))

    @Pyro5.api.oneway
    def spy_result(self, spy_name, player_a, player_b, success):
        if success:
            self.msg_queue.put(
                (
                    "log",
                    f"[ESPIONAGEM] {spy_name} espiou a troca de {player_a} e {player_b} e saiu impune!",
                )
            )
        else:
            self.msg_queue.put(
                (
                    "log",
                    f"[ESPIONAGEM FALHOU] {spy_name} tentou espiar {player_a} e {player_b} e foi pego! Perdeu 10 pontos!",
                )
            )

    @Pyro5.api.oneway
    def guess_result(self, guesser, target, guess_word, is_correct):
        if is_correct:
            self.msg_queue.put(
                (
                    "log",
                    f"[PALPITE] {guesser} ACERTOU que o objeto de {target} era '{guess_word}'!",
                )
            )
        else:
            self.msg_queue.put(
                (
                    "log",
                    f"[PALPITE] {guesser} errou ao dizer que o objeto de {target} era '{guess_word}'.",
                )
            )
            self.msg_queue.put(
                (
                    "log",
                    f"[PALPITE] {guesser} errou ao dizer que o objeto de {target} era '{guess_word}'.",
                )
            )

    @Pyro5.api.oneway
    def request_judgment(self, guesser, guess_word):
        self.msg_queue.put(("judgment", guesser, guess_word))

    @Pyro5.api.oneway
    def scores_updated(self, scores_data):
        self.msg_queue.put(("scores", scores_data))
