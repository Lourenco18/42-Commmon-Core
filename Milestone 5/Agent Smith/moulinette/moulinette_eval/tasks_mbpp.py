"""A small, self-contained set of MBPP-style tasks.

The real MBPP dataset is normally pulled from HuggingFace; since this
evaluation harness must run fully offline (no dataset-hub access required to
grade the framework itself), five hand-written tasks in the same spirit and
schema are embedded here. Swap in the real dataset by replacing this module
with a HuggingFace `datasets.load_dataset("mbpp")` loader if you have network
access to huggingface.co -- the rest of the pipeline (StepMetrics, agent CLI,
validate command) is unaffected either way.
"""
from __future__ import annotations

TASKS = [
    {
        "task_id": 1,
        "task_definition": "Write a function to find the sum of all numbers in a list.",
        "function_definition": "def sum_list(numbers: list) -> int:",
        "test_imports": [],
        "test_list": [
            "assert sum_list([1, 2, 3]) == 6",
            "assert sum_list([]) == 0",
            "assert sum_list([-1, 1, 10]) == 10",
        ],
    },
    {
        "task_id": 2,
        "task_definition": "Write a function to reverse a string.",
        "function_definition": "def reverse_string(s: str) -> str:",
        "test_imports": [],
        "test_list": [
            "assert reverse_string('hello') == 'olleh'",
            "assert reverse_string('') == ''",
            "assert reverse_string('a') == 'a'",
        ],
    },
    {
        "task_id": 3,
        "task_definition": "Write a function to check whether a given string is a palindrome.",
        "function_definition": "def is_palindrome(s: str) -> bool:",
        "test_imports": [],
        "test_list": [
            "assert is_palindrome('racecar') == True",
            "assert is_palindrome('hello') == False",
            "assert is_palindrome('') == True",
        ],
    },
    {
        "task_id": 4,
        "task_definition": "Write a function to find the maximum of three numbers.",
        "function_definition": "def max_of_three(a, b, c):",
        "test_imports": [],
        "test_list": [
            "assert max_of_three(1, 2, 3) == 3",
            "assert max_of_three(5, 2, 3) == 5",
            "assert max_of_three(-1, -2, -3) == -1",
        ],
    },
    {
        "task_id": 5,
        "task_definition": "Write a function to count the number of vowels in a string.",
        "function_definition": "def count_vowels(s: str) -> int:",
        "test_imports": [],
        "test_list": [
            "assert count_vowels('hello world') == 3",
            "assert count_vowels('xyz') == 0",
            "assert count_vowels('AEIOUaeiou') == 10",
        ],
    },
]
