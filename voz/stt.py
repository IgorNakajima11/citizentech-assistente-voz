import io
import os
import time
from functools import lru_cache

import av
import httpx
import numpy as np

from rag.config import GROQ_API_KEY

MOTORES = {
    "whisper-local-small": "faster-whisper small (local, CPU)",
    "whisper-local-base": "faster-whisper base (local, CPU)",
    "groq-whisper-large-v3-turbo": "Whisper large-v3-turbo (nuvem, Groq)",
}
PADRAO = os.environ.get("STT_MOTOR", "groq-whisper-large-v3-turbo")


class ErroSTT(Exception):
    pass


@lru_cache(maxsize=2)
def _modelo_local(tamanho: str):
    from faster_whisper import WhisperModel
    return WhisperModel(tamanho, device="cpu", compute_type="int8")


def decodificar(audio: bytes) -> np.ndarray:
    amostras = []
    with av.open(io.BytesIO(audio)) as c:
        reamostrador = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for quadro in c.decode(audio=0):
            for q in reamostrador.resample(quadro):
                amostras.append(q.to_ndarray().reshape(-1))
        for q in reamostrador.resample(None):
            amostras.append(q.to_ndarray().reshape(-1))
    if not amostras:
        raise ErroSTT("áudio vazio ou inválido")
    return np.concatenate(amostras).astype(np.float32) / 32768.0


def _local(audio: bytes, tamanho: str) -> str:
    try:
        sinal = decodificar(audio)
    except av.error.FFmpegError as e:
        raise ErroSTT("formato de áudio não reconhecido") from e
    segmentos, _ = _modelo_local(tamanho).transcribe(sinal, language="pt", beam_size=5, vad_filter=True)
    return " ".join(s.text.strip() for s in segmentos).strip()


def _groq(audio: bytes, nome: str, esperas: int = 6) -> str:
    if not GROQ_API_KEY:
        raise ErroSTT("GROQ_API_KEY não configurada")
    for _ in range(esperas + 1):
        r = _groq_chamada(audio, nome)
        if r.status_code != 429:
            break
        time.sleep(min(float(r.headers.get("retry-after", "5")), 30))
    if r.status_code >= 400:
        raise ErroSTT(f"HTTP {r.status_code}")
    return r.json().get("text", "").strip()


def _groq_chamada(audio: bytes, nome: str) -> httpx.Response:
    try:
        r = httpx.post("https://api.groq.com/openai/v1/audio/transcriptions",
                       headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                       data={"model": "whisper-large-v3-turbo", "language": "pt",
                             "response_format": "json", "temperature": "0"},
                       files={"file": (nome, audio)}, timeout=60)
    except httpx.HTTPError as e:
        raise ErroSTT(type(e).__name__) from e
    return r


def transcrever(audio: bytes, motor: str = PADRAO, nome: str = "audio.wav") -> str:
    if motor == "groq-whisper-large-v3-turbo":
        return _groq(audio, nome)
    if motor.startswith("whisper-local-"):
        return _local(audio, motor.removeprefix("whisper-local-"))
    raise ErroSTT(f"motor desconhecido: {motor}")
