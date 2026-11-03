import os
from typing import Any, Dict, List, Optional


class AnswerGenerator:
    """Carrega um modelo de linguagem e cria respostas com contexto do RAG."""

    def __init__(
        self,
        model_name: str = 'Qwen/Qwen3-0.6B',
        max_context_length: int = 500,
        max_sources: int = 3,
        max_new_tokens: int = 256,
    ) -> None:
        """Guarda as opções usadas para gerar respostas.

        Recebe o nome do modelo e limites de contexto, fontes e tokens.
        Inicializa o gerador sem carregar o modelo. Exemplo:
        ``AnswerGenerator(max_sources=2)`` configura o uso de até duas
        fontes; o método não devolve um valor.
        """
        self.model_name = model_name
        self.max_context_length = max_context_length
        self.max_sources = max_sources
        self.max_new_tokens = max_new_tokens
        self.tokenizer: Optional[Any] = None
        self.model: Optional[Any] = None

    def load(self) -> None:
        """Carrega o tokenizador e o modelo na melhor unidade disponível.

        Não recebe argumentos nem devolve um valor. Passo a passo: verifica
        se há Apple MPS, CUDA ou usa CPU; carrega o modelo e o tokenizador,
        coloca o modelo no dispositivo escolhido e desativa o treino.
        Exemplo: após ``load()``, o objeto pode gerar respostas.
        """
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
            self.model_name,
            trust_remote_code=True,
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=dtype,
            trust_remote_code=True,
        )

        assert self.model is not None

        self.model = self.model.to(device)  # type: ignore[arg-type]
        self.model.eval()

        torch.set_grad_enabled(False)

    def _resolve_context_path(
        self,
        file_path: str,
        repo_path: str,
    ) -> str:
        """Encontra o caminho real de um arquivo citado nos resultados.

        Recebe o caminho guardado no índice e a pasta do repositório.
        Testa o caminho original, relativo ao repositório e os caminhos
        absolutos correspondentes. Devolve o primeiro que existir; se
        nenhum existir, devolve o caminho original. Exemplo:
        ``("src/main.py", "/projeto")`` pode resultar em
        ``"/projeto/src/main.py"``.
        """
        candidates: List[str] = []

        normalized = file_path.strip()

        if normalized:
            candidates.append(normalized)
            candidates.append(
                os.path.join(repo_path, normalized)
            )
            candidates.append(
                os.path.abspath(
                    os.path.join(repo_path, normalized)
                )
            )
            candidates.append(
                os.path.abspath(normalized)
            )

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
        """Monta a instrução para o modelo com trechos encontrados no índice.

        Recebe a pergunta, fontes com caminho e posições, e a pasta do
        repositório. Lê até ``max_sources`` arquivos, limita o contexto a
        ``max_context_length`` caracteres e devolve o prompt completo com
        instruções, contexto e pergunta. Exemplo: o resultado inclui
        ``Context:``, os trechos encontrados e ``Question: ...``.
        """
        context_parts: List[str] = []
        remaining = self.max_context_length

        for src in sources[:self.max_sources]:
            if remaining <= 0:
                break

            file_path = str(src.get('file_path', ''))
            start = int(
                src.get('first_character_index', 0)
            )
            end = int(
                src.get('last_character_index', 0)
            )

            try:
                full_path = self._resolve_context_path(
                    file_path,
                    repo_path,
                )

                if not full_path:
                    continue

                with open(
                    full_path,
                    'r',
                    encoding='utf-8',
                    errors='ignore',
                ) as f:
                    content = f.read()

                snippet = content[start:end]

                if not snippet.strip():
                    continue

                snippet = snippet[:remaining]

                context_parts.append(
                    f"[{file_path}]\n{snippet}"
                )

                remaining -= len(snippet)

            except OSError:
                continue

        context_str = '\n---\n'.join(context_parts)

        return (
            "Use only the provided context to answer the question. "
            "If the answer is not stated directly in the snippets, "
            "reply with 'Not enough information in the provided context.' "
            "Keep the response short, factual, and grounded in the source.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

    def generate(
        self,
        question: str,
        sources: List[Dict[str, Any]],
        repo_path: str,
        max_new_tokens: Optional[int] = None,
    ) -> str:
        """Gera uma resposta baseada apenas nas fontes encontradas.

        Recebe a pergunta, as fontes, a pasta do repositório e, opcionalmente,
        o limite de tokens. Passo a passo: carrega o modelo se necessário,
        monta e codifica o prompt, gera texto e devolve a resposta. Se o
        modelo não produzir texto, devolve ``"No answer could be generated."``.
        Exemplo: ``generate("O que faz X?", fontes, pasta)`` devolve uma
        resposta curta ou a mensagem de falta de resposta.
        """
        if self.model is None or self.tokenizer is None:
            self.load()

        import torch

        tokens_to_gen = (
            max_new_tokens
            if max_new_tokens is not None
            else self.max_new_tokens
        )

        prompt = self._build_prompt(
            question,
            sources,
            repo_path,
        )

        assert self.model is not None
        assert self.tokenizer is not None

        chat_template = getattr(
            self.tokenizer,
            'chat_template',
            None,
        )

        if chat_template:
            messages = [
                {
                    'role': 'user',
                    'content': prompt,
                }
            ]

            try:
                encoded = self.tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    enable_thinking=False,
                    return_tensors='pt',
                )
            except TypeError:
                encoded = self.tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    return_tensors='pt',
                )

            inputs = dict(encoded)

        else:
            encoded = self.tokenizer(
                prompt,
                return_tensors='pt',
                truncation=True,
                max_length=1024,
            )

            inputs = dict(encoded)

        device = next(
            self.model.parameters()
        ).device

        inputs = {
            key: value.to(device)
            for key, value in inputs.items()
        }

        with torch.no_grad():
            pad_token_id = self.tokenizer.pad_token_id

            if pad_token_id is None:
                pad_token_id = self.tokenizer.eos_token_id

            outputs = self.model.generate(
                **inputs,
                max_new_tokens=tokens_to_gen,
                do_sample=False,
                repetition_penalty=1.1,
                no_repeat_ngram_size=4,
                pad_token_id=pad_token_id,
            )

        input_len = inputs['input_ids'].shape[1]

        generated = outputs[0][input_len:]

        answer = self.tokenizer.decode(
            generated,
            skip_special_tokens=True,
        ).strip()

        return (
            answer
            if answer
            else "No answer could be generated."
        )
