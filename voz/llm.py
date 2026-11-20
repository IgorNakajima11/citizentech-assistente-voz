import re
import unicodedata

from rag.assistente import Resposta, responder

PAPEL = ("Assistente de voz do CitizenTech: orienta moradores de São Paulo sobre serviços de zeladoria da Prefeitura, "
         "com base só nas páginas oficiais do SP156; recusa assuntos fora do tema e manda procurar o órgão certo.")

ENCAMINHAMENTOS = [
    ("emergencia_saude",
     r"\b(dor no peito|falta de ar|desmai|infart|avc|sangra|convuls|engasg|nao respira|inconsciente|overdose)",
     "Isso pode ser uma emergência de saúde. Ligue agora para o SAMU, no 192. Eu não posso dar orientação médica."),
    ("saude",
     r"\b(remedio|medicamento|doenca|sintoma|febre|dor de|dor no|dor na|consulta medica|receita medica|tratamento)",
     "Não posso dar orientação de saúde. Procure uma Unidade Básica de Saúde ou um profissional de saúde. "
     "Em emergência, ligue 192, o SAMU."),
    ("juridico",
     r"\b(processar|process(o|e) (o|a|meu|minha|um|uma|essa|esse|empresa)|processo judicial|advogad|justica|juiz|tribunal|indenizacao|acao judicial|direito trabalhista|pensao)",
     "Não posso dar orientação jurídica. Procure a Defensoria Pública ou um advogado. "
     "Para conflitos de consumo, o Procon também pode ajudar."),
    ("violencia",
     r"\b(assalt|roubo|furto|agress|violencia|ameaca|arma|tiro)",
     "Em situação de violência ou crime, ligue 190, a Polícia Militar. Eu só oriento sobre serviços de zeladoria."),
]


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def encaminhamento(texto: str) -> tuple[str, str] | None:
    t = _norm(texto)
    for tipo, padrao, mensagem in ENCAMINHAMENTOS:
        if re.search(padrao, t):
            return tipo, mensagem
    return None


def responder_turno(texto: str, historico: list[dict]) -> Resposta:
    fora = encaminhamento(texto)
    if fora:
        return Resposta(fora[1], f"recusa_{fora[0]}")
    return responder(texto, historico=historico)
