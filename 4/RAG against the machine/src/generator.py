from typing import Any, Dict, List, Optional


class AnswerGenerator:
    def __init__(
        self,
        model_name: str = 'Qwen/Qwen3-0.6B',
        max_context_length: int = 2000,
    ) -> None:
        self.model_name = model_name
        self.max_context_length = max_context_length
        self.tokenizer: Optional[Any] = None
        self.model: Optional[Any] = None

    def load(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float32,
            device_map='cpu',
            trust_remote_code=True,
        )
        assert self.model is not None
        self.model.eval()

    def _build_prompt(
        self,
        question: str,
        sources: List[Dict[str, Any]],
        repo_path: str,
    ) -> str:
        context_parts: List[str] = []

        for src in sources:
            file_path = src.get('file_path', '')
            start = src.get('first_character_index', 0)
            end = src.get('last_character_index', 0)

            try:
                full_path = (
                    file_path if file_path.startswith('/')
                    else f"{repo_path}/{file_path}"
                )
                with open(full_path, 'r', encoding='utf-8',
                          errors='ignore') as f:
                    content = f.read()
                snippet = content[start:end][:self.max_context_length]
                context_parts.append(
                    f"[File: {file_path} @ {start}-{end}]\n{snippet}"
                )
            except OSError:
                continue

        context_str = '\n\n---\n\n'.join(context_parts)

        prompt = (
            "You are a technical assistant for the vLLM codebase. "
            "Answer the question using ONLY the provided context below.\n"
            "Your answer must be:\n"
            "- Self-contained: readable and understandable without "
            "seeing the original question.\n"
            "- Source-grounded: mention the file(s) the information "
            "comes from.\n"
            "- Faithful: do not add information not present in the "
            "context (no hallucination).\n"
            "- Relevant: directly answer what was asked.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )
        return prompt

    def generate(
        self,
        question: str,
        sources: List[Dict[str, Any]],
        repo_path: str,
        max_new_tokens: int = 256,
    ) -> str:
        if self.model is None or self.tokenizer is None:
            self.load()

        import torch

        prompt = self._build_prompt(question, sources, repo_path)

        inputs = self.tokenizer(
            prompt,
            return_tensors='pt',
            truncation=True,
            max_length=2048,
        )

        assert self.model is not None
        assert self.tokenizer is not None

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=1.0,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        input_len = inputs['input_ids'].shape[1]
        generated = outputs[0][input_len:]
        answer = self.tokenizer.decode(
            generated, skip_special_tokens=True
        ).strip()

        return answer if answer else "No answer could be generated."
