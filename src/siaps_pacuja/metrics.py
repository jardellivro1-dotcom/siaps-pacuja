"""Métricas conforme a NT 8/2026: pontos por conceito x pesos -> nota do Componente III.

Limite dos dados públicos: o Siaps público traz, por quadrimestre, quantas equipes de Pacujá
ficaram em cada conceito por indicador (o resultado quadrimestral já é a média dos meses).
Valores mensais e notas por equipe ficam na área restrita e NÃO são usados aqui.
Como a nota final é linear (soma de peso x pontos), a **nota média das equipes** do município
é calculada exatamente a partir das contagens: nota_media = soma(peso x pontuação_média).
"""

import json
from collections import defaultdict

from . import config
from .config import Json

LABEL_MES = {"Q1": "1º", "Q2": "2º", "Q3": "3º"}


def _dist(linha: Json) -> Json:
    return {c: int(linha.get(campo, 0) or 0) for c, campo in config.CAMPOS_CONCEITO.items()}


def _pontuacao_media(dist: dict[str, int]) -> float | None:
    n = sum(dist.values())
    if not n:
        return None
    return sum(dist[c] * config.PONTOS[c] for c in dist) / n


def _rotulo(nu: str) -> str:
    return f"{LABEL_MES[nu[4:]]} quad/{nu[:4]}"


def _indicador(equipe: str, linha: Json) -> Json | None:
    info = config.INDICADORES.get(equipe, {}).get(linha["coTipoIndicador"])
    if not info:
        return None
    codigo, peso, curto = info
    d = _dist(linha)
    pm = _pontuacao_media(d)
    return {
        "codigo": codigo,
        "nome": linha["noIndicador"],
        "curto": curto,
        "peso": peso,
        "janela": config.JANELAS[codigo],
        "dist": d,
        "equipes": sum(d.values()),
        "pontuacaoMedia": pm,
        "contribuicao": None if pm is None else round(pm * peso, 4),
        # pontos que ainda podem ser ganhos se todas as equipes chegassem a "Ótimo"
        "potencial": None if pm is None else round((1 - pm) * peso, 4),
    }


def _equipe_qualidade(equipe: str, linhas_ind: list[Json], linha_final: Json | None) -> Json:
    indicadores = [i for i in (_indicador(equipe, linha) for linha in linhas_ind) if i]
    indicadores.sort(key=lambda i: (i["codigo"][0], int(i["codigo"][1:])))
    validos = [i for i in indicadores if i["pontuacaoMedia"] is not None]
    nota = round(sum(i["contribuicao"] for i in validos), 2) if validos else None
    return {
        "equipes": linha_final["totalEquipesValidasParaComponente"] if linha_final else None,
        "distFinal": _dist(linha_final) if linha_final else None,
        "notaMedia": nota,
        "classificacaoNotaMedia": config.classificar_componente_iii(nota) if nota is not None else None,
        "indicadores": indicadores,
    }


def processar_quadrimestre(relatorio: Json) -> Json:
    nu = relatorio["_meta"]["nuQuadrimestre"]
    finais = relatorio.get("classificacaoFinalComponente", [])
    qual_final = {linha["sgEquipe"]: linha for linha in finais if linha["tipoOrigem"] == "QUALIDADE"}
    cvat_final = {linha["sgEquipe"]: linha for linha in finais if linha["tipoOrigem"] == "CVAT"}

    por_equipe = defaultdict(list)
    for linha in relatorio.get("conceitoPorIndicadorQualidade", []):
        por_equipe[linha["sgEquipe"]].append(linha)

    componente3 = {
        eq: _equipe_qualidade(eq, por_equipe.get(eq, []), qual_final.get(eq))
        for eq in sorted(set(por_equipe) | set(qual_final))
    }

    dim_por_equipe = defaultdict(list)
    for linha in relatorio.get("classificacaoFinalPorDimensaoCvat", []):
        dim_por_equipe[linha["sgEquipe"]].append(
            {"nome": linha["noDimensao"].replace("CVAT - ", ""), "dist": _dist(linha)}
        )
    componente2 = {
        eq: {
            "equipes": linha["totalEquipesValidasParaComponente"],
            "distFinal": _dist(linha),
            "dimensoes": sorted(dim_por_equipe.get(eq, []), key=lambda d: d["nome"]),
        }
        for eq, linha in sorted(cvat_final.items())
    }
    return {
        "id": nu,
        "rotulo": _rotulo(nu),
        "descricao": relatorio["_meta"]["descricao"],
        "componente2": componente2,
        "componente3": componente3,
    }


def _prioridades(quad: Json, limite: int = 6) -> list[Json]:
    itens = []
    for eq, dados in quad["componente3"].items():
        for i in dados["indicadores"]:
            if i["potencial"]:
                itens.append(
                    {
                        "equipe": eq,
                        **{
                            k: i[k]
                            for k in ("codigo", "curto", "peso", "janela", "dist", "pontuacaoMedia", "potencial")
                        },
                    }
                )
    return sorted(itens, key=lambda x: (-x["potencial"], x["codigo"]))[:limite]


def carregar_brutos() -> list[Json]:
    from_dir = sorted(config.RAW_DIR.glob("*.json"))
    return [json.loads(p.read_text(encoding="utf-8")) for p in from_dir]


def construir_painel(gerado_em: str) -> Json:
    quads = [processar_quadrimestre(r) for r in carregar_brutos()]
    quads.sort(key=lambda q: q["id"])
    for q in quads:
        q["prioridades"] = _prioridades(q)
    return {
        "meta": {
            "municipio": config.MUNICIPIO_NOME.title(),
            "uf": config.UF,
            "ibge": config.MUNICIPIO_IBGE,
            "geradoEm": gerado_em,
            "fonte": config.PORTAL_URL,
            "notaTecnica": "Nota Técnica nº 8/2026-DEAPS/SAPS/MS (Portaria GM/MS nº 3.493/2024)",
            "pontos": config.PONTOS,
            "janelas": config.JANELAS,
        },
        "quadrimestres": quads,
    }
