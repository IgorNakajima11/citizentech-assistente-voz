import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from voz import fala, tts  # noqa: E402

PASTA = RAIZ / "testes" / "tts"


def main() -> None:
    respostas = json.loads((RAIZ / "testes" / "llm" / "resultados_llm.json").read_text(encoding="utf-8"))
    escolhidas = [r for r in respostas if r["situacao"] == "respondida"][:8] + \
                 [r for r in respostas if r["tipo"] == "fora_escopo"][:2]
    itens = []
    for n, r in enumerate(escolhidas, 1):
        falado = fala.para_fala(r["resposta"])
        (PASTA / f"tts{n:02d}.mp3").write_bytes(tts.sintetizar(falado))
        itens.append({"id": f"tts{n:02d}", "origem": r["id"], "texto_original": r["resposta"], "texto_falado": falado})
    (PASTA / "itens_tts.json").write_text(json.dumps(itens, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(itens), "áudios gerados")


if __name__ == "__main__":
    main()
