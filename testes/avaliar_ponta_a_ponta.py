import json
import statistics
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from voz import pipeline, tts  # noqa: E402

PASTA = RAIZ / "testes" / "ponta_a_ponta"
VOZ_CIDADAO = "pt-BR-AntonioNeural"


def main() -> None:
    conversas = json.loads((PASTA / "conversas.json").read_text(encoding="utf-8"))
    linhas = []
    for c, turnos in enumerate(conversas, 1):
        historico = []
        for n, fala in enumerate(turnos, 1):
            audio = tts.sintetizar(fala, voz=VOZ_CIDADAO)
            t = pipeline.processar(audio, historico, nome="pergunta.mp3")
            historico += [{"papel": "user", "texto": t.transcricao}, {"papel": "assistant", "texto": t.resposta_texto}]
            linhas.append({"conversa": c, "turno": n, "fala_cidadao": fala, "transcricao": t.transcricao,
                           "resposta": t.resposta_texto, "resposta_falada": t.resposta_fala, "situacao": t.situacao,
                           **{f"lat_{k}": v for k, v in t.latencia.items()}})
            print(c, n, t.situacao, t.latencia, t.resposta_texto[:90], flush=True)
    (PASTA / "resultados_ponta_a_ponta.json").write_text(json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    campos = list(linhas[0])
    with (PASTA / "planilha_ponta_a_ponta.csv").open("w", encoding="utf-8") as f:
        f.write(";".join(campos) + "\n")
        for l in linhas:
            f.write(";".join(str(l[k]).replace(";", ",").replace("\n", " ") for k in campos) + "\n")
    for k in ("stt", "llm", "adaptacao", "tts", "total"):
        v = [l[f"lat_{k}"] for l in linhas]
        print(k, "média", round(statistics.mean(v), 2), "mediana", round(statistics.median(v), 2), "máx", max(v))


if __name__ == "__main__":
    main()
