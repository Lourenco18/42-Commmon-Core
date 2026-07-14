from ex0.Card import Card


class CreatureCard(Card):

    def __init__(self, name: str, cost: int,
                 rarity: str, attack: int, health: int) -> None:
        if not isinstance(attack, int) or attack <= 0:
            raise ValueError("attack must be a positive integer")
        if not isinstance(health, int) or health <= 0:
            raise ValueError("health must be a positive integer")
        super().__init__(name, cost, rarity)
        self.attack = attack
        self.health = health

    def get_card_info(self) -> dict:
        info = super().get_card_info()
        info['type'] = 'Creature'
        info['attack'] = self.attack
        info['health'] = self.health
        return info

    def play(self, game_state: dict) -> dict:
        return {
            'card_played': self.name,
            'mana_used': self.cost,
            'effect': 'Creature summoned to battlefield',
        }

    def attack_target(self, target) -> dict:

        target_name = target.name if hasattr(target, 'name') else str(target)
        return {
            'attacker': self.name,
            'target': target_name,
            'damage_dealt': self.attack,
            'combat_resolved': True,
        }
