import uuid
from typing import List, Union

from pydantic import BaseModel, Field


class MinimalSource(BaseModel):
    """Representa a localização de um trecho recuperado.

    Recebe o caminho do arquivo e as posições inicial/final em caracteres.
    Exemplo: ``MinimalSource(file_path="src/main.py",
    first_character_index=0, last_character_index=50)``.
    """

    file_path: str
    first_character_index: int
    last_character_index: int


class UnansweredQuestion(BaseModel):
    """Representa uma pergunta sem resposta e sem fontes anotadas.

    Recebe o texto da pergunta e, opcionalmente, um identificador. Se o
    identificador não vier, o Pydantic cria um UUID. Exemplo:
    ``UnansweredQuestion(question="O que é RAG?")`` cria uma pergunta com
    ``question_id`` automático.
    """

    question_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    question: str


class AnsweredQuestion(UnansweredQuestion):
    """Representa uma pergunta do conjunto de dados com fontes e resposta.

    Recebe os campos de ``UnansweredQuestion`` mais uma lista de fontes e a
    resposta esperada. Exemplo: ``AnsweredQuestion(question="O que é RAG?",
    sources=[...], answer="...")``.
    """

    sources: List[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    """Representa o conjunto de perguntas usado para avaliar o RAG.

    Recebe uma lista de perguntas respondidas ou não respondidas.
    Exemplo: ``RagDataset(rag_questions=[pergunta1, pergunta2])`` valida e
    organiza os itens como dados do conjunto.
    """

    rag_questions: List[Union[AnsweredQuestion, UnansweredQuestion]]


class MinimalSearchResults(BaseModel):
    """Guarda os resultados de busca de uma pergunta, sem resposta gerada.

    Recebe o identificador e o texto da pergunta, além das fontes
    recuperadas. Exemplo: ``MinimalSearchResults(question_id="1",
    question_str="O que é RAG?", retrieved_sources=[...])``.
    """

    question_id: str
    question_str: str
    retrieved_sources: List[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    """Guarda os resultados de busca e a resposta gerada para uma pergunta.

    Recebe todos os campos de ``MinimalSearchResults`` e o texto da resposta.
    Exemplo: ``MinimalAnswer(question_id="1", question_str="...",
    retrieved_sources=[], answer="...")``.
    """

    answer: str


class StudentSearchResults(BaseModel):
    """Representa o resultado da busca para várias perguntas.

    Recebe a lista de resultados individuais e o valor de ``k`` usado na
    busca. Exemplo: ``StudentSearchResults(search_results=[...], k=5)``.
    """

    search_results: List[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(StudentSearchResults):
    """Representa resultados de busca em lote com respostas geradas.

    Recebe os resultados respondidos e o valor de ``k``. É o formato de
    saída da etapa que gera respostas para várias perguntas. Exemplo:
    ``StudentSearchResultsAndAnswer(search_results=[resposta], k=5)``.
    """

    search_results: List[MinimalAnswer]  # type: ignore[assignment]
