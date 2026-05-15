class ScoreCalculator:
    FIRST_CORRECT_GUESS_POINTS = 20
    LATER_CORRECT_GUESS_POINTS = 10
    ONLY_GUESSER_BONUS = 10

    @classmethod
    def apply_correct_guess(cls, player_states, target, guesser):
        current_hits = len(player_states[target]["guessers"])
        if current_hits == 0:
            player_states[guesser]["score"] += cls.FIRST_CORRECT_GUESS_POINTS
        else:
            player_states[guesser]["score"] += cls.LATER_CORRECT_GUESS_POINTS

    @staticmethod
    def calculate_round_end(player_states):
        total_players = len(player_states)
        for target, state in player_states.items():
            guessers = state["guessers"]
            n = len(guessers)

            if n == 1:
                player_states[guessers[0]]["score"] += ScoreCalculator.ONLY_GUESSER_BONUS

            # Bônus ou penalidade de exclusividade para o dono
            if n == 1:
                state["score"] += 30
            elif 1 < n < total_players - 1:
                state["score"] += 15
            elif n >= total_players - 1 and total_players > 2:
                state["score"] -= 20

        return player_states
