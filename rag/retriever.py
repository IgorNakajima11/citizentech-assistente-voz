import re
import unicodedata
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from .chunking import Chunk
from .config import MODELO_EMBEDDING

STOPWORDS = set("""a o as os de da do das dos e é em no na nos nas um uma uns umas para por pra com sem que se ao aos à às
ou como mais mas meu minha meus minhas seu sua seus suas eu você voce isso esse essa este esta tem ter há ha foi ser
qual quais quando onde quem posso pode preciso fazer faço faco sobre""".split())


def _sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def tokenizar(texto: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _sem_acento(texto)) if t not in STOPWORDS and len(t) > 1]


@dataclass
class Resultado:
    chunk: Chunk
    score: float
    similaridade: float


class _Embedder:
    _modelo = None

    @classmethod
    def modelo(cls):
        if cls._modelo is None:
            from fastembed import TextEmbedding
            cls._modelo = TextEmbedding(MODELO_EMBEDDING)
        return cls._modelo

    @classmethod
    def codificar(cls, textos: list[str]) -> np.ndarray:
        v = np.array(list(cls.modelo().embed(textos)), dtype=np.float32)
        return v / np.linalg.norm(v, axis=1, keepdims=True)


class Indice:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenizar(c.texto) for c in chunks])
        self.vetores = _Embedder.codificar([c.texto for c in chunks])

    def _filtrados(self, categoria: str | None) -> np.ndarray:
        if not categoria or categoria == "outro":
            return np.ones(len(self.chunks), dtype=bool)
        return np.array([c.categoria in (categoria, "outro") for c in self.chunks])

    def similaridades(self, consulta: str) -> np.ndarray:
        return self.vetores @ _Embedder.codificar([consulta])[0]

    def buscar(self, consulta: str, modo: str = "hibrido", k: int = 4, categoria: str | None = None) -> list[Resultado]:
        mascara = self._filtrados(categoria)
        sims = self.similaridades(consulta)
        lex = np.array(self.bm25.get_scores(tokenizar(consulta)))
        if modo == "bm25":
            score = lex
        elif modo == "denso":
            score = sims
        else:
            score = np.zeros(len(self.chunks))
            for valores in (lex, sims):
                ordem = np.argsort(-np.where(mascara, valores, -np.inf))
                for pos, i in enumerate(ordem):
                    score[i] += 1.0 / (60 + pos + 1)
        score = np.where(mascara, score, -np.inf)
        melhores = np.argsort(-score)[:k]
        return [Resultado(self.chunks[i], float(score[i]), float(sims[i])) for i in melhores]
