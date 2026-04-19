import functools
import operator
from typing import Callable


def spell_reducer(spells: list[int], operation: str) -> int:
    ops = {
        'add': operator.add,
        'multiply': operator.mul,
        'max': lambda a, b: a if a > b else b,
        'min': lambda a, b: a if a < b else b,
    }
    return functools.reduce(ops[operation], spells)


def partial_enchanter(base_enchantment: Callable) -> dict[str, Callable]:
    return {
        'fire_enchant': functools.partial(
            base_enchantment, power=50, element='fire'
        ),
        'ice_enchant': functools.partial(
            base_enchantment, power=50, element='ice'
        ),
        'lightning_enchant': functools.partial(
            base_enchantment, power=50, element='lightning'
        ),
    }


@functools.lru_cache(maxsize=None)
def memoized_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return memoized_fibonacci(n - 1) + memoized_fibonacci(n - 2)


def spell_dispatcher() -> Callable:
    @functools.singledispatch
    def cast(spell):
        return f"Unknown spell type: {spell}"

    @cast.register(int)
    def _(spell: int) -> str:
        return f"Damage spell dealing {spell} points"

    @cast.register(str)
    def _(spell: str) -> str:
        return f"Enchantment: {spell}"

    @cast.register(list)
    def _(spell: list) -> str:
        results = [f"Cast {s}" for s in spell]
        return f"Multi-cast: {', '.join(results)}"

    return cast


def main() -> None:
    spells = [10, 20, 30, 40]

    print("Testing spell reducer...")
    print(f"Sum: {spell_reducer(spells, 'add')}")
    print(f"Product: {spell_reducer(spells, 'multiply')}")
    print(f"Max: {spell_reducer(spells, 'max')}")

    print("\nTesting memoized fibonacci...")
    print(f"Fib(10): {memoized_fibonacci(10)}")
    print(f"Fib(15): {memoized_fibonacci(15)}")

    print("\nTesting partial enchanter...")

    def base_enchantment(item: str, power: int, element: str) -> str:
        return f"{element} enchantment on {item} with {power} power"

    enchants = partial_enchanter(base_enchantment)
    print(enchants['fire_enchant']('Sword'))
    print(enchants['ice_enchant']('Shield'))
    print(enchants['lightning_enchant']('Staff'))


if __name__ == "__main__":
    main()
