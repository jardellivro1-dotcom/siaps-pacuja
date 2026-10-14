"""Cliente HTTP para a API pública do Siaps (mesma fonte usada pelo portal /publico)."""

import json
import time
import urllib.error
import urllib.request
from typing import Any

from . import config
from .config import Json

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "siaps-pacuja/1.0 (monitoramento APS; dados publicos)",
}


def _request(url: str, body: Json | None = None, retries: int = 3, timeout: int = 60) -> Any:
    if not url.startswith("https://"):  # nunca file:/ftp: etc.
        raise ValueError(f"URL não permitida: {url}")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(  # noqa: S310 - esquema https validado acima
        url, data=data, headers=HEADERS, method="POST" if body is not None else "GET"
    )
    for tentativa in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            if tentativa == retries:
                raise RuntimeError(f"Falha ao acessar {url}: {exc}") from exc
            time.sleep(2 * tentativa)


def listar_quadrimestres() -> list[Json]:
    """Quadrimestres publicados pelo portal (ex.: 2026Q1), do mais antigo ao mais novo."""
    competencias = _request(f"{config.API_BASE}/filtros/competencias")
    quads = [c for c in competencias if c.get("quadrimestre")]
    return sorted(quads, key=lambda c: c["nuCompetencia"])


def buscar_quadrimestre(nu_quadrimestre: str) -> Json:
    """Relatório do quadrimestre para Pacujá/CE (mesma chamada do botão 'Gerar e baixar')."""
    resultado: Json = _request(
        f"{config.API_BASE}/componente/indicador-quadrimestre/filtro",
        {
            "uf": [config.UF],
            "coMunicipioIbge": [config.MUNICIPIO_IBGE],
            "nuQuadrimestre": [nu_quadrimestre],
        },
    )
    return resultado
