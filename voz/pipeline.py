import time
from dataclasses import dataclass, field

from . import fala, llm, stt, tts

MSG_NAO_ENTENDI = "Não consegui entender o áudio. Pode falar de novo, um pouco mais perto do microfone?"


@dataclass
class Turno:
    transcricao: str
    resposta_texto: str
    resposta_fala: str
    audio_resposta: bytes
    situacao: str
    fontes: list = field(default_factory=list)
    latencia: dict = field(default_factory=dict)


def processar(audio: bytes, historico: list[dict], motor_stt: str = stt.PADRAO, nome: str = "audio.wav") -> Turno:
    lat, t0 = {}, time.perf_counter()
    try:
        texto = stt.transcrever(audio, motor_stt, nome)
    except stt.ErroSTT:
        texto = ""
    lat["stt"] = time.perf_counter() - t0
    del audio

    t = time.perf_counter()
    if len(texto.split()) < 2:
        resposta = None
        resposta_texto, situacao, fontes = MSG_NAO_ENTENDI, "nao_entendeu", []
    else:
        resposta = llm.responder_turno(texto, historico)
        resposta_texto, situacao, fontes = resposta.resposta, resposta.situacao, resposta.fontes
    lat["llm"] = time.perf_counter() - t

    t = time.perf_counter()
    falado = fala.para_fala(resposta_texto)
    lat["adaptacao"] = time.perf_counter() - t

    t = time.perf_counter()
    try:
        audio_resp = tts.sintetizar(falado)
    except tts.ErroTTS:
        audio_resp = b""
    lat["tts"] = time.perf_counter() - t
    lat["total"] = time.perf_counter() - t0
    return Turno(texto, resposta_texto, falado, audio_resp, situacao, fontes, {k: round(v, 2) for k, v in lat.items()})
