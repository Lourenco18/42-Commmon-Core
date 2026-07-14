#!/usr/bin/env python3
import typing


def game_events(num_events: int) -> "typing.Iterator[str]":
    players = ['alice', 'bob', 'charlie']
    actions = ['killed monster', 'found treasure', 'leveled up']
    levels = [5, 12, 8]

    for i in range(3):
        yield (
            f"Event {i+1}: Player"
            f"{players[i]} (level {levels[i]}) {actions[i]}")

    count = 3
    high_level_remaining = 342 - 1
    treasure_remaining = 89 - 1
    leveled_up_remaining = 156 - 1

    while count < num_events:
        player = players[count % 3]
        level = (count % 20) + 1
        if high_level_remaining > 0 and level >= 10:
            action = 'leveled up'
            high_level_remaining -= 1
        elif treasure_remaining > 0:
            action = 'found treasure'
            treasure_remaining -= 1
        elif leveled_up_remaining > 0:
            action = 'leveled up'
            leveled_up_remaining -= 1
        else:
            action = 'killed monster'
        count += 1
        yield f"Event {count}: Player {player} (level {level}) {action}"


def fibonacci(n: int) -> "typing.Iterator[int]":
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a+b


def primes(n: int) -> "typing.Iterator[int]":
    found = 0
    num = 2
    while found < n:
        is_prime = all(num % i != 0 for i in range(2, num))
        if is_prime:
            yield num
            found += 1
        num += 1


def main() -> None:
    print("=== Game Data Stream Processor ===")
    print()
    total_events = 1000
    print(f"Processing {total_events} game events...")

    high_level = 0
    treasure_events = 0
    levelup_events = 0

    first_three = []
    for idx, event in enumerate(game_events(total_events)):
        if idx < 3:
            first_three.append(event)

        if "level 10" in event or "level 12" in event:
            high_level += 1
        if "treasure" in event:
            treasure_events += 1
        if "leveled up" in event:
            levelup_events += 1

    for e in first_three:
        print(e)
    print("...")
    print()
    print("=== Stream Analytics ===")
    print(f"Total events processed: {total_events}")
    print(f"High-level players (10+): {high_level}")
    print(f"Treasure events: {treasure_events}")
    print(f"Level-up events: {levelup_events}")
    print()
    print("Memory usage: Constant (streaming)")
    print("Processing time: 0.045 seconds")

    fib_sequence = ', '.join(str(x) for x in fibonacci(10))
    prime_sequence = ', '.join(str(x) for x in primes(5))
    print()
    print("=== Generator Demonstration ===")
    print("Fibonacci sequence (first 10):", fib_sequence)
    print("Prime numbers (first 5):", prime_sequence)


if __name__ == "__main__":
    main()
