from ex4.TournamentCard import TournamentCard


class TournamentPlatform:

    def __init__(self) -> None:
        self._cards: dict[str, TournamentCard] = {}
        self._matches: list[dict] = []

    def register_card(self, card: TournamentCard) -> str:

        short = card.name.lower().split()[-1]
        card_id = f"{short}_001"
        self._cards[card_id] = card
        return card_id

    def create_match(self, card1_id: str, card2_id: str) -> dict:
        card1 = self._cards[card1_id]
        card2 = self._cards[card2_id]

        score1 = card1.attack_power + card1.defense
        score2 = card2.attack_power + card2.defense
        if score1 >= score2:
            winner, loser, winner_id, loser_id = (card1, card2,
                                                  card1_id, card2_id)
        else:
            winner, loser, winner_id, loser_id = (card2, card1,
                                                  card2_id, card1_id)

        expected_winner = 1 / (1 + 10 ** ((loser.rating - winner.rating)
                                          / 400))
        delta = round(TournamentCard.K_FACTOR * (1 - expected_winner))

        winner.rating += delta
        loser.rating -= delta
        winner.update_wins(1)
        loser.update_losses(1)

        result = {
            'winner': winner_id,
            'loser': loser_id,
            'winner_rating': winner.rating,
            'loser_rating': loser.rating,
        }
        self._matches.append(result)
        return result

    def get_leaderboard(self) -> list:
        ranked = sorted(self._cards.items(), key=lambda kv: kv[1].rating,
                        reverse=True)
        return [
            {
                'rank': i + 1,
                'id': card_id,
                'name': card.name,
                'rating': card.rating,
                'record': f'{card.wins}-{card.losses}',
            }
            for i, (card_id, card) in enumerate(ranked)
        ]

    def generate_tournament_report(self) -> dict:
        ratings = [c.rating for c in self._cards.values()]
        avg_rating = round(sum(ratings) / len(ratings)) if ratings else 0
        return {
            'total_cards': len(self._cards),
            'matches_played': len(self._matches),
            'avg_rating': avg_rating,
            'platform_status': 'active',
        }
