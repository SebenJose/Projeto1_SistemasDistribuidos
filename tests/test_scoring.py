import copy
import unittest
from unittest.mock import patch

from score import ScoreCalculator
from server import GameServer


def player(score=0, guessers=None, object_name="Objeto"):
    return {
        "score": score,
        "object": object_name,
        "guessers": list(guessers or []),
        "is_ready": False,
        "public_hint": None,
        "has_traded": False,
        "has_spied": False,
    }


class ScoreCalculatorTest(unittest.TestCase):
    def test_correct_guess_points_first_and_later_guessers(self):
        states = {
            "jose": player(),
            "caio": player(),
            "pepe": player(),
        }

        ScoreCalculator.apply_correct_guess(states, "jose", "caio")
        states["jose"]["guessers"].append("caio")
        ScoreCalculator.apply_correct_guess(states, "jose", "pepe")
        states["jose"]["guessers"].append("pepe")

        self.assertEqual(states["caio"]["score"], 20)
        self.assertEqual(states["pepe"]["score"], 10)
        self.assertEqual(states["jose"]["score"], 0)

    def test_round_end_scores_owner_when_exactly_one_player_guessed_object(self):
        states = {
            "jose": player(guessers=["caio"]),
            "caio": player(),
            "pepe": player(),
        }

        ScoreCalculator.calculate_round_end(states)

        self.assertEqual(states["jose"]["score"], 15)
        self.assertEqual(states["caio"]["score"], 10)
        self.assertEqual(states["pepe"]["score"], 0)

    def test_round_end_penalizes_owner_when_all_other_players_guessed_object(self):
        states = {
            "jose": player(guessers=["caio", "pepe"]),
            "caio": player(),
            "pepe": player(),
        }

        ScoreCalculator.calculate_round_end(states)

        self.assertEqual(states["jose"]["score"], -10)
        self.assertEqual(states["caio"]["score"], 0)
        self.assertEqual(states["pepe"]["score"], 0)

    def test_round_end_with_two_players_does_not_score_owner_exclusivity(self):
        states = {
            "jose": player(guessers=["caio"]),
            "caio": player(),
        }

        ScoreCalculator.calculate_round_end(states)

        self.assertEqual(states["jose"]["score"], 0)
        self.assertEqual(states["caio"]["score"], 10)

    def test_round_end_scores_owner_for_more_than_one_but_not_all_guessers(self):
        states = {
            "jose": player(guessers=["caio", "pepe"]),
            "caio": player(),
            "pepe": player(),
            "ana": player(),
        }

        ScoreCalculator.calculate_round_end(states)

        self.assertEqual(states["jose"]["score"], 8)

    def test_user_reported_shape_matches_current_rules(self):
        states = {
            "jose": player(score=20, guessers=["caio", "pepe"]),
            "caio": player(score=25, guessers=[]),
            "pepe": player(score=10, guessers=["jose"]),
        }

        ScoreCalculator.calculate_round_end(states)

        self.assertEqual(states["jose"]["score"], 20)
        self.assertEqual(states["caio"]["score"], 25)
        self.assertEqual(states["pepe"]["score"], 25)

    def test_round_end_is_idempotent_when_server_closes_round_twice(self):
        server = GameServer()
        server.player_states = {
            "jose": player(guessers=["caio"]),
            "caio": player(),
            "pepe": player(),
        }

        server._score_round_if_needed_locked()
        first_result = copy.deepcopy(server.player_states)
        server._score_round_if_needed_locked()

        self.assertEqual(server.player_states, first_result)


class GameServerPenaltyTest(unittest.TestCase):
    def test_wrong_guess_subtracts_points_and_records_failed_pair(self):
        server = GameServer()
        server.phase = "ACTION_PHASE"
        server.player_states = {
            "jose": player(score=0),
            "caio": player(score=20),
        }
        server.pending_guesses = {"jose": [("caio", "bicicleta")], "caio": []}

        ok, _ = server.judge_guess("jose", "caio", False)

        self.assertTrue(ok)
        self.assertEqual(server.player_states["caio"]["score"], 15)
        self.assertIn(("caio", "jose"), server.failed_guesses)

    def test_spy_failure_subtracts_points(self):
        server = GameServer()
        server.phase = "ACTION_PHASE"
        server.player_states = {
            "jose": player(),
            "caio": player(),
            "pepe": player(score=10),
        }
        server.trade_history[frozenset(["jose", "caio"])] = ("rapido", "vermelho")

        with patch("server.random.random", return_value=0.10):
            ok, msg = server.spy_on_trade("pepe", "jose", "caio")

        self.assertTrue(ok)
        self.assertIn("perdeu 10 pontos", msg)
        self.assertEqual(server.player_states["pepe"]["score"], 0)

    def test_spy_success_adds_points(self):
        server = GameServer()
        server.phase = "ACTION_PHASE"
        server.player_states = {
            "jose": player(),
            "caio": player(),
            "pepe": player(score=10),
        }
        server.trade_history[frozenset(["jose", "caio"])] = ("rapido", "vermelho")

        with patch("server.random.random", return_value=0.90):
            ok, msg = server.spy_on_trade("pepe", "jose", "caio")

        self.assertTrue(ok)
        self.assertIn("SUCESSO", msg)
        self.assertEqual(server.player_states["pepe"]["score"], 15)


class GameServerRoundFlowTest(unittest.TestCase):
    def test_private_trade_is_once_per_object_not_reset_each_turn(self):
        server = GameServer()
        server.phase = "ACTION_PHASE"
        server.turn_count = 1
        server.player_states = {
            "jose": player(),
            "caio": player(),
        }
        server.player_states["jose"]["has_traded"] = True
        server.player_states["caio"]["has_traded"] = True
        server.player_states["jose"]["is_ready"] = True
        server.player_states["caio"]["is_ready"] = True
        server.pending_guesses = {"jose": [], "caio": []}

        server._finish_action_phase()

        self.assertEqual(server.phase, "WAITING_HINTS")
        self.assertTrue(server.player_states["jose"]["has_traded"])
        self.assertTrue(server.player_states["caio"]["has_traded"])

    def test_all_players_guessing_does_not_end_game_automatically(self):
        server = GameServer()
        server.phase = "ACTION_PHASE"
        server.player_states = {
            "jose": player(),
            "caio": player(),
        }
        server.pending_guesses = {
            "jose": [("caio", "objeto")],
            "caio": [("jose", "objeto")],
        }

        ok_jose, _ = server.judge_guess("jose", "caio", True)
        ok_caio, _ = server.judge_guess("caio", "jose", True)

        self.assertTrue(ok_jose)
        self.assertTrue(ok_caio)
        self.assertEqual(server.phase, "ACTION_PHASE")


class GameServerObjectFilterTest(unittest.TestCase):
    def test_chat_blocks_own_object_name_and_synonyms(self):
        server = GameServer()
        server.player_states = {
            "jose": player(object_name="Maca"),
            "caio": player(object_name="Carro"),
        }

        ok, msg = server.send_chat_message("jose", "meu objeto parece uma maçã")

        self.assertFalse(ok)
        self.assertIn("bloqueada", msg)
        self.assertEqual(server.chat_system.history, [])

        ok, msg = server.send_chat_message("jose", "parece uma apple")

        self.assertFalse(ok)
        self.assertIn("bloqueada", msg)
        self.assertEqual(server.chat_system.history, [])

    def test_chat_allows_other_players_object_words(self):
        server = GameServer()
        server.player_states = {
            "jose": player(object_name="Maca"),
            "caio": player(object_name="Carro"),
        }

        ok, _ = server.send_chat_message("jose", "acho que alguem tem carro")

        self.assertTrue(ok)
        self.assertEqual(server.chat_system.history, [("jose", "acho que alguem tem carro")])

    def test_public_hint_blocks_own_object_synonym(self):
        server = GameServer()
        server.phase = "WAITING_HINTS"
        server.player_states = {"jose": player(object_name="Bicicleta")}

        ok, msg = server.send_public_hint("jose", "bike")

        self.assertFalse(ok)
        self.assertIn("bloqueada", msg)
        self.assertIsNone(server.player_states["jose"]["public_hint"])

    def test_trade_request_blocks_sender_own_object_synonym(self):
        server = GameServer()
        server.phase = "ACTION_PHASE"
        server.player_states = {
            "jose": player(object_name="Computador"),
            "caio": player(object_name="Carro"),
        }

        ok, msg = server.request_trade("jose", "caio", "notebook")

        self.assertFalse(ok)
        self.assertIn("bloqueada", msg)
        self.assertEqual(server.pending_trades, {})

    def test_trade_response_blocks_target_own_object_synonym_without_dropping_request(self):
        server = GameServer()
        server.phase = "ACTION_PHASE"
        server.player_states = {
            "jose": player(object_name="Computador"),
            "caio": player(object_name="Cachorro"),
        }
        server.pending_trades["caio"] = {"sender": "jose", "hint": "teclado"}

        ok, msg = server.respond_trade("caio", "jose", True, "dog")

        self.assertFalse(ok)
        self.assertIn("bloqueada", msg)
        self.assertIn("caio", server.pending_trades)


if __name__ == "__main__":
    unittest.main()
