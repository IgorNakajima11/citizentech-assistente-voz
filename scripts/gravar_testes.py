import json
from pathlib import Path

import streamlit as st

PASTA = Path(__file__).resolve().parents[1] / "testes" / "stt"
FRASES = json.loads((PASTA / "frases_reais.json").read_text(encoding="utf-8"))
DESTINO = PASTA / "audios_reais"
DESTINO.mkdir(exist_ok=True)

st.set_page_config(page_title="Gravar áudios de teste")
st.title("Gravação dos áudios de teste do STT")
st.info("Estes áudios são só para medir o reconhecimento de fala (WER) e ficam no repositório como material de teste. "
        "Ao gravar, você concorda com esse uso da sua voz.")
st.write("Leia a frase exatamente como está escrita, em tom normal. Nas marcadas com BARULHO, ligue uma TV, música ou "
         "fale perto de um ventilador antes de gravar.")

for f in FRASES:
    arq = DESTINO / f"{f['id']}.wav"
    feito = arq.exists()
    st.subheader(f"{f['id']} {'(gravado)' if feito else ''}")
    st.markdown(f"**{f['texto']}**" + ("  \n:red[BARULHO DE FUNDO]" if f["ruido"] else ""))
    audio = st.audio_input("Gravar", key=f["id"], label_visibility="collapsed")
    if audio is not None:
        arq.write_bytes(audio.getvalue())
        st.success("Salvo.")
    elif feito:
        st.audio(str(arq))
