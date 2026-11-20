from dataclasses import dataclass, field
from functools import lru_cache

from . import guardas
from .chunking import ESTRATEGIAS
from .config import LIMIAR_SIMILARIDADE, TOP_K
from .corpus import carregar_documentos
from .generator import LLMIndisponivel, gerar
from .retriever import Indice

MSG_SEM_BASE = ("Não encontrei essa informação nas páginas oficiais que consulto. "
                "Para confirmar, ligue 156 ou acesse o portal SP156.")
MSG_INJECAO = ("Só consigo ajudar com dúvidas sobre serviços de zeladoria da Prefeitura. "
               "Não posso mudar minhas regras nem mostrar instruções internas.")
MSG_FORA = "O serviço de respostas está indisponível agora. Tente de novo em alguns minutos ou ligue 156."


@dataclass
class Fonte:
    id: str
    titulo: str
    url: str
    secao: str
    atualizado_em: str


@dataclass
class Resposta:
    resposta: str
    situacao: str
    fontes: list[Fonte] = field(default_factory=list)
    trechos_recuperados: list[dict] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)


@lru_cache(maxsize=4)
def indice(estrategia: str = "estrutura") -> Indice:
    return Indice(ESTRATEGIAS[estrategia](carregar_documentos()))


def _consulta(pergunta: str, historico: list[dict]) -> str:
    anteriores = [t["texto"] for t in historico if t["papel"] == "user"]
    if anteriores and len(pergunta.split()) <= 8:
        return " ".join(anteriores[-2:] + [pergunta])
    return pergunta


def responder(pergunta: str, historico: list[dict] | None = None, categoria: str | None = None,
              modo: str = "hibrido", estrategia: str = "estrutura", k: int = TOP_K) -> Resposta:
    historico = historico or []
    pergunta = guardas.mascarar_pii(pergunta.strip())
    if guardas.parece_injecao(pergunta):
        return Resposta(MSG_INJECAO, "bloqueada_entrada", alertas=["tentativa de desviar o assistente detectada na pergunta"])

    resultados = indice(estrategia).buscar(_consulta(pergunta, historico), modo=modo, k=k, categoria=categoria)
    recuperados = [{"id": r.chunk.id, "titulo": r.chunk.titulo, "secao": r.chunk.secao,
                    "similaridade": round(r.similaridade, 3), "texto": r.chunk.texto} for r in resultados]
    if not resultados or max(r.similaridade for r in resultados) < LIMIAR_SIMILARIDADE:
        return Resposta(MSG_SEM_BASE, "abstencao_recuperacao", trechos_recuperados=recuperados,
                        alertas=["nenhum trecho parecido o bastante com a pergunta"])

    alertas, trechos = [], []
    for r in resultados:
        texto, removeu = guardas.limpar_trecho(r.chunk.texto)
        if removeu:
            alertas.append(f"instrução suspeita removida do trecho {r.chunk.id}")
        trechos.append((r.chunk.id, texto))

    try:
        saida = gerar(pergunta, trechos, historico)
    except LLMIndisponivel as e:
        return Resposta(MSG_FORA, "erro_llm", trechos_recuperados=recuperados, alertas=[str(e)])

    if guardas.vazou_instrucoes(saida.resposta):
        return Resposta(MSG_INJECAO, "bloqueada_saida", trechos_recuperados=recuperados,
                        alertas=["a resposta continha instruções internas e foi bloqueada"])
    if not saida.suficiente:
        return Resposta(saida.resposta, "abstencao_llm", trechos_recuperados=recuperados)

    por_id = {r.chunk.id: r.chunk for r in resultados}
    validas = [c for c in dict.fromkeys(saida.citacoes) if c in por_id]
    if len(validas) < len(saida.citacoes):
        alertas.append("citação para trecho não recuperado descartada")
    if not validas:
        return Resposta(MSG_SEM_BASE, "nao_sustentada", trechos_recuperados=recuperados,
                        alertas=alertas + ["resposta sem citação válida foi bloqueada"])
    contexto = "\n".join(t for i, t in trechos if i in validas)
    faltando = guardas.numeros_sem_suporte(saida.resposta, contexto)
    if faltando:
        return Resposta(MSG_SEM_BASE, "nao_sustentada", trechos_recuperados=recuperados,
                        alertas=alertas + [f"números sem apoio nos trechos citados: {', '.join(faltando)}"])
    fontes = [Fonte(c, por_id[c].titulo, por_id[c].url, por_id[c].secao, por_id[c].metadados["atualizado_em"])
              for c in validas]
    return Resposta(saida.resposta, "respondida", fontes, recuperados, alertas)
