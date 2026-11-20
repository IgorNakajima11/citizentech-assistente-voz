import json
import sys
import time
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from voz import llm  # noqa: E402

PASTA = RAIZ / "testes" / "llm"
RECUSAS = {"abstencao_recuperacao", "abstencao_llm", "nao_sustentada", "bloqueada_entrada", "bloqueada_saida",
           "recusa_emergencia_saude", "recusa_saude", "recusa_juridico", "recusa_violencia"}


def norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def main() -> None:
    perguntas = json.loads((PASTA / "perguntas.json").read_text(encoding="utf-8"))
    linhas = []
    for p in perguntas:
        historico = []
        if p.get("contexto"):
            r0 = llm.responder_turno(p["contexto"], [])
            historico = [{"papel": "user", "texto": p["contexto"]}, {"papel": "assistant", "texto": r0.resposta}]
        t0 = time.perf_counter()
        r = llm.responder_turno(p["pergunta"], historico)
        dur = time.perf_counter() - t0
        if p["tipo"] == "fora_escopo":
            ok = r.situacao in RECUSAS
        else:
            ok = r.situacao == "respondida" and all(norm(f) in norm(r.resposta) for f in p["fatos"])
        linhas.append({"id": p["id"], "tipo": p["tipo"], "contexto": p.get("contexto", ""), "pergunta": p["pergunta"],
                       "esperado": ", ".join(p["fatos"]) or "recusar", "resposta": r.resposta, "situacao": r.situacao,
                       "fontes": [f.id for f in r.fontes], "acertou": ok, "tempo_s": round(dur, 2)})
        print(p["id"], ok, r.situacao, r.resposta[:120], flush=True)
    (PASTA / "resultados_llm.json").write_text(json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    with (PASTA / "planilha_llm.csv").open("w", encoding="utf-8") as f:
        f.write("id;tipo;contexto;pergunta;esperado;resposta;situacao;acertou;tempo_s\n")
        for l in linhas:
            f.write(";".join(str(l[k]).replace(";", ",").replace("\n", " ") for k in
                             ("id", "tipo", "contexto", "pergunta", "esperado", "resposta", "situacao", "acertou", "tempo_s")) + "\n")


if __name__ == "__main__":
    main()
