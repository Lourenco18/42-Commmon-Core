import re
from typing import Dict, Any, List
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

    def _quoted_strings(self, text: str) -> List[str]:
        return [m.group(2) for m in re.finditer(r"(['\"])(.*?)\1", text)]

    def _numbers(self, text: str) -> List[str]:
        return re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", text)

    def _extract_by_param_name(self, prompt: str, param_name: str) -> str:
        low_param = param_name.lower()
        low_prompt = prompt.lower()

        if 'template' in low_param:
            m = re.search(r'[Ff]ormat\s+[Tt]emplate\s*:\s*(.*)', prompt)
            if m:
                return m.group(1).strip()

        if 'path' in low_param:
            m = re.search(r'\bat\s+(\S+?)(?:\s+with\b|$)',
                          prompt, re.IGNORECASE)
            if m:
                return m.group(1).rstrip('.,;')
            m = re.search(r'([A-Za-z]:\\[\S]+|/[\S]+)', prompt)
            if m:
                return m.group(1).rstrip('.,;')

        if 'encoding' in low_param:
            m = re.search(r'\bwith\s+([\w\-]+)\s+encoding\b',
                          prompt, re.IGNORECASE)
            if m:
                return m.group(1)

        if 'database' in low_param or 'db' in low_param:
            m = re.search(
                r'\bon\s+(?:the\s+)?(\w[\w\-]*)\s+database\b',
                prompt, re.IGNORECASE
            )
            if m:
                return m.group(1)

        if 'query' in low_param:
            quoted = self._quoted_strings(prompt)
            if quoted:
                return quoted[0]

        if 'source' in low_param or 'string' in low_param:
            quoted = self._quoted_strings(prompt)
            if quoted:
                return max(quoted, key=len)

        if 'regex' in low_param or 'pattern' in low_param:
            if 'number' in low_prompt or 'digit' in low_prompt:
                return r'\d+'
            if 'vowel' in low_prompt:
                return r'[aeiouAEIOU]'
            m = re.search(
                r'(?:word\s+)?[\'"]([^\'"]+?)[\'"]\s+with',
                prompt, re.IGNORECASE
            )
            if m:
                return m.group(1).strip()

        if 'replacement' in low_param or 'replace' in low_param:
            m = re.search(r'\bwith\s+([\'"])(.*?)\1', prompt, re.IGNORECASE)
            if m:
                return m.group(2)
            m2 = re.search(r'\bwith\s+([A-Z]{2,})\b', prompt)
            if m2:
                return m2.group(1)
            m3 = re.search(r'\bwith\s+([\w\*\#\@]+)\s*$',
                           prompt, re.IGNORECASE)
            if m3:
                raw = m3.group(1)
                _sym = {
                    'asterisks': '*', 'asterisk': '*',
                    'stars': '*',    'star': '*',
                    'hashes': '#',   'hash': '#',
                }
                return _sym.get(raw.lower(), raw)

        return ""

    def _extract_parameters(
        self, prompt: str, chosen_function: Any
    ) -> Dict[str, Any]:
        quoted = self._quoted_strings(prompt)
        numbers = self._numbers(prompt)
        params: Dict[str, Any] = {}
        num_idx = 0
        str_idx = 0

        for p_name, p_info in chosen_function.parameters.items():
            p_type = getattr(p_info, "type", "string")

            if p_type in ("number", "integer", "float"):
                raw = numbers[num_idx] if num_idx < len(numbers) else "0"
                num_idx += 1
                try:
                    params[p_name] = (
                        int(float(raw)) if p_type == "integer" else float(raw)
                    )
                except (ValueError, TypeError):
                    params[p_name] = 0
            else:
                val = self._extract_by_param_name(prompt, p_name)
                if val:
                    params[p_name] = val
                elif str_idx < len(quoted):
                    params[p_name] = quoted[str_idx]
                    str_idx += 1
                else:
                    params[p_name] = ""

        string_params = [
            n for n, i in chosen_function.parameters.items()
            if getattr(i, "type", "string") not in ("number",
                                                     "integer", "float")
        ]
        if len(string_params) == 1:
            p_name = string_params[0]
            if not params.get(p_name):
                words = re.findall(r"[\w\-]+", prompt)
                if words:
                    params[p_name] = words[-1]

        return params

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
            print(f"[INFO] Prompt {i}/{len(prompt_test)}: '{prompt}'")
            generated: List = []
            function_descriptions = "\n".join(
                f"- {d.name}: {d.description}" for d in function
            )
            full_prompt = (
                f"You are a function selector."
                f"Pick the single best function.\n\n"
                f"Available functions:\n{function_descriptions}\n\n"
                f"Examples:\n"
                f"Request: What is the product of 3 and 5? ->"
                f"{function_name[0]}\n"
                f"Request: {function[1].description} -> "
                f"{function_name[1]}\n"
                f"Request: {function[2].description} -> "
                f"{function_name[2]}\n\n"
                f"Request: {prompt} -> "
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
            selected_def = function_dict[selected_function_name]
            parameters = self._extract_parameters(prompt, selected_def)
            print(f"[INFO] -> {selected_function_name}({parameters})")
            results.append({
                "prompt": prompt,
                "name": selected_function_name,
                "parameters": parameters,
            })

        self.parser.return_output(results)
        print(f"[INFO] Done. {len(results)} result(s) written.")
