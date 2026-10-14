"""Configuração do projeto e regras da Nota Técnica nº 8/2026-DEAPS/SAPS/MS."""

from pathlib import Path
from typing import Any

Json = dict[str, Any]

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
CSV_DIR = ROOT / "data" / "csv"
PROCESSED_DIR = ROOT / "data" / "processed"
DASHBOARD_DIR = ROOT / "dashboard"

# Somente endpoints públicos (sem autenticação) do Siaps.
API_BASE = "https://apisiaps.saude.gov.br/api/public"
PORTAL_URL = "https://siaps.saude.gov.br/publico"

UF = "CE"
MUNICIPIO_NOME = "PACUJÁ"
MUNICIPIO_IBGE = "230990"  # código IBGE de 6 dígitos usado pelo Siaps (2309904 com DV)

# Primeiro quadrimestre exibido pelo portal público (a API ainda devolve 2025Q1, que o portal não lista).
PRIMEIRO_QUADRIMESTRE = "2025Q2"

# Conceito -> pontos (NT 8/2026, item 4.3.2)
CONCEITOS = ("Ótimo", "Bom", "Suficiente", "Regular")
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
