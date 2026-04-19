from ex0.CreatureCard import CreatureCard
from ex1.SpellCard import SpellCard
from ex1.ArtifactCard import ArtifactCard
from ex3.CardFactory import CardFactory
from ex0.Card import Card


class FantasyCardFactory(CardFactory):

    def __init__(self) -> None:
        self._supported = {
            'creatures': ['dragon', 'goblin'],
            'spells':    ['fireball'],
            'artifacts': ['mana_ring'],
        }

    def get_supported_types(self) -> dict:
        return self._supported

    def create_creature(self, name_or_power: str | int | None = None) -> Card:
        kind = str(name_or_power).lower() if name_or_power else 'dragon'
        if kind == 'goblin':
            return CreatureCard("Goblin Warrior", cost=2, rarity="Common",
                                attack=2, health=1)
        return CreatureCard("Fire Dragon", cost=5, rarity="Legendary",
                            attack=7, health=5)

    def create_spell(self, name_or_power: str | int | None = None) -> Card:
        return SpellCard("Lightning Bolt", cost=3, rarity="Uncommon",
                         effect_type="damage")

    def create_artifact(self, name_or_power: str | int | None = None) -> Card:
        return ArtifactCard("Mana Ring", cost=2, rarity="Rare", durability=5,
                            effect="+1 mana per turn")

    def create_themed_deck(self, size: int) -> dict:
        cards = []
        for i in range(size):
            if i % 3 == 0:
                cards.append(self.create_creature('dragon'))
            elif i % 3 == 1:
                cards.append(self.create_spell())
            else:
                cards.append(self.create_artifact())
        return {'factory': 'FantasyCardFactory', 'size': len(cards),
                'cards': cards}
