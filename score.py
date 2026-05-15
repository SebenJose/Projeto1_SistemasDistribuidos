class ScoreCalculator:
    @staticmethod
    def calculate_round_end(player_states):
        total_players = len(player_states)
        for target, state in player_states.items():
            guessers = state["guessers"]
            n = len(guessers)

            if n > 0:
                # Bônus de rapidez para o primeiro que acertou
                first_guesser = guessers[0]
                player_states[first_guesser]["score"] += 20 + (10 if n == 1 else 0)

                # Pontos normais para os demais que acertaram
                for g in guessers[1:]:
                    player_states[g]["score"] += 10

            # Bônus ou penalidade de exclusividade para o dono
            if n == 1:
                state["score"] += 30
            elif 1 < n < total_players - 1:
                state["score"] += 15
            elif n >= total_players - 1 and total_players > 2:
                state["score"] -= 20

        return player_states
