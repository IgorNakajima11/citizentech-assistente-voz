import re
import secrets
import unicodedata

_PII = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
    (re.compile(r"(?:\(?\b\d{2}\)?\s?)?\b9?\d{4}-?\d{4}\b"), "[TELEFONE]"),
]

_INJECAO = [
    r"ignor\w* (as |todas as |suas )?(instru|regras|orienta)",
    r"esque[cç]\w* (as |todas as |suas )?(instru|regras)",
    r"(revel|mostr|exib|repit|imprim)\w* (o |seu |suas |as )?(prompt|instru[cç][oõ]es|regras do sistema|mensagem de sistema)",
    r"system prompt|prompt do sistema|mensagem de sistema",
    r"voc[eê] agora [eé]|a partir de agora voc[eê]|finja que|aja como",
    r"modo (desenvolvedor|developer|dan)|jailbreak",
    r"ignore (all |the )?(previous|above) instructions",
]
_RE_INJECAO = re.compile("|".join(_INJECAO), re.IGNORECASE)

CANARIO = f"CANARIO-{secrets.token_hex(4)}"


def mascarar_pii(texto: str) -> str:
    for padrao, troca in _PII:
        texto = padrao.sub(troca, texto)
    return texto


def parece_injecao(texto: str) -> bool:
    return bool(_RE_INJECAO.search(texto))


def limpar_trecho(texto: str) -> tuple[str, bool]:
    linhas, removeu = [], False
    for linha in texto.split("\n"):
        if parece_injecao(linha):
            removeu = True
            continue
        linhas.append(linha)
    return "\n".join(linhas), removeu


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def numeros_sem_suporte(resposta: str, contexto: str) -> list[str]:
    ctx = _norm(contexto)
    faltando = []
    for m in re.finditer(r"\d+(?:[.,]\d+)?(?:\s*(?:dias|horas|dia|hora|meses|anos|reais))?", _norm(resposta)):
        valor = m.group(0).strip()
        numero = re.match(r"\d+(?:[.,]\d+)?", valor).group(0)
        if len(numero) <= 1 and "dia" not in valor and "hora" not in valor:
            continue
        if numero not in ctx:
            faltando.append(valor)
    return faltando


def vazou_instrucoes(resposta: str) -> bool:
    return CANARIO in resposta or "REGRAS INTERNAS" in resposta
