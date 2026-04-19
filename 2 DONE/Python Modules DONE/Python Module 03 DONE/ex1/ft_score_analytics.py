#!/usr/bin/env python3
import sys


def main() -> None:
    print("=== Player Score Analytics ===")

    args = sys.argv[1:]

    if len(args) == 0:
        print(
                "No scores provided. Usage: python3 ft_score_analytics.py "
                "<score1> <score2> ...")
        return

    scores = []
    for arg in args:
        try:
            score = int(arg)
            scores.append(score)
        except ValueError as e:
            print(f"Invalid input '{arg}' skipped. Error: {e}")

    if len(scores) == 0:
        print("No valid scores to process.")
        return

    total_score = sum(scores)
    high_score = max(scores)
    low_score = min(scores)
    score_range = high_score - low_score
    average_score = total_score / len(scores)

    print(f"Scores processed: {scores}")
    print(f"Total players: {len(scores)}")
    print(f"Total score: {total_score}")
    print(f"Average score: {average_score}")
    print(f"High score: {high_score}")
    print(f"Low score: {low_score}")
    print(f"Score range: {score_range}")


if __name__ == "__main__":
    main()
