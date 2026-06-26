"""Answer generation system using Qwen/Qwen3-0.6B.

This module handles loading the LLM and generating answers
based on retrieved context chunks.
"""

from typing import Any, Dict, List, Optional


class AnswerGenerator:
    """Generates natural language answers using a local LLM.

    Uses Qwen/Qwen3-0.6B for inference via the transformers library.

    Attributes:
        model_name: HuggingFace model identifier.
        max_context_length: Maximum characters per context chunk.
        tokenizer: The loaded tokenizer instance.
        model: The loaded model instance.
    """

    def __init__(
        self,
        model_name: str = 'Qwen/Qwen3-0.6B',
        max_context_length: int = 2000,
    ) -> None:
        """Initialize the AnswerGenerator.

        Args:
            model_name: HuggingFace model name to load.
            max_context_length: Max chars per retrieved context chunk.
        """
        self.model_name = model_name
        self.max_context_length = max_context_length
        self.tokenizer: Optional[Any] = None
        self.model: Optional[Any] = None

    def load(self) -> None:
        """Load the tokenizer and model into memory.

        Raises:
            ImportError: If transformers or torch are not installed.
            OSError: If the model cannot be loaded from HuggingFace.
        """
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
        """Build the prompt for the LLM from question and context.

        Args:
            question: The question to answer.
            sources: List of source dicts with file_path, first/last char idx.
            repo_path: Base path to the repository for reading files.

        Returns:
            A formatted prompt string.
        """
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
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                snippet = content[start:end][:self.max_context_length]
                context_parts.append(
                    f"[File: {file_path} @ {start}-{end}]\n{snippet}"
                )
            except OSError:
                continue

        context_str = '\n\n---\n\n'.join(context_parts)

        prompt = (
            f"You are a helpful assistant. Answer the question based on "
            f"the provided code context.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )
        return prompt

    def generate(
        self,
        question: str,
        sources: List[Dict[str, Any]],
        repo_path: str,
        max_new_tokens: int = 256,
    ) -> str:
        """Generate an answer given a question and retrieved sources.

        Args:
            question: The question to answer.
            sources: List of source dicts (file_path, first/last char idx).
            repo_path: Base path to the repository.
            max_new_tokens: Maximum tokens to generate.

        Returns:
            The generated answer as a string.
        """
        if self.model is None or self.tokenizer is None:
            self.load()

        import torch

        prompt = self._build_prompt(question, sources, repo_path)

        inputs = self.tokenizer(  # type: ignore[misc]
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
