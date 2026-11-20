import asyncio
import os

import edge_tts

VOZ = os.environ.get("TTS_VOZ", "pt-BR-FranciscaNeural")


class ErroTTS(Exception):
    pass


async def _sintetizar(texto: str, voz: str, velocidade: str) -> bytes:
    partes = []
    async for bloco in edge_tts.Communicate(texto, voz, rate=velocidade).stream():
        if bloco["type"] == "audio":
            partes.append(bloco["data"])
    return b"".join(partes)


def sintetizar(texto: str, voz: str = VOZ, velocidade: str = "+0%") -> bytes:
    try:
        audio = asyncio.run(_sintetizar(texto, voz, velocidade))
    except Exception as e:
        raise ErroTTS(type(e).__name__) from e
    if not audio:
        raise ErroTTS("áudio vazio")
    return audio
