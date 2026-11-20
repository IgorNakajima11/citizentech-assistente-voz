import hashlib

import streamlit as st

from rag.assistente import indice
from voz import pipeline, stt

st.set_page_config(page_title="CitizenTech por voz", layout="centered")
st.cache_resource(show_spinner="Carregando a base de conhecimento...")(indice)()
st.session_state.setdefault("consentiu", False)
st.session_state.setdefault("conversa", [])
st.session_state.setdefault("ultimo_audio", None)

st.title("CitizenTech por voz")
st.write("Fale sua dúvida sobre serviços de zeladoria da Prefeitura de São Paulo (buraco, entulho, árvore, "
         "Cata-Bagulho, dengue, sinalização). O assistente responde falando, com base nas páginas oficiais do SP156.")

if not st.session_state.consentiu:
    st.warning(
        "**Antes de começar.** Sua voz é um dado pessoal. Ao usar o assistente:\n\n"
        "- o áudio é gravado e enviado para transcrição. No modo nuvem (padrão), ele vai para a empresa Groq, nos "
        "Estados Unidos; no modo local, fica só neste computador;\n"
        "- o áudio é descartado logo depois da transcrição e nada é salvo em disco;\n"
        "- a resposta em texto é enviada ao serviço de voz da Microsoft para virar áudio;\n"
        "- CPF, telefone e e-mail são apagados do texto antes de ir para a inteligência artificial;\n"
        "- o histórico da conversa fica só nesta tela e some quando você fecha ou clica em Nova conversa.\n\n"
        "Não informe dados pessoais que não sejam necessários.")
    if st.button("Entendi e concordo", type="primary"):
        st.session_state.consentiu = True
        st.rerun()
    st.stop()

with st.sidebar:
    motor = st.radio("Transcrição da fala", list(stt.MOTORES), format_func=stt.MOTORES.get,
                     help="Nuvem é mais rápida e precisa; local não envia sua voz para fora deste computador.")
    if st.button("Nova conversa"):
        st.session_state.conversa = []
        st.session_state.ultimo_audio = None
        st.rerun()
    st.caption("Em emergência, ligue 199 (Defesa Civil), 193 (Bombeiros) ou 192 (SAMU).")

aba_mic, aba_arquivo = st.tabs(["Falar pelo microfone", "Enviar arquivo de áudio"])
with aba_mic:
    gravado = st.audio_input("Aperte para falar e aperte de novo para terminar")
with aba_arquivo:
    enviado = st.file_uploader("Arquivo de áudio (wav, mp3, ogg, m4a, webm)", type=["wav", "mp3", "ogg", "m4a", "webm"])

entrada = gravado or enviado
if entrada is not None:
    dados = entrada.getvalue()
    assinatura = hashlib.sha256(dados).hexdigest()
    if assinatura != st.session_state.ultimo_audio:
        st.session_state.ultimo_audio = assinatura
        historico = []
        for t in st.session_state.conversa[-3:]:
            historico += [{"papel": "user", "texto": t.transcricao}, {"papel": "assistant", "texto": t.resposta_texto}]
        with st.spinner("Ouvindo e preparando a resposta..."):
            turno = pipeline.processar(dados, historico, motor, getattr(entrada, "name", "audio.wav"))
        del dados
        st.session_state.conversa.append(turno)

for n, t in enumerate(reversed(st.session_state.conversa)):
    ultimo = n == 0
    with st.container(border=True):
        st.markdown(f"**Você disse:** {t.transcricao or '(não foi possível entender)'}")
        st.markdown(f"**Assistente:** {t.resposta_texto}")
        if t.audio_resposta:
            st.audio(t.audio_resposta, format="audio/mp3", autoplay=ultimo)
        else:
            st.error("Não foi possível gerar o áudio da resposta agora. A resposta está em texto acima.")
        for f in t.fontes:
            st.caption(f"Fonte: [{f.titulo}]({f.url}), atualizada em {f.atualizado_em}")
        l = t.latencia
        st.caption(f"Tempo: transcrição {l['stt']} s, resposta {l['llm']} s, adaptação {l['adaptacao']} s, "
                   f"voz {l['tts']} s. Total até começar a falar: {l['total']} s.")
