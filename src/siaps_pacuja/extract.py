"""Extração: descobre quadrimestres publicados, baixa os de Pacujá e grava JSON bruto + CSV."""

import csv
import json
import logging

from . import client, config
from .config import Json

log = logging.getLogger("siaps")

SECOES = {
    "classificacao_final": "classificacaoFinalComponente",
    "indicadores_qualidade": "conceitoPorIndicadorQualidade",
    "dimensoes_cvat": "classificacaoFinalPorDimensaoCvat",
}


# Campos mínimos que o restante do pipeline usa; se a API mudar, falhamos alto em vez de gerar painel errado.
CAMPOS_OBRIGATORIOS = {
    "classificacaoFinalComponente": {
        "nuQuadrimestre",
        "sgUf",
        "coMunicipioIbge",
        "sgEquipe",
        "tipoOrigem",
        "totalEquipesValidasParaComponente",
        *config.CAMPOS_CONCEITO.values(),
    },
    "conceitoPorIndicadorQualidade": {
        "nuQuadrimestre",
        "sgUf",
        "coMunicipioIbge",
        "sgEquipe",
        "coTipoIndicador",
        "noIndicador",
        *config.CAMPOS_CONCEITO.values(),
    },
    "classificacaoFinalPorDimensaoCvat": {
        "nuQuadrimestre",
        "sgUf",
        "coMunicipioIbge",
        "sgEquipe",
        "coTipoIndicador",
        "noDimensao",
        *config.CAMPOS_CONCEITO.values(),
    },
}


def validar_esquema(relatorio: Json) -> Json:
    """Detecta mudança de formato da API e valida tipos básicos das contagens."""
    for secao, campos in CAMPOS_OBRIGATORIOS.items():
        linhas = relatorio.get(secao, [])
        if not isinstance(linhas, list):
            raise ValueError(f"Esquema inesperado: '{secao}' deveria ser lista")
        for linha in linhas:
            faltando = campos - set(linha)
            if faltando:
                raise ValueError(f"Esquema mudou em '{secao}': faltam {sorted(faltando)}")
            for campo in config.CAMPOS_CONCEITO.values():
                if not isinstance(linha[campo], int) or linha[campo] < 0:
                    raise ValueError(f"Valor inválido em '{secao}.{campo}': {linha[campo]!r}")
    return relatorio


def _so_pacuja(relatorio: Json) -> Json:
    """Garante que nada além de Pacujá/CE entre no projeto."""
    for secao in SECOES.values():
        for linha in relatorio.get(secao, []):
            if linha.get("coMunicipioIbge") != config.MUNICIPIO_IBGE or linha.get("sgUf") != config.UF:
                raise ValueError(f"Linha fora de Pacujá/{config.UF} em '{secao}': {linha}")
    return relatorio


def _tem_dados(relatorio: Json) -> bool:
    return any(relatorio.get(s) for s in SECOES.values())


def _gravar_csv(nu_quad: str, relatorio: Json) -> None:
    config.CSV_DIR.mkdir(parents=True, exist_ok=True)
    for nome, secao in SECOES.items():
        linhas = relatorio.get(secao, [])
        if not linhas:
            continue
        caminho = config.CSV_DIR / f"pacuja_{nu_quad}_{nome}.csv"
        # utf-8-sig + ';' => abre corretamente no Excel em português
        with caminho.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()), delimiter=";")
            w.writeheader()
            w.writerows(linhas)


def atualizar() -> list[str]:
    """Baixa todos os quadrimestres públicos com dados. Devolve os ids que mudaram/novos."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    alterados = []
    for quad in client.listar_quadrimestres():
        nu = quad["nuCompetencia"]
        if nu < config.PRIMEIRO_QUADRIMESTRE:
            continue
        relatorio = client.buscar_quadrimestre(nu)
        if not _tem_dados(relatorio):
            log.info("%s (%s): sem dados publicados para Pacujá — ignorado", nu, quad["competencia"])
            continue
        relatorio = validar_esquema(_so_pacuja(relatorio))
        relatorio["_meta"] = {"nuQuadrimestre": nu, "descricao": quad["competencia"]}
        novo = json.dumps(relatorio, ensure_ascii=False, indent=2, sort_keys=True)
        destino = config.RAW_DIR / f"{nu}.json"
        antigo = destino.read_text(encoding="utf-8") if destino.exists() else None
        if antigo != novo:
            destino.write_text(novo, encoding="utf-8")
            alterados.append(nu)
            log.info("%s: %s", nu, "novo" if antigo is None else "atualizado")
        else:
            log.info("%s: sem alterações", nu)
        _gravar_csv(nu, relatorio)
    return alterados
