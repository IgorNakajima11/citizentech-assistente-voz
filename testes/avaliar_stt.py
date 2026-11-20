import json
import re
import statistics
import sys
import time
from pathlib import Path

import jiwer
from num2words import num2words

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from voz import stt  # noqa: E402

PASTA = RAIZ / "testes" / "stt"


def normalizar(t: str) -> str:
    t = t.lower().replace("-", " ")
    t = re.sub(r"\d+", lambda m: num2words(int(m.group(0)), lang="pt_BR"), t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def main() -> None:
    itens = []
    for arq, origem in (("frases_reais.json", "real"), ("frases_sinteticas.json", "sintetico")):
        for f in json.loads((PASTA / arq).read_text(encoding="utf-8")):
            pasta = "audios_reais" if origem == "real" else "audios_sinteticos"
            voz = "Igor (gravação real)" if origem == "real" else f["voz"].replace("pt-BR-", "").replace("Neural", "")
            itens.append({**f, "origem": origem, "voz": voz, "arquivo": f"{pasta}/{f['id']}.wav"})
    linhas = []
    for motor in stt.MOTORES:
        stt.transcrever((PASTA / itens[0]["arquivo"]).read_bytes(), motor)
        if motor.startswith("groq"):
            time.sleep(3)
        for it in itens:
            audio = (PASTA / it["arquivo"]).read_bytes()
            t0 = time.perf_counter()
            hip = stt.transcrever(audio, motor)
            dur = time.perf_counter() - t0
            wer = jiwer.wer(normalizar(it["texto"]), normalizar(hip))
            linhas.append({"motor": motor, "id": it["id"], "origem": it["origem"], "voz": it["voz"], "ruido": it["ruido"],
                           "referencia": it["texto"], "transcricao": hip, "wer": round(wer, 3), "tempo_s": round(dur, 2)})
            print(motor, it["id"], round(wer, 3), round(dur, 2), hip, flush=True)
            if motor.startswith("groq"):
                time.sleep(3)
    (PASTA / "resultados_stt.json").write_text(json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    with (PASTA / "planilha_stt.csv").open("w", encoding="utf-8") as f:
        f.write("motor;id;origem;voz;ruido;referencia;transcricao;wer;tempo_s\n")
        for l in linhas:
            f.write(";".join(str(l[k]).replace(";", ",") for k in
                             ("motor", "id", "origem", "voz", "ruido", "referencia", "transcricao", "wer", "tempo_s")) + "\n")
    for motor in stt.MOTORES:
        ls = [l for l in linhas if l["motor"] == motor]
        print(motor, "WER médio", round(statistics.mean(l["wer"] for l in ls), 3),
              "tempo médio", round(statistics.mean(l["tempo_s"] for l in ls), 2))


if __name__ == "__main__":
    main()
