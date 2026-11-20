import csv
import json
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
T = RAIZ / "testes"
SAIDA_HTML = RAIZ / "relatorio" / "relatorio.html"
SAIDA_PDF = RAIZ / "relatorio" / "Relatorio_PLN_Assistente_Voz_Igor_Nakajima_563632.pdf"
MOTORES = {"groq-whisper-large-v3-turbo": "Whisper large-v3-turbo (Groq, nuvem)",
           "whisper-local-small": "faster-whisper small (local, CPU)",
           "whisper-local-base": "faster-whisper base (local, CPU)"}


def m(v):
    return statistics.mean(v) if v else float("nan")


def pct(x):
    return f"{100 * x:.1f}%".replace(".", ",")


def num(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")


def tabela(cab, linhas):
    h = "".join(f"<th>{c}</th>" for c in cab)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def secao_stt():
    d = json.loads((T / "stt" / "resultados_stt.json").read_text(encoding="utf-8"))
    linhas = []
    for mot, nome in MOTORES.items():
        g = [l for l in d if l["motor"] == mot]
        linhas.append([nome, pct(m([l["wer"] for l in g])), pct(m([l["wer"] for l in g if l["origem"] == "real"])),
                       pct(m([l["wer"] for l in g if l["origem"] == "sintetico"])),
                       pct(m([l["wer"] for l in g if l["ruido"]])), pct(m([l["wer"] for l in g if not l["ruido"]])),
                       num(m([l["tempo_s"] for l in g])) + " s"])
    geral = tabela(["Motor", "WER geral (20)", "Voz real (10)", "Vozes sintéticas (10)", "Com ruído (5)",
                    "Sem ruído (15)", "Tempo médio"], linhas)
    por_voz = defaultdict(list)
    for l in d:
        if l["motor"] == "groq-whisper-large-v3-turbo":
            por_voz[l["voz"]].append(l["wer"])
    voz = tabela(["Voz (motor final)", "Áudios", "WER médio"],
                 [[v, len(w), pct(m(w))] for v, w in por_voz.items()])
    reais = tabela(["Id", "Frase lida", "Transcrição (motor final)", "WER"],
                   [[l["id"], l["referencia"], l["transcricao"], pct(l["wer"])] for l in d
                    if l["motor"] == "groq-whisper-large-v3-turbo" and l["origem"] == "real"])
    return geral, voz, reais


def secao_llm():
    d = json.loads((T / "llm" / "resultados_llm.json").read_text(encoding="utf-8"))
    nomes = {"respondivel": "Perguntas do tema", "continuacao": "Continuação", "fora_escopo": "Fora do escopo"}
    linhas = []
    for tipo, nome in nomes.items():
        g = [l for l in d if l["tipo"] == tipo]
        linhas.append([nome, len(g), sum(l["acertou"] for l in g), pct(m([l["acertou"] for l in g]))])
    linhas.append(["<b>Total</b>", len(d), sum(l["acertou"] for l in d), pct(m([l["acertou"] for l in d]))])
    resumo = tabela(["Tipo", "Perguntas", "Corretas / recusas adequadas", "Taxa"], linhas)
    falhas = tabela(["Id", "Pergunta", "Esperado", "Resposta"],
                    [[l["id"], (l["contexto"] + " / " if l["contexto"] else "") + l["pergunta"], l["esperado"], l["resposta"]]
                     for l in d if not l["acertou"]])
    return resumo, falhas, d


def secao_tts():
    arq = T / "tts" / "planilha_tts.csv"
    if not arq.exists():
        return None, 0
    with arq.open(encoding="utf-8") as f:
        notas = list(csv.DictReader(f, delimiter=";"))
    avaliadores = sorted({n["avaliador"] for n in notas})
    por_audio = defaultdict(lambda: ([], []))
    for n in notas:
        por_audio[n["audio"]][0].append(int(n["naturalidade"]))
        por_audio[n["audio"]][1].append(int(n["clareza"]))
    itens = {i["id"]: i for i in json.loads((T / "tts" / "itens_tts.json").read_text(encoding="utf-8"))}
    linhas = [[a, itens[a]["texto_falado"], num(m(n), 1), num(m(c), 1)] for a, (n, c) in sorted(por_audio.items())]
    linhas.append(["<b>Média</b>", "", num(m([int(n["naturalidade"]) for n in notas]), 2),
                   num(m([int(n["clareza"]) for n in notas]), 2)])
    return tabela(["Áudio", "Texto falado (após a adaptação para fala)", "Naturalidade (1 a 5)", "Clareza (1 a 5)"], linhas), len(avaliadores)


def secao_e2e(nome):
    arq = T / "ponta_a_ponta" / nome
    if not arq.exists():
        return None, None, None
    d = json.loads(arq.read_text(encoding="utf-8"))
    etapas = [("stt", "Transcrição (STT)"), ("llm", "Busca + LLM"), ("adaptacao", "Adaptação para fala"),
              ("tts", "Síntese de voz (TTS)"), ("total", "Total até a resposta falada")]
    lat = tabela(["Etapa", "Média", "Mediana", "Máximo"],
                 [[n, num(m([l[f"lat_{k}"] for l in d])) + " s", num(statistics.median([l[f"lat_{k}"] for l in d])) + " s",
                   num(max(l[f"lat_{k}"] for l in d)) + " s"] for k, n in etapas])
    conv = tabela(["Conv.", "Turno", "Cidadão falou", "Transcrição", "Resposta do assistente", "Situação", "Total"],
                  [[l["conversa"], l["turno"], l["fala_cidadao"], l["transcricao"], l["resposta"], l["situacao"],
                    num(l["lat_total"]) + " s"] for l in d])
    return lat, conv, d


DIAGRAMA = """<svg viewBox="0 0 760 210" xmlns="http://www.w3.org/2000/svg" font-family="Arial" font-size="12">
<defs><marker id="s" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#333"/></marker></defs>
<g fill="#fff" stroke="#333">
<rect x="5" y="20" width="110" height="50" rx="6"/><rect x="150" y="20" width="120" height="50" rx="6"/>
<rect x="305" y="20" width="140" height="50" rx="6"/><rect x="480" y="20" width="130" height="50" rx="6"/>
<rect x="640" y="20" width="110" height="50" rx="6"/><rect x="305" y="120" width="140" height="70" rx="6"/>
<rect x="480" y="120" width="130" height="50" rx="6"/></g>
<g text-anchor="middle"><text x="60" y="42">Microfone ou</text><text x="60" y="58">arquivo de áudio</text>
<text x="210" y="42">STT (voz/stt.py)</text><text x="210" y="58">Whisper turbo</text>
<text x="375" y="42">LLM (voz/llm.py)</text><text x="375" y="58">RAG + gpt-oss-20b</text>
<text x="545" y="42">Adaptação para fala</text><text x="545" y="58">(voz/fala.py)</text>
<text x="695" y="42">TTS (voz/tts.py)</text><text x="695" y="58">Francisca, pt-BR</text>
<text x="375" y="142">Base: 22 páginas do</text><text x="375" y="158">SP156 (busca híbrida</text><text x="375" y="174">BM25 + embeddings)</text>
<text x="545" y="142">Memória: últimos</text><text x="545" y="158">3 turnos da conversa</text></g>
<g stroke="#333" marker-end="url(#s)"><line x1="115" y1="45" x2="148" y2="45"/><line x1="270" y1="45" x2="303" y2="45"/>
<line x1="445" y1="45" x2="478" y2="45"/><line x1="610" y1="45" x2="638" y2="45"/><line x1="375" y1="118" x2="375" y2="72"/>
<line x1="480" y1="140" x2="447" y2="70"/></g>
<text x="380" y="205" text-anchor="middle">Tela Streamlit (app.py): mostra transcrição, resposta em texto, áudio, fontes e tempo de cada etapa</text>
</svg>"""


def main():
    stt_geral, stt_voz, stt_reais = secao_stt()
    llm_resumo, llm_falhas, llm = secao_llm()
    v1 = json.loads((T / "llm" / "resultados_llm_v1.json").read_text(encoding="utf-8"))
    llm_v1 = f"{sum(l['acertou'] for l in v1)}/{len(v1)}"
    tts_tab, n_aval = secao_tts()
    lat, conv, e2e = secao_e2e("resultados_ponta_a_ponta_v1.json")
    acerto_llm = pct(m([l["acertou"] for l in llm]))
    html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Relatório PLN</title><style>
@page {{ size: A4; margin: 3cm 2cm 2cm 3cm; }}
body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #000; }}
h1 {{ font-size: 13pt; text-transform: uppercase; margin-top: 18pt; }} h2 {{ font-size: 12pt; margin-top: 14pt; }}
p {{ text-align: justify; margin: 0 0 8pt; }}
table {{ border-collapse: collapse; width: 100%; font-size: 9pt; margin: 6pt 0 4pt; page-break-inside: auto; }}
th, td {{ border: 1px solid #555; padding: 3pt 4pt; vertical-align: top; text-align: left; }} th {{ background: #eee; }}
.capa {{ height: 24cm; display: flex; flex-direction: column; justify-content: space-between; text-align: center; page-break-after: always; }}
.capa .t {{ font-size: 15pt; font-weight: bold; text-transform: uppercase; }}
.fonte {{ font-size: 9pt; }} ul {{ margin: 0 0 8pt; }} li {{ margin-bottom: 3pt; }}
svg {{ width: 100%; margin: 6pt 0; }}
</style></head><body>
<div class="capa"><div><b>FIAP - FACULDADE DE INFORMÁTICA E ADMINISTRAÇÃO PAULISTA</b><br>Processamento de Linguagem Natural, Chatbots & Virtual Agents</div>
<div><b>IGOR THIAGO NAKAJIMA VIEIRA</b><br>RM 563632</div>
<div class="t">CitizenTech por voz: assistente de voz para dúvidas sobre zeladoria urbana em São Paulo</div>
<div>Global Solution 2026.2<br>Trabalho individual</div><div>São Paulo<br>2026</div></div>

<h1>1 Problema e persona</h1>
<p>Para pedir um serviço de zeladoria em São Paulo (tapa-buraco, remoção de entulho, poda de árvore), o cidadão precisa
achar o serviço certo entre mais de mil opções do portal SP156, ler a página e entender prazos, custos e exigências. Isso
exclui quem tem dificuldade com interfaces de texto.</p>
<p><b>Persona:</b> Dona Cida, 68 anos, moradora da zona leste, com baixa visão e pouca familiaridade com celular. Ela quer
saber quanto tempo a Prefeitura leva para tapar o buraco na frente de casa e se precisa pagar. Hoje depende de um parente
para pesquisar. Com o assistente, ela aperta um botão, pergunta falando e ouve a resposta, que também aparece em texto
grande na tela. Pode fazer perguntas de continuação ("e é pago?") como numa conversa.</p>

<h1>2 ODS relacionados</h1>
<p><b>ODS 10 (Redução das desigualdades), meta 10.2:</b> inclusão de idosos, pessoas com deficiência visual ou motora e pessoas
com baixa alfabetização no acesso a serviços públicos. <b>ODS 11 (Cidades e comunidades sustentáveis):</b> facilita o pedido
de manutenção urbana (vias, calçadas, árvores, resíduos), que afeta segurança e qualidade de vida no bairro.</p>

<h1>3 Arquitetura</h1>
<p>O fluxo é microfone, STT, LLM, adaptação para fala, TTS e alto-falante, repetido a cada turno. Cada etapa é um módulo
separado com uma função de entrada e saída simples (<i>transcrever</i>, <i>responder_turno</i>, <i>para_fala</i>,
<i>sintetizar</i>), então trocar um componente não exige mudar os outros. Prova disso: o STT tem três motores
selecionáveis na tela sem nenhuma mudança no resto do fluxo.</p>
{DIAGRAMA}
<p class="fonte">Figura 1: arquitetura do assistente. Fonte: elaborada pelo autor.</p>
<p><b>Base de conhecimento (RAG):</b> 22 páginas oficiais da Carta de Serviços do SP156, coletadas em 19/11/2026 e
reaproveitadas do trabalho da disciplina Generative AI. Os trechos são separados por seção da página (O que é, Prazo,
Taxas, Canais...), buscados de forma híbrida (BM25 + embeddings multilíngues) e enviados ao LLM, que só pode responder com
base neles e deve citar a fonte. Escolhemos RAG em vez de colocar tudo no prompt (as 22 páginas somam cerca de 85 mil
caracteres, acima do limite de tokens por minuto da camada gratuita) e em vez de fine-tuning (prazos e regras mudam; com RAG
basta coletar as páginas de novo, e cada resposta pode ser conferida na fonte).</p>
<p><b>Memória:</b> os últimos 3 turnos vão ao LLM como histórico. Em perguntas curtas de continuação, a busca junta as
duas últimas falas do cidadão com a pergunta atual, para não perder o assunto.</p>
<p><b>Adaptação para fala:</b> antes do TTS, o texto perde markdown, links e emojis; números viram palavras ("45 dias" para
"quarenta e cinco dias"), valores em reais e datas são escritos por extenso, telefones de emergência são lidos dígito a
dígito ("um nove nove") e siglas viram forma pronunciável ("SP156" para "S P cento e cinquenta e seis", "CET" para "C E T").
A resposta é limitada a 4 frases.</p>

<h1>4 Justificativa das escolhas</h1>
{tabela(["Etapa", "Escolha final", "Versão e licença", "Por quê"], [
 ["STT", "Whisper large-v3-turbo na Groq (nuvem)", "Pesos MIT (OpenAI); API Groq",
  "Menor erro e menor tempo na comparação da seção 5.1. Opção local (faster-whisper 1.2.1, MIT) disponível na tela para quem não quer enviar a voz para fora"],
 ["LLM", "gpt-oss-20b na Groq, temperatura 0 (versão 1: gpt-oss-120b)", "Apache 2.0",
  "Mesma família, saída JSON nativa, rápido; trocado porque a cota diária gratuita do 120b (200 mil tokens) acabou durante os testes; acerto igual nas 30 perguntas (seção 5.3)"],
 ["Embeddings", "paraphrase-multilingual-MiniLM-L12-v2 via fastembed 0.9.1", "Apache 2.0", "Multilíngue, leve, roda em CPU sem enviar texto para fora"],
 ["TTS", "edge-tts 7.3.1, voz pt-BR-FranciscaNeural", "Biblioteca LGPL-3.0; voz sintética pronta da Microsoft",
  "Voz natural em português do Brasil, sem GPU; voz sintética pronta, sem clonagem de voz real"],
 ["Interface", "Streamlit 1.67.0", "Apache 2.0", "Gravação pelo microfone (st.audio_input) e upload de arquivo na mesma tela"],
])}
<p><b>Nuvem ou local:</b> a escolha final é nuvem para STT, LLM e TTS, por <b>latência</b> (o modelo local mais preciso levou
cerca de 5 vezes mais tempo no STT e não há GPU na máquina) e <b>custo</b> (camadas gratuitas). O custo dessa escolha é a
<b>privacidade</b>: a voz vai para a Groq. Por isso o aviso de consentimento diz isso explicitamente, e a tela oferece o modo
local. A desvantagem de <b>disponibilidade</b> é depender de internet; sem ela, o STT local continua funcionando, mas LLM e TTS
não.</p>

<h1>5 Resultados das métricas</h1>
<h2>5.1 STT: comparação de três motores (WER com jiwer)</h2>
<p>20 áudios: 10 gravados pelo autor com microfone de notebook (3 com TV ou música ao fundo) e 10 gerados com 3 vozes
sintéticas diferentes (Antonio, Thalita e Francisca), 2 deles com ruído adicionado a 5 dB de relação sinal-ruído. Trabalho
individual: as 3 vozes adicionais são sintéticas, e não pessoas reais; isso é uma limitação discutida abaixo. Antes do WER,
texto em minúsculas, sem pontuação e com números por extenso nos dois lados.</p>
{stt_geral}
<p>O Whisper large-v3-turbo na nuvem teve o menor erro e o menor tempo, e foi o escolhido. O faster-whisper small local é a
alternativa para privacidade, com erro maior e cerca de 5 vezes mais tempo em CPU.</p>
<p><b>Correção feita durante os testes:</b> a primeira versão passava ao Whisper uma "dica" com nomes de serviços. Nos áudios
reais, a dica vazou para a transcrição ("Uma árvore caiu na rua" virou "Serviços da Prefeitura de Sônia Ruberti"). A dica
foi removida; os números acima já são sem ela.</p>
<h2>5.2 Análise de viés do STT</h2>
{stt_voz}
<p>O erro na voz real do autor é muito maior que nas vozes sintéticas, em todos os motores. As vozes sintéticas são
"de estúdio": dicção perfeita, sem eco e sem variação de ritmo. A gravação real tem microfone de notebook, eco do cômodo e
fala natural. Isso indica que avaliar só com voz sintética superestima a qualidade e que o assistente tende a funcionar pior
justamente para o público real: pessoas com dicção menos clara, sotaques regionais, idosos ou microfones ruins. Com uma só
pessoa real não é possível separar o efeito do falante do efeito do microfone; uma avaliação justa exigiria vozes de vários
gêneros, idades e sotaques. Como mitigação, o assistente mostra a transcrição na tela para conferência e, se entender menos
de duas palavras, pede para repetir em vez de responder a algo que não ouviu.</p>
{stt_reais}

<h2>5.3 LLM: 30 perguntas do tema</h2>
<p>20 perguntas do tema, 5 de continuação (com uma pergunta de contexto antes) e 5 fora do escopo (saúde, jurídico, IPTU,
restaurante e uma tentativa de desviar o assistente). Correta = resposta com o fato esperado (prazo, custo, documento),
conferido no texto das páginas oficiais. Recusa adequada = o assistente não responde e orienta a procurar o canal certo.</p>
{llm_resumo}
<p>Taxa geral de {acerto_llm} na versão final, com gpt-oss-20b (versão 1, com gpt-oss-120b: {llm_v1}). <b>Comparação
dos dois LLMs:</b> o acerto total foi o mesmo, mas o tipo de erro mudou. Com o 120b, todas as falhas foram abstenções
seguras. Com o 20b, uma falha foi uma resposta errada (L16: atribuiu o tempo do semáforo à "Prefeitura", quando a página
diz CET). O 20b foi mantido por necessidade (cota diária do 120b esgotada), e a recomendação para produção é o 120b. Da
versão 1 para a final também mudaram a memória (a busca de perguntas curtas junta as duas últimas falas) e as recusas, que
passaram a encaminhar ao órgão certo: dor no peito vai para o SAMU (192), assunto jurídico para a Defensoria Pública,
violência para a Polícia (190), em vez do genérico "ligue 156". As outras 4 falhas da versão final são abstenções ("não encontrei, ligue 156"), sem prazo
ou custo inventado; a causa é a recuperação, que não trouxe o trecho certo (por exemplo, a seção de taxas da remoção de
entulho). Para o cidadão, nesses casos a falha é ficar sem resposta, não receber uma informação errada.</p>
{llm_falhas}

<h2>5.4 TTS: naturalidade e clareza</h2>
{tts_tab if tts_tab else "<p>Planilha de notas ainda não preenchida.</p>"}
<p>Avaliadores: {n_aval} (o autor). O enunciado pede pelo menos 3; por ser trabalho individual e pelo prazo, só o autor
avaliou, e as notas não representam a percepção de outras pessoas, em especial do público-alvo idoso. As notas ficaram
abaixo do esperado (média perto de 3), inclusive em frases curtas e simples, como a do áudio tts01. Como o motivo de cada
nota não foi registrado na avaliação, as causas abaixo são <b>hipóteses</b>, não constatações: (1) a voz sintética
escolhida pode soar artificial ou rápida para esse ouvinte; (2) respostas longas (tts04, tts07, tts09 e tts10 têm mais de 120
caracteres) ficam difíceis de acompanhar só pelo ouvido; (3) termos como "tapa-buraco", "S P cento e cinquenta e seis" e
números de telefone lidos dígito a dígito podem soar estranhos. Próximo passo: repetir a avaliação com 3 pessoas, comparar
outra voz (pt-BR-ThalitaMultilingualNeural) e velocidade 10% menor, e registrar o motivo junto de cada nota.</p>

<h2>5.5 Ponta a ponta: 10 conversas de 3 turnos</h2>
<p>10 conversas completas por voz (30 turnos): a fala do cidadão foi gerada com a voz sintética Antonio, passou pelo fluxo
inteiro (STT na nuvem, LLM, adaptação e TTS) e o tempo de cada etapa foi medido. Cada conversa tem pergunta de continuação,
e três delas terminam com um pedido fora do escopo (saúde, restaurante e processo judicial).</p>
<p><b>Importante:</b> esta rodada foi feita com a versão 1 do código e o gpt-oss-120b, antes das duas correções descritas a
seguir e da troca para o gpt-oss-20b; por falta de tempo, a rodada com a versão final não foi concluída. Os tempos de STT,
adaptação e TTS não dependem dessas mudanças; o do LLM pode variar um pouco com o modelo menor.</p>
{lat if lat else ""}
{("<p><b>Correção de memória:</b> na primeira rodada (versão 1), a busca de uma pergunta curta de continuação juntava só a fala anterior. No terceiro turno de uma conversa (\"E eu preciso pagar alguma coisa?\" depois de \"E quanto tempo demora?\"), o assunto tapa-buraco se perdia e a resposta falou de outro serviço. A busca passou a juntar as duas últimas falas. Também nesta rodada, \"dor no peito, que remédio eu tomo?\" recebeu o genérico \"ligue 156\"; por isso as recusas passaram a encaminhar ao SAMU (192), à Defensoria Pública ou à Polícia (190), como mostra a seção 5.3.</p>")}
<p>A etapa mais lenta é a síntese de voz: o edge-tts só devolve o áudio quando termina de gerar. Uma melhoria direta é
começar a tocar o áudio enquanto ele é gerado (streaming) ou sintetizar frase por frase.</p>
{conv if conv else ""}

<h1>6 Cuidados com a LGPD e ética</h1>
<ul>
<li><b>Consentimento:</b> antes do primeiro uso, a tela explica que a voz é gravada, que vai para a Groq (EUA) no modo nuvem,
que o texto da resposta vai para o serviço de voz da Microsoft e que nada fica salvo; só depois do "Entendi e concordo" o
microfone aparece.</li>
<li><b>Retenção mínima:</b> o áudio é processado em memória e descartado logo após a transcrição; nada é gravado em disco.
O histórico de texto fica só na sessão da tela e some em "Nova conversa" ou ao fechar. Os únicos áudios guardados são os de
teste, gravados pelo próprio autor com consentimento, para a avaliação de WER.</li>
<li><b>Dados pessoais no texto:</b> CPF, telefone e e-mail são mascarados antes de ir ao LLM.</li>
<li><b>Limites:</b> o assistente só responde sobre zeladoria com base nas páginas oficiais; recusa saúde, assuntos jurídicos
e outros temas, e em emergência orienta ligar 199, 193 ou 192 (5 de 5 recusas adequadas na seção 5.3).</li>
<li><b>Alucinação:</b> sem trecho relevante, o assistente diz que não encontrou e indica o 156; respostas sem citação válida
ou com número que não aparece na fonte são bloqueadas.</li>
<li><b>Voz:</b> só vozes sintéticas prontas; nenhuma clonagem de voz real.</li>
<li><b>Viés:</b> ver seção 5.2; o STT erra mais com voz real do que com voz sintética.</li>
</ul>

<h1>7 Limitações e melhorias futuras</h1>
<ul>
<li>Áudios de teste reais de uma só pessoa; vozes adicionais sintéticas. Melhoria: coletar vozes de idosos e de sotaques
diferentes, com consentimento, e medir o WER por grupo.</li>
<li>Avaliação do TTS com um só avaliador. Melhoria: pelo menos 3 pessoas, incluindo alguém do público-alvo.</li>
<li>Dependência de internet e de serviços externos (Groq e Microsoft), com limite de uso na camada gratuita; o código espera e
tenta de novo quando bate no limite. Melhoria: modo totalmente local com Whisper, um LLM pequeno via Ollama e Piper para voz,
quando houver GPU.</li>
<li>A base cobre 22 serviços de zeladoria de São Paulo; fora disso o assistente se abstém. As páginas mudam: a coleta precisa
ser refeita periodicamente.</li>
<li>Latência dominada pelo TTS. Melhoria: tocar o áudio em streaming, frase por frase.</li>
<li>Gravação por botão (aperta para falar); detecção automática de voz não foi implementada.</li>
</ul>

<h1>Referências</h1>
<p class="fonte">PREFEITURA DE SÃO PAULO. Portal de Atendimento SP156: Carta de Serviços. Disponível em:
https://sp156.prefeitura.sp.gov.br. Acesso em: 19 nov. 2026.<br>
RADFORD, A. et al. Robust Speech Recognition via Large-Scale Weak Supervision (Whisper). OpenAI, 2022.<br>
SYSTRAN. faster-whisper. Disponível em: https://github.com/SYSTRAN/faster-whisper. Acesso em: 19 nov. 2026.<br>
ORGANIZAÇÃO DAS NAÇÕES UNIDAS. Objetivos de Desenvolvimento Sustentável. Disponível em: https://brasil.un.org/pt-br/sdgs.
Acesso em: 19 nov. 2026.<br>
BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD).</p>
</body></html>"""
    SAIDA_HTML.write_text(html, encoding="utf-8")
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={SAIDA_PDF}", SAIDA_HTML.as_uri()], check=True, capture_output=True)
    print(SAIDA_PDF)


if __name__ == "__main__":
    main()
