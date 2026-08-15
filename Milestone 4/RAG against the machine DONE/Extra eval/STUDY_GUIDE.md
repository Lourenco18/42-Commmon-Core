# RAG against the machine — Study Guide

> Este documento explica o código, as ferramentas usadas e o raciocínio por detrás de cada decisão.
> Serve para preparar a peer evaluation.

---

## 1. O que é RAG?

**RAG (Retrieval-Augmented Generation)** é uma técnica que combina dois sistemas:

1. **Retrieval** — dado uma pergunta, vai buscar os documentos mais relevantes a uma base de dados
2. **Generation** — passa esses documentos a um LLM que gera uma resposta baseada neles

Em vez de o modelo "saber" tudo de memória (o que exige re-treino), o RAG dá-lhe acesso a uma fonte externa de informação em tempo real.

**Analogia**: imagina que tens um exame com consulta. O RAG é o sistema que te ajuda a encontrar a página certa no livro (retrieval) antes de escreveres a resposta (generation).

---

## 2. Estrutura do Projecto

```
src/student/
├── models.py      # Estruturas de dados (Pydantic)
├── chunker.py     # Divide ficheiros em pedaços
├── indexer.py     # Constrói e guarda o índice BM25
├── generator.py   # Gera respostas com o LLM
└── __main__.py    # CLI — interface de linha de comandos
```

O pipeline completo é:

```
vLLM repo → chunker → indexer (BM25) → [pergunta] → retriever → generator → resposta
```

---

## 3. models.py — Estruturas de Dados

### O que é o Pydantic?

**Pydantic** é uma biblioteca Python que valida dados automaticamente. Defines a estrutura esperada e ele garante que os dados estão correctos.

```python
class MinimalSource(BaseModel):
    file_path: str              # caminho do ficheiro
    first_character_index: int  # onde começa o chunk no ficheiro
    last_character_index: int   # onde acaba o chunk no ficheiro
```

### Porquê Pydantic?

- **Validação automática**: se um campo estiver a faltar ou tiver o tipo errado, dá erro imediatamente
- **Serialização JSON**: `model.model_dump_json()` produz JSON no formato exacto que a moulinette espera
- **O subject exige**: "All classes must use pydantic for validation and type safety"

### Modelos importantes

| Modelo | Para que serve |
|--------|---------------|
| `MinimalSource` | Representa uma fonte: ficheiro + índices de caracteres |
| `UnansweredQuestion` | Pergunta sem resposta (input) |
| `AnsweredQuestion` | Pergunta com resposta e fontes (ground truth) |
| `RagDataset` | Lista de perguntas (dataset completo) |
| `MinimalSearchResults` | Resultado de search: pergunta + fontes recuperadas |
| `MinimalAnswer` | MinimalSearchResults + resposta gerada |
| `StudentSearchResults` | Lista de MinimalSearchResults + k |
| `StudentSearchResultsAndAnswer` | Lista de MinimalAnswer + k |

### Porquê `question_str` em vez de `question`?

O subject PDF (V.7) diz `question`, mas o **binário da moulinette** (o avaliador real) espera `question_str`. Descobrimos isto ao ler o `moulinette_pkg/README.md` e ao testar com o Docker. O binário é a fonte da verdade — por isso usamos `question_str`.

---

## 4. chunker.py — Estratégia de Chunking

### O que é chunking?

Um ficheiro pode ter 10.000 caracteres. Não podemos indexar o ficheiro inteiro como uma unidade — seria demasiado genérico. O chunking divide o ficheiro em pedaços menores e mais significativos.

**Limite**: máximo **2000 caracteres** por chunk (exigido pelo subject e validado pela moulinette).

### Duas estratégias diferentes

#### Python files (`.py`) — AST chunking

```python
import ast
tree = ast.parse(content)
# Encontra boundaries em def e class de nível superior
```

**Porquê AST?** O AST (Abstract Syntax Tree) é a representação estrutural do código Python. Ao dividir em `def` e `class`, cada chunk contém uma unidade lógica completa — uma função ou uma classe. Isto é crítico para retrieval de código: se alguém pergunta "como funciona a função X", queremos recuperar o chunk que contém essa função inteira, não metade dela.

**Fallback**: se o ficheiro tiver erro de sintaxe, usa chunking por parágrafos.

#### Text/Markdown files — Paragraph chunking

```python
paragraphs = content.split('\n\n')  # divide em parágrafos
# Junta parágrafos adjacentes até ao limite de 2000 chars
```

**Porquê parágrafos?** A documentação Markdown é naturalmente dividida por parágrafos e secções. Cada parágrafo tende a falar de um tópico específico — ideal para retrieval.

### Garantia de tamanho máximo

Há três camadas de protecção:
1. Tratamento específico de parágrafos/blocos grandes
2. `_split_by_size` — divide por linhas
3. `_enforce_max_size` — rede de segurança final, divide por caracteres se necessário

Isto foi necessário porque a moulinette rejeita qualquer chunk com mais de 2000 caracteres com `Student data is valid: False`.

---

## 5. indexer.py — BM25

### O que é BM25?

**BM25 (Best Match 25)** é um algoritmo de ranking de documentos baseado em frequência de termos. É a evolução do TF-IDF.

**TF-IDF** (o predecessor):
- TF (Term Frequency): quantas vezes a palavra aparece no documento
- IDF (Inverse Document Frequency): palavras raras têm mais peso

**BM25 melhora o TF-IDF com**:
- **Term saturation**: a partir de certo ponto, repetir uma palavra não aumenta mais o score (evita spam de keywords)
- **Document length normalisation**: documentos longos não têm vantagem injusta sobre curtos

### Porquê BM25 em vez de embeddings semânticos?

- **Velocidade**: BM25 é instantâneo. Embeddings requerem um modelo neural para cada query
- **Sem GPU**: BM25 corre em CPU sem problemas
- **Código**: para perguntas sobre código, keywords exactas (nomes de funções, classes) são mais importantes que semântica
- **O subject exige**: "TF-IDF or BM25" — escolhemos BM25 por ser superior

### Tokenização personalizada

```python
def tokenize(text: str) -> List[str]:
    tokens = re.split(r'[^\w_]+', text.lower())
    # Também divide camelCase e snake_case
```

**Porquê tokenização personalizada?** O código Python usa `camelCase` e `snake_case`. Um tokenizador padrão trataria `OpenAIServer` como um token. O nosso divide em `openai` + `server` + `openaiserver` — assim uma query "openai server" encontra `OpenAIServer`.

### File paths

```python
rel_path = os.path.relpath(fpath).replace(os.sep, '/')
```

O `os.sep` no Windows é `\`. A moulinette compara paths com `/`. Por isso normalizamos sempre para `/` — descobrimos este bug ao testar no Windows onde o Recall@k dava 0.000.

### Persistência do índice

O índice é guardado em 3 ficheiros:
- `bm25.pkl` — o modelo BM25 serializado
- `chunks_meta.json` — metadados (file_path, start, end) de cada chunk
- `chunk_texts.pkl` — texto de cada chunk

**Porquê 3 ficheiros?** Separa dados estruturados (JSON legível) de dados binários (pickle), e permite recarregar o índice em < 1 segundo sem re-indexar.

---

## 6. generator.py — Geração de Respostas

### O modelo: Qwen/Qwen3-0.6B

- **0.6B** significa 600 milhões de parâmetros — pequeno o suficiente para correr em CPU
- O subject exige este modelo específico
- Carregado via HuggingFace `transformers`

### Detecção automática de device

```python
if torch.backends.mps.is_available():
    device = 'mps'    # Apple Silicon GPU
elif torch.cuda.is_available():
    device = 'cuda'   # NVIDIA GPU
else:
    device = 'cpu'    # fallback
```

No Linux da escola (com GPU), usa CUDA e é ~10x mais rápido que CPU.

### O prompt

```
Answer the question using only the context below. Be concise and source-grounded.

Context:
[ficheiro1.py]
...código...
---
[ficheiro2.md]
...documentação...

Question: Como funciona X?
Answer:
```

**Porquê este formato?**
- "using only the context" — evita alucinação (o modelo inventar coisas)
- "Be concise" — respostas curtas e directas
- Incluímos o nome do ficheiro para que a resposta seja source-grounded

### Parâmetros de geração

- `max_new_tokens=128` — respostas curtas, mais rápidas
- `do_sample=False` — geração determinística (sempre a mesma resposta para a mesma pergunta)
- `temperature=1.0` — obrigatório quando `do_sample=False`

---

## 7. __main__.py — CLI

### Python Fire

**Fire** é uma biblioteca que converte automaticamente uma classe Python numa CLI.

```python
class RAGSystem:
    def index(self, ...): ...
    def search(self, ...): ...

fire.Fire(RAGSystem)
```

Resultado:
```bash
uv run python -m student index --max_chunk_size 2000
uv run python -m student search "query" --k 10
```

**Porquê Fire?** O subject exige "CLI using Python Fire". É simples — não precisas de definir argumentos manualmente como no `argparse`.

### Comandos disponíveis

| Comando | O que faz |
|---------|-----------|
| `index` | Lê o repo vLLM, chunka os ficheiros, constrói o índice BM25 |
| `search` | Pesquisa uma query e mostra os top-k resultados |
| `search_dataset` | Processa um dataset de perguntas e guarda os resultados em JSON |
| `answer` | Pesquisa + gera resposta com o LLM para uma query |
| `answer_dataset` | Gera respostas para um dataset completo |
| `evaluate` | Calcula Recall@k comparando resultados com ground truth |

### Avaliação — Recall@k e IoU

**Recall@k**: para cada pergunta, verifica se as fontes correctas estão nos top-k resultados recuperados.

```
Recall@5 = número de fontes correctas encontradas no top-5 / total de fontes correctas
```

**IoU (Intersection over Union)**: como comparar dois intervalos de caracteres?

```
IoU = intersecção / união
```

Exemplo: GT é chars 100-200, recuperamos chars 150-300:
- Intersecção: 150-200 = 50 chars
- União: 100-300 = 200 chars
- IoU = 50/200 = 25% ≥ 5% → fonte encontrada ✅

**Porquê IoU ≥ 5%?** O subject (VI.1.1) diz "minimum 5% overlap counts as found". Usamos IoU porque é a métrica standard para comparar intervalos — descobrimos que era IoU (não overlap simples) ao ler o `moulinette_pkg/README.md`.

---

## 8. Ferramentas e Bibliotecas

| Ferramenta | Para que serve | Porquê |
|------------|---------------|--------|
| `uv` | Gestor de pacotes e ambientes virtuais | Exigido pelo subject; mais rápido que pip |
| `pydantic` | Validação e serialização de dados | Exigido pelo subject |
| `rank_bm25` | Algoritmo BM25 | Implementação eficiente de BM25 |
| `transformers` | Carregar e correr o Qwen3-0.6B | Biblioteca padrão HuggingFace |
| `torch` | Framework de deep learning | Necessário para o transformers |
| `fire` | CLI automática | Exigido pelo subject |
| `tqdm` | Barras de progresso | Exigido pelo subject |
| `flake8` | Linting (estilo de código) | Exigido pelo subject |
| `mypy` | Type checking estático | Exigido pelo subject |
| `accelerate` | Suporte a device_map no transformers | Necessário em algumas versões |

---

## 9. Resultados Finais

| Métrica | Resultado | Target | Status |
|---------|-----------|--------|--------|
| Recall@5 Docs | **0.830** | ≥ 0.80 | ✅ PASS |
| Recall@5 Code | **0.590** | ≥ 0.50 | ✅ PASS |
| Moulinette Docs | **PASS** | PASS | ✅ |
| Moulinette Code | **PASS** | PASS | ✅ |
| Questions valid (docs) | **86/100** | ≥ 80 | ✅ |
| Indexing time | ~10 segundos | ≤ 5 min | ✅ |
| flake8 | 0 erros | 0 erros | ✅ |
| mypy | 0 erros | 0 erros | ✅ |

---

## 10. O que NÃO vai no repo (e porquê)

| O que é | Porquê não commitar |
|---------|-------------------|
| `data/raw/vllm-0.10.1/` | Ficheiro grande (~12MB zip), o avaliador tem o seu |
| `data/processed/` | Gerado pelo `make index`, não é código |
| `data/output/` | Gerado pelo `make test`, não é código |
| `datasets_public/` | Fornecido pela escola, o avaliador tem o seu |
| `moulinette_pkg/` | Fornecido pela escola, não é teu código |
| `.venv/` | Gerado pelo `make install` |
| `*.egg-info/` | Gerado automaticamente pelo setuptools |

O subject (IX) diz explicitamente: *"Do not include large data files, model weights, or generated outputs in your repository."*

---

## 11. Perguntas Típicas da Peer Evaluation

**"Porque usaste BM25 em vez de embeddings?"**
> BM25 é rápido, corre em CPU, e para código com nomes de funções específicos funciona muito bem. Embeddings seriam mais lentos e precisavam de GPU.

**"O que é o chunking e porque tens duas estratégias?"**
> Chunking divide ficheiros grandes em pedaços pesquisáveis. Para Python uso AST porque preserva funções e classes inteiras. Para Markdown uso parágrafos porque é a unidade natural da documentação.

**"Como funciona o Recall@k?"**
> Para cada pergunta, verifico se as fontes correctas (do ground truth) estão nos top-k resultados que recuperei. Uso IoU ≥ 5% para decidir se uma fonte foi "encontrada".

**"Porque `question_str` em vez de `question`?"**
> O subject PDF diz `question`, mas o binário da moulinette espera `question_str`. Descobrimos ao testar com Docker — o binário é a fonte da verdade.

**"O que é o IoU?"**
> Intersection over Union — mede o overlap entre dois intervalos de caracteres. Intersecção dividida pela união. A moulinette usa IoU ≥ 5% como threshold.

**"Porque o path dos ficheiros inclui `data/raw/vllm-0.10.1/`?"**
> A moulinette compara os paths que retornamos com os paths no ground truth, que são `data/raw/vllm-0.10.1/...`. Usamos `os.path.relpath()` relativo à raiz do projecto para gerar o path correcto automaticamente.
