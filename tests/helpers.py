import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from siaps_pacuja import config  # noqa: E402


def linha_ind(co=105, eq="eSF", **conc):
    base = {
        "nuQuadrimestre": "2026Q1",
        "sgUf": config.UF,
        "coMunicipioIbge": config.MUNICIPIO_IBGE,
        "noMunicipioAcentuado": "PACUJÁ",
        "sgEquipe": eq,
        "coTipoIndicador": co,
        "noIndicador": "x",
        "qtdClassificacaoOtimo": 1,
        "qtdClassificacaoBom": 2,
        "qtdClassificacaoSuficiente": 0,
        "qtdClassificacaoRegular": 0,
    }
    return {**base, **conc}


def relatorio_exemplo():
    final = {**linha_ind(), "tipoOrigem": "QUALIDADE", "totalEquipesValidasParaComponente": 3}
    cvat = {**final, "tipoOrigem": "CVAT"}
    dim = {**linha_ind(101), "noDimensao": "CVAT - Dimensão Cadastro"}
    return {
        "classificacaoFinalComponente": [final, cvat],
        "conceitoPorIndicadorQualidade": [linha_ind(105), linha_ind(104)],
        "classificacaoFinalPorDimensaoCvat": [dim],
    }
