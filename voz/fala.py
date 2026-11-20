import re
from datetime import date

from num2words import num2words

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
SIGLAS = {
    "SP156": "S P cento e cinquenta e seis", "SPTrans": "S P Trans", "SMSUB": "Secretaria das Subprefeituras",
    "CET": "C E T", "SABESP": "Sabesp", "COMGÁS": "Comgás", "UBS": "U B S", "CPF": "C P F", "RG": "R G",
    "PIX": "pix", "OGM": "Ouvidoria Geral do Município", "SELIMP": "Selimp", "Ilume": "Ilume",
}
TELEFONES = {"156", "199", "193", "190", "192", "0800"}
_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")


def _n(x: str) -> str:
    return num2words(int(x), lang="pt_BR")


def _data(m: re.Match) -> str:
    d, mes, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        date(a, mes, d)
    except ValueError:
        return m.group(0)
    dia = "primeiro" if d == 1 else _n(str(d))
    return f"{dia} de {MESES[mes - 1]} de {_n(str(a))}"


def _dinheiro(m: re.Match) -> str:
    reais = int(m.group(1).replace(".", ""))
    cent = int(m.group(2) or 0)
    t = f"{num2words(reais, lang='pt_BR')} {'real' if reais == 1 else 'reais'}"
    if cent:
        t += f" e {num2words(cent, lang='pt_BR')} centavos"
    return t


def _digitos(n: str) -> str:
    nomes = "zero um dois três quatro cinco seis sete oito nove".split()
    return " ".join(nomes[int(c)] for c in n)


def para_fala(texto: str, max_frases: int = 4) -> str:
    t = _EMOJI.sub("", texto)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"https?://\S+", "no site da Prefeitura", t)
    t = re.sub(r"[*_`#>|]+", "", t)
    t = re.sub(r"^\s*[-•]\s*", "", t, flags=re.M)
    t = t.replace("‑", "-").replace("–", ",").replace("—", ",").replace("“", "").replace("”", "").replace('"', "")
    for s, f in SIGLAS.items():
        t = re.sub(rf"\b{re.escape(s)}\b", f, t)
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", _data, t)
    t = re.sub(r"R\$\s*(\d{1,3}(?:\.\d{3})*|\d+)(?:,(\d{2}))?", _dinheiro, t)
    t = re.sub(r"\(?\b(\d{2})\)?\s?(\d{4,5})-(\d{4})\b", lambda m: _digitos(m.group(1) + m.group(2) + m.group(3)), t)
    t = re.sub(r"\b(\d+)\b", lambda m: _digitos(m.group(1)) if m.group(1) in TELEFONES else _n(m.group(1)), t)
    t = re.sub(r"\b(\d+),(\d+)\b", lambda m: f"{_n(m.group(1))} vírgula {_n(m.group(2))}", t)
    t = re.sub(r"\s*;\s*", ". ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.!?])", r"\1", t)
    frases = [f[:1].upper() + f[1:] for f in re.split(r"(?<=[.!?])\s+", t) if f]
    return " ".join(frases[:max_frases]).strip()
