import re
from dataclasses import dataclass, field

from .corpus import Documento

SECOES = [
    "O QUE É", "QUANDO SOLICITAR", "PÚBLICO-ALVO", "PÚBLICO- ALVO", "REQUISITOS, DOCUMENTOS E INFORMAÇÕES",
    "REQUISITOS, DOCUMENTOS OU INFORMAÇÕES", "PRAZO MÁXIMO", "TAXAS OU PREÇO PÚBLICO", "CANAIS PARA SOLICITAR O SERVIÇO",
    "CANAIS PARA SOLICITAR", "PRINCIPAIS ETAPAS", "LEGISLAÇÃO", "OBSERVAÇÕES", "ÓRGÃO RESPONSÁVEL",
    "MANIFESTAÇÃO SOBRE O SERVIÇO", "MANIFESTAÇÃO SOBRE SERVIÇO",
]
_TITULO_SECAO = re.compile(r"^-?\s*(" + "|".join(re.escape(s) for s in SECOES) + r")\s*$", re.IGNORECASE)


@dataclass
class Chunk:
    id: str
    doc_id: str
    titulo: str
    url: str
    secao: str
    texto: str
    categoria: str
    metadados: dict = field(default_factory=dict)


def _janelas(texto: str, tamanho: int, overlap: int) -> list[str]:
    if len(texto) <= tamanho:
        return [texto]
    partes, inicio = [], 0
    while inicio < len(texto):
        fim = min(len(texto), inicio + tamanho)
        if fim < len(texto):
            corte = texto.rfind(" ", inicio + tamanho // 2, fim)
            fim = corte if corte > 0 else fim
        partes.append(texto[inicio:fim].strip())
        if fim >= len(texto):
            break
        inicio = max(fim - overlap, inicio + 1)
    return partes


def _descricao(secoes: list[tuple[str, str]]) -> str:
    for secao, corpo in secoes:
        if secao == "O QUE É":
            frase = re.split(r"(?<=[.!?])\s", corpo.strip(), maxsplit=1)[0]
            return frase[:200]
    return ""


def por_estrutura(docs: list[Documento], tamanho_max: int = 1200, overlap: int = 200,
                  com_descricao: bool = True) -> list[Chunk]:
    chunks = []
    for d in docs:
        secoes, atual, linhas = [], "AVISOS", []
        for linha in d.texto.split("\n"):
            m = _TITULO_SECAO.match(linha.strip())
            if m:
                if linhas:
                    secoes.append((atual, "\n".join(linhas)))
                atual, linhas = m.group(1).upper().replace("PÚBLICO- ALVO", "PÚBLICO-ALVO"), []
            else:
                linhas.append(linha)
        if linhas:
            secoes.append((atual, "\n".join(linhas)))
        descricao = _descricao(secoes)
        for n, (secao, corpo) in enumerate(secoes):
            if secao.startswith("MANIFESTAÇÃO") or secao == "LEGISLAÇÃO":
                continue
            for k, parte in enumerate(_janelas(corpo, tamanho_max, overlap)):
                cabecalho = f"Serviço: {d.titulo}\n"
                if com_descricao and descricao:
                    cabecalho += f"Descrição do serviço: {descricao}\n"
                cabecalho += f"Seção: {secao}\n"
                chunks.append(Chunk(f"{d.id}#{n}.{k}", d.id, d.titulo, d.url, secao, cabecalho + parte, d.categoria,
                                    {"atualizado_em": d.atualizado_em, "data_consulta": d.data_consulta}))
    return chunks


def tamanho_fixo(docs: list[Documento], tamanho: int = 600, overlap: int = 120) -> list[Chunk]:
    chunks = []
    for d in docs:
        texto = re.sub(r"\s+", " ", d.texto)
        for k, parte in enumerate(_janelas(texto, tamanho, overlap)):
            chunks.append(Chunk(f"{d.id}#f{k}", d.id, d.titulo, d.url, "", parte, d.categoria,
                                {"atualizado_em": d.atualizado_em, "data_consulta": d.data_consulta}))
    return chunks


ESTRATEGIAS = {
    "estrutura": por_estrutura,
    "estrutura_sem_descricao": lambda docs: por_estrutura(docs, com_descricao=False),
    "fixo": tamanho_fixo,
}
