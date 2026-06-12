import argparse
from typing import Any, List
from pathlib import Path
import json
from src.validation_parsing import Calling, Definition


class Pars:
    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser()
        self.args: Any = None
        self.calling = Calling
        self.definition = Definition

    def default_pars(self) -> None:
        self.parser.add_argument(
            '--functions_definition',
            default='data/input/functions_definition.json'
        )
        self.parser.add_argument(
            '--input',
            default='data/input/function_calling_tests.json'
        )
        self.parser.add_argument(
            '--output',
            default='data/output/function_calls.json'
        )
        self.args = self.parser.parse_args()
        output = Path(self.args.output)
        output.parent.mkdir(parents=True, exist_ok=True)

    def pars_file(self, files: List[str]) -> None:
        self.parser.add_argument(
            '--functions_definition',
            default=files
        )
        self.parser.add_argument(
            '--input',
            default=files
        )
        self.parser.add_argument(
            '--output',
            default=files
        )
        self.args = self.parser.parse_args()
        output = Path(self.args.output)
        output.parent.mkdir(parents=True, exist_ok=True)

    def open_files(self) -> tuple[list[Calling], list[Definition]]:
        with open(self.args.input, "r", encoding='utf-8') as fd:
            promps = [self.calling(**item) for item in json.load(fd)]
        with open(
            self.args.functions_definition,
            "r",
            encoding='utf-8'
        ) as fd2:
            call = [self.definition(**item) for item in json.load(fd2)]
        return promps, call

    def return_output(self, results: Any) -> None:
        with open(self.args.output, 'w') as fd:
            json.dump(results, fd, indent=2)
