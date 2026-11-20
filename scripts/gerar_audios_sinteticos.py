import io
import json
import wave
from pathlib import Path

import numpy as np

from voz import tts
from voz.stt import decodificar

PASTA = Path(__file__).resolve().parents[1] / "testes" / "stt"
SNR_DB = 5.0


def salvar_wav(caminho: Path, sinal: np.ndarray) -> None:
    pcm = (np.clip(sinal, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm.tobytes())


def ruido_de_fundo(n: int, rng: np.random.Generator) -> np.ndarray:
    branco = rng.normal(size=n)
    rosa = np.cumsum(branco)
    rosa -= np.convolve(rosa, np.ones(400) / 400, mode="same")
    murmurio = np.sin(2 * np.pi * rng.uniform(120, 250) * np.arange(n) / 16000) * (1 + np.sin(np.arange(n) / 3000))
    r = rosa / np.std(rosa) + 0.5 * murmurio
    return r / np.std(r)


def main() -> None:
    rng = np.random.default_rng(42)
    frases = json.loads((PASTA / "frases_sinteticas.json").read_text(encoding="utf-8"))
    for f in frases:
        sinal = decodificar(tts.sintetizar(f["texto"], voz=f["voz"]))
        if f["ruido"]:
            potencia = np.mean(sinal ** 2)
            sinal = sinal + ruido_de_fundo(len(sinal), rng) * np.sqrt(potencia / 10 ** (SNR_DB / 10))
            sinal = sinal / max(1.0, np.max(np.abs(sinal)))
        salvar_wav(PASTA / "audios_sinteticos" / f"{f['id']}.wav", sinal)
        print(f["id"], f["voz"], "com ruído" if f["ruido"] else "")


if __name__ == "__main__":
    main()
