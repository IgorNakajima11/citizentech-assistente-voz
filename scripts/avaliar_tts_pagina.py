import csv
import json
from pathlib import Path

import streamlit as st

PASTA = Path(__file__).resolve().parents[1] / "testes" / "tts"
ITENS = json.loads((PASTA / "itens_tts.json").read_text(encoding="utf-8"))
PLANILHA = PASTA / "planilha_tts.csv"

st.set_page_config(page_title="Avaliar a voz do assistente")
st.title("Avaliação da voz do assistente")
avaliador = st.text_input("Seu nome ou apelido (avaliador)")
st.write("Ouça cada áudio e dê uma nota de 1 a 5. **Naturalidade:** parece uma pessoa falando? "
         "**Clareza:** dá para entender todas as palavras?")
notas = {}
for it in ITENS:
    st.subheader(it["id"])
    st.audio(str(PASTA / f"{it['id']}.mp3"))
    c1, c2 = st.columns(2)
    notas[it["id"]] = (c1.slider("Naturalidade", 1, 5, 3, key=f"n{it['id']}"),
                       c2.slider("Clareza", 1, 5, 3, key=f"c{it['id']}"))
if st.button("Salvar minhas notas", type="primary", disabled=not avaliador.strip()):
    novo = not PLANILHA.exists()
    with PLANILHA.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if novo:
            w.writerow(["avaliador", "audio", "naturalidade", "clareza"])
        for i, (n, c) in notas.items():
            w.writerow([avaliador.strip(), i, n, c])
    st.success("Notas salvas. Obrigado!")
