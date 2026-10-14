"""Configuração do projeto e regras da Nota Técnica nº 8/2026-DEAPS/SAPS/MS."""

from pathlib import Path
from typing import Any

Json = dict[str, Any]

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
CSV_DIR = ROOT / "data" / "csv"
PROCESSED_DIR = ROOT / "data" / "processed"
DASHBOARD_DIR = ROOT / "dashboard"

VERSAO_APP = "1.1.0"

# Versão da regra metodológica aplicada; muda quando uma nova Nota Técnica passar a valer.
METODOLOGIA = {
    "id": "NT8-2026",
    "norma": "Nota Técnica nº 8/2026-DEAPS/SAPS/MS",
    "base_legal": "Portaria GM/MS nº 3.493/2024 (alterada pelas Portarias GM/MS nº 6.907, 7.799/2025)",
    "revoga": "Nota Técnica nº 6/2025-DEAPS/SAPS/MS",
}

# Somente endpoints públicos (sem autenticação) do Siaps.
API_BASE = "https://apisiaps.saude.gov.br/api/public"
PORTAL_URL = "https://siaps.saude.gov.br/publico"

# Coletor: só fala com este host (https), sem seguir redirecionamentos.
HOST_PERMITIDO = "apisiaps.saude.gov.br"
QUADRIMESTRE_REGEX = r"^\d{4}Q[1-3]$"
MAX_RESPOSTA_BYTES = 5_000_000  # respostas reais têm poucas dezenas de KB
TIMEOUT_S = 60
TENTATIVAS = 3
INTERVALO_ENTRE_CONSULTAS_S = 1.0  # cortesia com a fonte
INTERVALO_MIN_ATUALIZACAO_S = 60  # botão "Atualizar dados": no máximo 1 coleta por minuto
LOCK_EXPIRA_S = 900  # trava de coleta esquecida (processo morto) expira em 15 min
DADOS_OBSOLETOS_APOS_DIAS = 45  # alerta quando a última coleta bem-sucedida for mais antiga
SCHEMA_VERSAO = 1  # versão do formato dos arquivos em data/

UF = "CE"
MUNICIPIO_NOME = "PACUJÁ"
MUNICIPIO_IBGE = "230990"  # código IBGE de 6 dígitos usado pelo Siaps (2309904 com DV)

# Primeiro quadrimestre exibido pelo portal público (a API ainda devolve 2025Q1, que o portal não lista).
PRIMEIRO_QUADRIMESTRE = "2025Q2"

# Conceito -> pontos (NT 8/2026, item 4.3.2)
PONTOS = {"Ótimo": 1.0, "Bom": 0.75, "Suficiente": 0.5, "Regular": 0.25}
CAMPOS_CONCEITO = {
    "Ótimo": "qtdClassificacaoOtimo",
    "Bom": "qtdClassificacaoBom",
    "Suficiente": "qtdClassificacaoSuficiente",
    "Regular": "qtdClassificacaoRegular",
}

# Período máximo de monitoramento por boa prática (NT 8/2026, Figura 2)
JANELAS = {
    "C1": "30 dias",
    "C2": "24 meses",
    "C3": "12 meses",
    "C4": "12 meses",
    "C5": "12 meses",
    "C6": "12 meses",
    "C7": "60 meses",
    "B1": "30 dias",
    "B2": "30 dias",
    "B3": "30 dias",
    "B4": "30 dias",
    "B5": "30 dias",
    "B6": "30 dias",
    "M1": "4 meses",
    "M2": "4 meses",
}

# coTipoIndicador (Siaps) -> (código NT, peso NT 4.3.1 / 4.3.3, rótulo curto)
INDICADORES = {
    "eSF": {
        110: ("C1", 1, "Mais Acesso à APS"),
        108: ("C2", 2, "Desenvolvimento infantil"),
        107: ("C3", 2, "Gestação e puerpério"),
        105: ("C4", 1, "Pessoa com diabetes"),
        104: ("C5", 1, "Pessoa com hipertensão"),
        106: ("C6", 1, "Pessoa idosa"),
        109: ("C7", 2, "Mulher / prevenção do câncer"),
    },
    "eSB": {
        111: ("B1", 2, "1ª consulta odontológica programada"),
        112: ("B2", 2, "Tratamento concluído"),
        113: ("B3", 2, "Taxa de exodontias"),
        114: ("B4", 1, "Escovação supervisionada"),
        115: ("B5", 2, "Procedimentos preventivos"),
        116: ("B6", 1, "Tratamento restaurador atraumático"),
    },
    "eMulti": {
        117: ("M1", 6, "Atendimentos da eMulti por pessoa"),
        118: ("M2", 4, "Ações interprofissionais"),
    },
}
# eAP segue a mesma metodologia da eSF (mesmos indicadores C1-C7 e pesos)
INDICADORES["eAP"] = INDICADORES["eSF"]


# Classificação da Nota Final do Componente III (NT 8/2026, Quadro 6)
def classificar_componente_iii(nota: float) -> str:
    if nota > 7.5:
        return "Ótimo"
    if nota >= 5:
        return "Bom"
    if nota > 2.5:
        return "Suficiente"
    return "Regular"


def manifesto_path() -> Path:
    return RAW_DIR.parent / "manifest.json"


def revisoes_dir() -> Path:
    return RAW_DIR / "revisoes"


def lock_path() -> Path:
    return RAW_DIR.parent / ".coleta.lock"
