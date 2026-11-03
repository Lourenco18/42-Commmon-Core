"""Ponto de entrada alternativo para iniciar o projeto.

O código principal fica no pacote ``student`` (``src/student/``) e pode ser
iniciado com ``python -m student ...``.

Os scripts de avaliação também podem usar ``python -m src ...``. Este
arquivo encaminha essa chamada para ``student.__main__.main`` sem duplicar
a lógica do programa.
"""
from student.__main__ import main

if __name__ == '__main__':
    main()
