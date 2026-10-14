import copy
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from siaps_pacuja import config  # noqa: E402


def linha_ind(co=105, eq="eSF", nu="2026Q1", **conc):
    base = {
        "nuQuadrimestre": nu,
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


def relatorio_exemplo(nu="2026Q1"):
    final = {**linha_ind(nu=nu), "tipoOrigem": "QUALIDADE", "totalEquipesValidasParaComponente": 3}
    cvat = {**final, "tipoOrigem": "CVAT"}
    dim = {**linha_ind(101, nu=nu), "noDimensao": "CVAT - Dimensão Cadastro"}
    return {
        "classificacaoFinalComponente": [final, cvat],
        "conceitoPorIndicadorQualidade": [linha_ind(105, nu=nu), linha_ind(104, nu=nu)],
        "classificacaoFinalPorDimensaoCvat": [dim],
    }


@contextmanager
def dados_temporarios() -> Iterator[Path]:
    """Redireciona data/ e dashboard/ para uma pasta temporária."""
    tmp = Path(tempfile.mkdtemp())
    with (
        mock.patch.object(config, "RAW_DIR", tmp / "raw"),
        mock.patch.object(config, "CSV_DIR", tmp / "csv"),
        mock.patch.object(config, "PROCESSED_DIR", tmp / "proc"),
        mock.patch.object(config, "DASHBOARD_DIR", tmp / "dash"),
    ):
        (tmp / "dash").mkdir()
        yield tmp


@contextmanager
def fonte_simulada(relatorios: dict) -> Iterator[mock.MagicMock]:
    """Simula a API do Siaps: lista de quadrimestres e relatórios por id."""
    quads = [{"nuCompetencia": q, "competencia": q, "quadrimestre": True} for q in ("2025Q1", *sorted(relatorios))]
    with (
        mock.patch("siaps_pacuja.client.listar_quadrimestres", return_value=quads),
        mock.patch(
            "siaps_pacuja.client.buscar_quadrimestre", side_effect=lambda nu: copy.deepcopy(relatorios.get(nu, {}))
        ) as buscar,
        mock.patch("time.sleep"),
    ):
        yield buscar
