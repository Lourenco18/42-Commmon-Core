from ex0.Card import Card
from ex2.Combatable import Combatable
from ex4.Rankable import Rankable


class TournamentCard(Card, Combatable, Rankable):

    BASE_RATING = 1200
    K_FACTOR = 32

    def __init__(
        self,
        name: str,
        cost: int,
        rarity: str,
        attack_power: int,
        defense: int,
    ) -> None:
        super().__init__(name, cost, rarity)
        self.attack_power = attack_power
        self.defense = defense
        self.wins = 0
        self.losses = 0
        self.rating = self.BASE_RATING

    def get_card_info(self) -> dict:
        info = super().get_card_info()
        info['type'] = 'TournamentCard'
        info['attack_power'] = self.attack_power
        info['defense'] = self.defense
        return info

    def play(self, game_state: dict) -> dict:
        return {
            'card_played': self.name,
            'mana_used': self.cost,
            'effect': 'Tournament card enters the arena',
        }

    def attack(self, target) -> dict:
        target_name = target.name if hasattr(target, 'name') else str(target)
        return {
            'attacker': self.name,
            'target': target_name,
            'damage': self.attack_power,
            'combat_type': 'tournament',
        }

    def defend(self, incoming_damage: int) -> dict:
        damage_blocked = min(self.defense, incoming_damage)
        damage_taken = incoming_damage - damage_blocked
        return {
            'defender': self.name,
            'damage_taken': damage_taken,
            'damage_blocked': damage_blocked,
            'still_alive': damage_taken < 100,
        }

    def get_combat_stats(self) -> dict:
        return {
            'attack_power': self.attack_power,
            'defense': self.defense,
        }

    def calculate_rating(self) -> int:
        return self.rating

    def update_wins(self, wins: int) -> None:
        self.wins += wins

    def update_losses(self, losses: int) -> None:
        self.losses += losses

    def get_rank_info(self) -> dict:
        return {
            'name': self.name,
            'rating': self.rating,
            'wins': self.wins,
            'losses': self.losses,
            'record': f'{self.wins}-{self.losses}',
        }

    def get_tournament_stats(self) -> dict:
        return {
            **self.get_card_info(),
            **self.get_combat_stats(),
            **self.get_rank_info(),
            'interfaces': ['Card', 'Combatable', 'Rankable'],
        }
