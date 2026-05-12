import time
import threading
import Pyro5.api
from server import GameServer

# === CLASSES MOCK PARA O CLIENTE ===
@Pyro5.api.expose
class MockClient:
    def __init__(self, name):
        self.name = name
        self.secret_object = None
        self.phase = None
        self.events = []

    @Pyro5.api.oneway
    def phase_changed(self, new_phase, message):
        self.phase = new_phase
        self.events.append(f"PHASE:{new_phase}")

    @Pyro5.api.oneway
    def game_started(self, secret_object, img_base64=""):
        self.secret_object = secret_object
        self.img_base64 = img_base64

    @Pyro5.api.oneway
    def receive_public_hint(self, sender, hint): pass
    @Pyro5.api.oneway
    def receive_chat_message(self, sender, message): pass
    @Pyro5.api.oneway
    def receive_trade_request(self, sender): pass
    @Pyro5.api.oneway
    def trade_rejected(self, partner): pass
    @Pyro5.api.oneway
    def trade_completed(self, partner, partner_hint): pass
    @Pyro5.api.oneway
    def trade_occurred_public(self, player_a, player_b): pass
    @Pyro5.api.oneway
    def spy_result(self, spy_name, player_a, player_b, success): pass
    @Pyro5.api.oneway
    def guess_result(self, guesser, target, guess_word, is_correct): pass
    @Pyro5.api.oneway
    def request_judgment(self, guesser, guess_word): pass

# === FUNÇÕES DE RUNNER ===
def run_server(daemon):
    daemon.requestLoop()

def run_client_daemon(daemon):
    daemon.requestLoop()

def run_tests():
    print("--- INICIANDO BANCA DE TESTES AUTOMATIZADA (FASE 3) ---")
    
    server_daemon = Pyro5.api.Daemon(port=9099)
    server_obj = GameServer()
    server_uri = server_daemon.register(server_obj, objectId="GameServerTest")
    threading.Thread(target=run_server, args=(server_daemon,), daemon=True).start()
    
    client_daemon = Pyro5.api.Daemon()
    threading.Thread(target=run_client_daemon, args=(client_daemon,), daemon=True).start()
    
    p_alice = MockClient("Alice")
    p_bob = MockClient("Bob")
    p_charlie = MockClient("Charlie")
    
    uri_alice = client_daemon.register(p_alice)
    uri_bob = client_daemon.register(p_bob)
    uri_charlie = client_daemon.register(p_charlie)
    
    server = Pyro5.api.Proxy(server_uri)
    
    # 1: Registro
    print("Teste 1: Registrando Clientes...")
    server.register_client("Alice", uri_alice)
    server.register_client("Bob", uri_bob)
    server.register_client("Charlie", uri_charlie)
    time.sleep(0.5)
    
    # 2: Iniciando
    server.start_game("Alice")
    time.sleep(0.5)
    print(f"Objetos: Alice={p_alice.secret_object}, Bob={p_bob.secret_object}, Charlie={p_charlie.secret_object}")
    
    # Vamos injetar objetos fixos para o teste
    server_obj.player_states["Alice"]["object"] = "Cachorro"
    server_obj.player_states["Bob"]["object"] = "Carro"
    server_obj.player_states["Charlie"]["object"] = "Livro"

    assert len(p_alice.img_base64) > 0, "Imagem não foi enviada para Alice!"

    # 3: Turno 1 - Dicas
    server.send_public_hint("Alice", "Pêlo")
    server.send_public_hint("Bob", "Roda")
    server.send_public_hint("Charlie", "Páginas")
    time.sleep(0.5)
    assert server_obj.phase == "ACTION_PHASE"
    
    # 4: Adivinhações (Múltiplas pessoas adivinhando com julgamento)
    print("Teste 4: Adivinhações e Arbitração...")
    # Alice adivinha errado o do Bob
    server.guess_object("Alice", "Bob", "Barco")
    # Bob deve julgar negativo
    server.judge_guess("Bob", "Alice", False)
    
    # Alice adivinha certo o do Bob
    server.guess_object("Alice", "Bob", "Carro")
    # Bob julga afirmativo
    server.judge_guess("Bob", "Alice", True)
    assert "Alice" in server_obj.player_states["Bob"]["guessers"]
    
    # Charlie também adivinha certo o do Bob
    server.guess_object("Charlie", "Bob", "Carro")
    server.judge_guess("Bob", "Charlie", True)
    assert "Charlie" in server_obj.player_states["Bob"]["guessers"]
    
    # Bob tenta adivinhar Charlie (Livro)
    server.guess_object("Bob", "Charlie", "Livro")
    server.judge_guess("Charlie", "Bob", True)
    assert "Bob" in server_obj.player_states["Charlie"]["guessers"]
    
    # Teste de Troca e Espionagem
    server.request_trade("Alice", "Charlie", "dica1")
    server.respond_trade("Charlie", "Alice", True, "dica2")
    assert server_obj.player_states["Alice"]["has_traded"] == True
    server.spy_on_trade("Bob", "Alice", "Charlie")

    # 5: Fim do Turno 1
    print("Teste 5: Comando /pronto e Múltiplos Turnos...")
    server.player_ready("Alice")
    server.player_ready("Bob")
    assert server_obj.phase == "ACTION_PHASE"
    server.player_ready("Charlie")
    time.sleep(0.5)
    assert server_obj.phase == "WAITING_HINTS"
    assert server_obj.turn_count == 2
    
    # Rodar os próximos turnos para acabar o jogo
    server.send_public_hint("Alice", "x")
    server.send_public_hint("Bob", "y")
    server.send_public_hint("Charlie", "z")
    server.player_ready("Alice")
    server.player_ready("Bob")
    server.player_ready("Charlie")
    time.sleep(0.5)
    assert server_obj.turn_count == 3
    
    server.send_public_hint("Alice", "a")
    server.send_public_hint("Bob", "b")
    server.send_public_hint("Charlie", "c")
    server.player_ready("Alice")
    server.player_ready("Bob")
    server.player_ready("Charlie")
    time.sleep(0.5)
    assert server_obj.phase == "END_GAME"

    print("✓ Toda a matemática de Arbitração passou perfeitamente e os Turnos funcionaram!")
    print("\n--- TODOS OS TESTES PASSARAM COM SUCESSO! ---")

if __name__ == "__main__":
    run_tests()
