import os
from typing import Any, Dict, List, Optional


class AnswerGenerator:
    def __init__(
        self,
        model_name: str = 'Qwen/Qwen3-0.6B',
        max_context_length: int = 500,
        max_sources: int = 3,
        max_new_tokens: int = 128,
    ) -> None:
        self.model_name = model_name
        self.max_context_length = max_context_length
        self.max_sources = max_sources
        self.max_new_tokens = max_new_tokens
        self.tokenizer: Optional[Any] = None
        self.model: Optional[Any] = None

    def load(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if torch.backends.mps.is_available():
            device = 'mps'
            dtype = torch.float16
        elif torch.cuda.is_available():
            device = 'cuda'
            dtype = torch.float16
        else:
            device = 'cpu'
            dtype = torch.float32

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=dtype,
            trust_remote_code=True,
        )
        assert self.model is not None
        # transformers/accelerate wrap `to` with a decorator whose stub
        # signature mypy resolves incorrectly for a plain device string;
        # this is a stub-only mismatch, not a runtime issue.
        self.model = self.model.to(device)  # type: ignore[arg-type]
        self.model.eval()

        import torch
        torch.set_grad_enabled(False)

    def _resolve_context_path(self, file_path: str, repo_path: str) -> str:
        candidates: List[str] = []
        normalized = file_path.strip()
        if normalized:
            candidates.append(normalized)
            candidates.append(os.path.join(repo_path, normalized))
            candidates.append(os.path.abspath(os.path.join(repo_path,
                                                           normalized)))
            candidates.append(os.path.abspath(normalized))

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        return normalized

    def _build_prompt(
        self,
        question: str,
        sources: List[Dict[str, Any]],
        repo_path: str,
    ) -> str:
        context_parts: List[str] = []

        for src in sources[:self.max_sources]:
            file_path = src.get('file_path', '')
            start = src.get('first_character_index', 0)
            end = src.get('last_character_index', 0)

            try:
                full_path = self._resolve_context_path(file_path, repo_path)
                if not full_path:
                    continue
                with open(
                    full_path,
                    'r',
                    encoding='utf-8',
                    errors='ignore',
                ) as f:
                    content = f.read()
                snippet = content[start:end][:self.max_context_length]
                if snippet.strip():
                    context_parts.append(
                        f"[{os.path.basename(file_path)}]\n{snippet}"
                    )
            except OSError:
                continue

        context_str = '\n---\n'.join(context_parts)

        prompt = (
            "Use only the provided context to answer the question. "
            "If the answer is not stated directly in the snippets, reply "
            "with 'Not enough information in the provided context.' "
            "Keep the response short, factual, and grounded in the source.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
        return prompt

    def generate(
        self,
        question: str,
        sources: List[Dict[str, Any]],
        repo_path: str,
        max_new_tokens: Optional[int] = None,
    ) -> str:
        if self.model is None or self.tokenizer is None:
            self.load()

        import torch

        tokens_to_gen = max_new_tokens or self.max_new_tokens
        prompt = self._build_prompt(question, sources, repo_path)

        assert self.model is not None
        assert self.tokenizer is not None

        # Qwen3-0.6B is a chat/instruction-tuned model: it expects the
        # ChatML-style special tokens (<|im_start|>/<|im_end|>) that
        # apply_chat_template inserts, not a raw completion-style
        # string. Without them the model doesn't reliably recognise
        # where the question ends or when to stop, which is what was
        # producing incoherent, repeating output. enable_thinking=False
        # keeps it a direct answer instead of a long <think> preamble
        # that could eat the whole token budget. Fall back to a plain
        # prompt for any tokenizer that doesn't define a chat template
        # (e.g. in tests with a non-chat stand-in model).
        chat_template = getattr(self.tokenizer, 'chat_template', None)
        if chat_template:
            messages = [{'role': 'user', 'content': prompt}]
            try:
                encoded = self.tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    enable_thinking=False,
                    return_tensors='pt',
                )
            except TypeError:
                # Older/other chat templates may not accept
                # enable_thinking; retry without it.
                encoded = self.tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    return_tensors='pt',
                )
            inputs = dict(encoded)
        else:
            encoded = self.tokenizer(  # type: ignore[misc]
                prompt,
                return_tensors='pt',
                truncation=True,
                max_length=1024,
            )
            inputs = dict(encoded)

        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=tokens_to_gen,
                do_sample=False,
                repetition_penalty=1.1,
                no_repeat_ngram_size=4,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        input_len = inputs['input_ids'].shape[1]
        generated = outputs[0][input_len:]
        answer = self.tokenizer.decode(
            generated, skip_special_tokens=True
        ).strip()

        return answer if answer else "No answer could be generated."
