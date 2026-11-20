import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _carregar_env(caminho: Path) -> None:
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env(RAIZ / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_URL = os.environ.get("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")
LLM_TIMEOUT_S = float(os.environ.get("LLM_TIMEOUT_S", "30"))
MODELO_EMBEDDING = os.environ.get("MODELO_EMBEDDING", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
TOP_K = int(os.environ.get("TOP_K", "4"))
LIMIAR_SIMILARIDADE = float(os.environ.get("LIMIAR_SIMILARIDADE", "0.25"))
ARQUIVO_CORPUS = RAIZ / "corpus" / "documentos.jsonl"
