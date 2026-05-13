from ex0.Card import Card
from ex2.Combatable import Combatable
from ex2.Magical import Magical


class EliteCard(Card, Combatable, Magical):

    def __init__(
        self,
        name: str,
        cost: int,
        rarity: str,
        attack_power: int,
        defense: int,
        mana_pool: int,
    ) -> None:
        super().__init__(name, cost, rarity)
        self.attack_power = attack_power
        self.defense = defense
        self.mana_pool = mana_pool

    def get_card_info(self) -> dict:
        info = super().get_card_info()
        info['type'] = 'Elite'
        info['attack_power'] = self.attack_power
        info['defense'] = self.defense
        info['mana_pool'] = self.mana_pool
        return info

    def play(self, game_state: dict) -> dict:
        return {
            'card_played': self.name,
            'mana_used': self.cost,
            'effect': ("Elite card enters battlefield with "
                       "combat and magic abilities"),
        }

    def attack(self, target) -> dict:
        target_name = target.name if hasattr(target, 'name') else str(target)
        return {
            'attacker': self.name,
            'target': target_name,
            'damage': self.attack_power,
            'combat_type': 'melee',
        }

    def defend(self, incoming_damage: int) -> dict:
        damage_blocked = min(self.defense, incoming_damage)
        damage_taken = incoming_damage - damage_blocked
        return {
            'defender': self.name,
            'damage_taken': damage_taken,
            'damage_blocked': damage_blocked,
            'still_alive': True,
        }

    def get_combat_stats(self) -> dict:
        return {
            'attack_power': self.attack_power,
            'defense': self.defense,
        }

    def cast_spell(self, spell_name: str, targets: list) -> dict:
        mana_cost = len(targets) + 2
        self.mana_pool -= mana_cost
        target_names = [t.name if hasattr(t, 'name') else
                        str(t) for t in targets]
        return {
            'caster': self.name,
            'spell': spell_name,
            'targets': target_names,
            'mana_used': mana_cost,
        }

    def channel_mana(self, amount: int) -> dict:
        self.mana_pool += amount
        return {
            'channeled': amount,
            'total_mana': self.mana_pool,
        }

    def get_magic_stats(self) -> dict:
        return {
            'mana_pool': self.mana_pool,
        }
