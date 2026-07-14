from ex3.GameStrategy import GameStrategy
from ex0.CreatureCard import CreatureCard


class AggressiveStrategy(GameStrategy):

    def get_strategy_name(self) -> str:
        return "AggressiveStrategy"

    def prioritize_targets(self, available_targets: list) -> list:
        prioritized = [t for t in available_targets if 'Player' in str(t)]
        others = [t for t in available_targets if 'Player' not in str(t)]
        return prioritized + others

    def execute_turn(self, hand: list, battlefield: list) -> dict:
        available_mana = 6
        mana_used = 0
        cards_played = []
        damage_dealt = 0

        affordable = sorted(
            [c for c in hand if c.cost <= available_mana],
            key=lambda c: c.cost
        )

        for card in affordable:
            if mana_used + card.cost <= available_mana:
                cards_played.append(card.name)
                mana_used += card.cost
                if isinstance(card, CreatureCard):
                    damage_dealt += card.attack
                else:
                    damage_dealt += card.cost

        targets = self.prioritize_targets(['Enemy Player'])

        return {
            'strategy': self.get_strategy_name(),
            'actions': {
                'cards_played': cards_played,
                'mana_used': mana_used,
                'targets_attacked': targets,
                'damage_dealt': damage_dealt,
            }
        }
