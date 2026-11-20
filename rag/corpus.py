import json
from dataclasses import dataclass

from .config import ARQUIVO_CORPUS

CATEGORIA_POR_DOCUMENTO = {
    "servico-952": "buraco_pavimentacao", "servico-3170": "buraco_pavimentacao", "servico-957": "buraco_pavimentacao",
    "servico-1071": "poda_arvore", "servico-3619": "poda_arvore", "servico-3620": "poda_arvore",
    "conteudo-3495": "poda_arvore",
    "servico-2641": "coleta_lixo", "servico-745": "coleta_lixo", "servico-751": "coleta_lixo",
    "servico-731": "coleta_lixo", "servico-915": "coleta_lixo",
    "servico-774": "transito_sinalizacao", "servico-753": "transito_sinalizacao", "servico-773": "transito_sinalizacao",
    "servico-757": "transito_sinalizacao", "servico-949": "transito_sinalizacao",
}


@dataclass(frozen=True)
class Documento:
    id: str
    titulo: str
    url: str
    data_consulta: str
    atualizado_em: str
    texto: str

    @property
    def categoria(self) -> str:
        return CATEGORIA_POR_DOCUMENTO.get(self.id, "outro")


def carregar_documentos() -> list[Documento]:
    with ARQUIVO_CORPUS.open(encoding="utf-8") as f:
        return [Documento(**json.loads(linha)) for linha in f if linha.strip()]
