import re
from typing import Dict, Any, List, Optional
from llm_sdk.llm_sdk import Small_LLM_Model
import json
from src.parsing import Pars


class Answer:
    def __init__(self) -> None:
        self.llm = Small_LLM_Model()
        self.path_vocab: str = ""
        self.id_to_token: Dict[Any, Any] = {}
        self.vocab: Dict[str, Any] = {}
        self.parser = Pars()

    def get_vocab(self) -> None:
        self.path_vocab = self.llm.get_path_to_vocab_file()
        with open(self.path_vocab, 'r') as fd:
            self.vocab = json.load(fd)
        self.id_to_token = {v: k for k, v in self.vocab.items()}

    # ------------------------------------------------------------------
    # Generic argument extraction via regex (no LLM, no hardcoding)
    # ------------------------------------------------------------------

    def _extract_quoted_strings(self, text: str) -> List[str]:
        """Extract all single or double quoted substrings from text.

        Args:
            text: The raw user prompt.

        Returns:
            List of unquoted string contents in order of appearance.
        """
        return re.findall(r"""['"](.*?)['"]""", text)

    def _extract_numbers(self, text: str) -> List[str]:
        """Extract all numeric values (int or float) from text.

        Args:
            text: The raw user prompt.

        Returns:
            List of number strings in order of appearance.
        """
        return re.findall(r'-?\d+(?:\.\d+)?', text)

    def _extract_parameters(
        self, prompt: str, chosen_function: Any
    ) -> Dict[str, Any]:
        """Extract arguments from a prompt generically using regex.

        Strategy (no hardcoding per function name):
        - string parameters: filled from quoted substrings first, then
          remaining words; the LAST word-like token fills named params
          that look like identifiers (database, encoding, name, etc.)
        - number / integer parameters: filled from numeric tokens in order
        - boolean parameters: detect true/false/yes/no keywords

        This is O(1) per prompt — no LLM calls, no hangs.

        Args:
            prompt: The original user request.
            chosen_function: FunctionDefinition for the selected function.

        Returns:
            Dict of parameter names to coerced values.
        """
        params: Dict[str, Any] = {}
        param_items = list(chosen_function.parameters.items())

        numbers = self._extract_numbers(prompt)
        quoted = self._extract_quoted_strings(prompt)

        num_idx = 0
        str_idx = 0

        # Separate string and number params
        string_params = [(n, i) for n, i in param_items
                         if getattr(i, 'type', 'string') == 'string']
        number_params = [(n, i) for n, i in param_items
                         if getattr(i, 'type', 'string') in ('number', 'float', 'integer')]

        # --- Fill number params in order from extracted numbers ---
        for p_name, p_info in number_params:
            p_type = getattr(p_info, 'type', 'number')
            raw = numbers[num_idx] if num_idx < len(numbers) else "0"
            num_idx += 1
            try:
                if p_type == 'integer':
                    params[p_name] = int(float(raw))
                else:
                    params[p_name] = float(raw)
            except (ValueError, TypeError):
                params[p_name] = 0 if p_type == 'integer' else 0.0

        # --- Fill string params ---
        # First pass: use quoted values in order
        for p_name, p_info in string_params:
            if str_idx < len(quoted):
                params[p_name] = quoted[str_idx]
                str_idx += 1
            else:
                params[p_name] = ""

        # Second pass: for params still empty, try smart extraction
        # based on common linguistic patterns (generic, not per-function)
        for p_name, p_info in string_params:
            if params.get(p_name):
                continue

            val = self._extract_string_param(prompt, p_name)
            if val:
                params[p_name] = val

        # Log string params

        # --- Fill boolean params ---
        for p_name, p_info in param_items:
            if getattr(p_info, 'type', '') == 'boolean':
                low = prompt.lower()
                params[p_name] = any(
                    w in low for w in ('true', 'yes')
                ) and not any(
                    w in low for w in ('false', 'no', 'not')
                )

        return params

    def _extract_string_param(self, prompt: str, param_name: str) -> str:
        """Attempt to extract a string value using generic linguistic patterns.

        Uses common prepositions and keyword patterns that appear in natural
        language function call descriptions — no per-function names hardcoded.

        Patterns (in priority order):
        1. 'at <value> with'  — file paths
        2. 'on the <value> database/server/system' — named targets
        3. 'with <value> encoding' — encoding names
        4. 'Format template: <rest of line>' — templates
        5. Last word-like token before common stopwords

        Args:
            prompt: The original user request.
            param_name: The parameter name (used as hint only).

        Returns:
            Extracted string value, or empty string if not found.
        """
        # Pattern: "at <PATH> with" — file paths
        m = re.search(r'\bat\s+(\S+?)(?:\s+with\b)', prompt, re.IGNORECASE)
        if m and 'path' in param_name.lower():
            return m.group(1)

        # Pattern: "at <PATH>" (end of relevant segment)
        m = re.search(r'\bat\s+(\S+)', prompt, re.IGNORECASE)
        if m and 'path' in param_name.lower():
            return m.group(1).rstrip('.,;')

        # Pattern: "on the <NAME> database/server/system"
        m = re.search(
            r'\bon\s+(?:the\s+)?(\w[\w\-]*)\s+(?:database|server|system|db)\b',
            prompt, re.IGNORECASE
        )
        if m and param_name.lower() in ('database', 'server', 'db', 'target'):
            return m.group(1)

        # Pattern: "with <ENCODING> encoding"
        m = re.search(r'\bwith\s+([\w\-]+)\s+encoding\b', prompt, re.IGNORECASE)
        if m and 'encoding' in param_name.lower():
            return m.group(1)

        # Pattern: "Format template: <REST>"
        m = re.search(r'[Ff]ormat\s+[Tt]emplate\s*:\s*(.*)', prompt)
        if m and 'template' in param_name.lower():
            return m.group(1).strip()

        # Pattern: "C:\..." or "/path/..." — file paths
        m = re.search(r'([A-Za-z]:\\[\S]+|/[\S]+)', prompt)
        if m and 'path' in param_name.lower():
            return m.group(1).rstrip('.,;')

        return ""

    # ------------------------------------------------------------------
    # Function selection — constrained decoding (unchanged)
    # ------------------------------------------------------------------

    def function_token(self) -> None:
        prompts, function = self.parser.open_files()
        function_name = [definition.name for definition in function]
        prompt_test = [prompt.prompt for prompt in prompts]
        function_name_token = [
            self.llm.encode(name).tolist()[0] for name in function_name
        ]
        function_dict = {d.name: d for d in function}
        results = []

        for i, prompt in enumerate(prompt_test, 1):
            print(f"\n[INFO] Prompt {i}/{len(prompt_test)}: '{prompt}'")

            # Constrained function-name generation
            generated: List = []
            function_descriptions = "\n".join(
                f"- {d.name}: {d.description}" for d in function
            )
            full_prompt = (
                f"Available functions:\n{function_descriptions}\n\n"
                f"Select the correct function for: {prompt}\n"
                f"Function name:"
            )
            while True:
                if generated in function_name_token:
                    break
                test = self.llm.encode(full_prompt).tolist()[0]
                logits = self.llm.get_logits_from_input_ids(test)
                valid_tokens = set()
                for tokens in function_name_token:
                    if tokens[:len(generated)] == generated:
                        valid_tokens.add(tokens[len(generated)])
                for token_id in range(len(logits)):
                    if token_id not in valid_tokens:
                        logits[token_id] = float('-inf')
                generated.append(logits.index(max(logits)))
                full_prompt += self.llm.decode(generated[-1])

            selected_function_name = self.llm.decode(generated)
            print(f"[INFO] -> Function: {selected_function_name}")
            selected_def = function_dict[selected_function_name]

            parameters = self._extract_parameters(prompt, selected_def)
            print(f"[INFO] -> Parameters: {parameters}")

            results.append({
                "prompt": prompt,
                "name": selected_function_name,
                "parameters": parameters,
            })

        self.parser.return_output(results)
        print(f"\n[INFO] Done. {len(results)} result(s) written.")
