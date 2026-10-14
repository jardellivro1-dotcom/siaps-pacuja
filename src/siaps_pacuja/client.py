"""Cliente HTTP para a API pública do Siaps (mesma fonte usada pelo portal /publico).

Controles: só https para o host oficial, certificado verificado, sem seguir redirecionamentos,
tempo limite, tentativas limitadas, tamanho máximo de resposta e parada imediata se a fonte
exigir autenticação (este projeto usa exclusivamente o acesso público).
"""

import json
import logging
import re
import ssl
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from . import config
from .config import Json

log = logging.getLogger("siaps")

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": f"siaps-pacuja/{config.VERSAO_APP} (monitoramento APS; dados publicos)",
}


class ColetaErro(RuntimeError):
    """Falha ao consultar a fonte."""


class AutenticacaoExigida(ColetaErro):
    """A fonte pediu autenticação (401/403). Nunca tentamos contornar: a coleta é interrompida."""


class _SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None  # 3xx vira HTTPError: não seguimos para destinos não autorizados


# Contexto padrão do Python: verifica certificado e nome do host.
_OPENER = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=ssl.create_default_context()), _SemRedirecionamento()
)


def _validar_destino(url: str) -> None:
    partes = urlparse(url)
    if partes.scheme != "https" or partes.hostname != config.HOST_PERMITIDO or partes.username or partes.password:
        raise ValueError(f"Destino não autorizado: {url}")


def _request(url: str, body: Json | None = None, retries: int | None = None, timeout: int | None = None) -> Any:
    _validar_destino(url)
    retries = retries or config.TENTATIVAS
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(  # noqa: S310 - destino validado acima (https + host oficial)
        url, data=data, headers=HEADERS, method="POST" if body is not None else "GET"
    )
    for tentativa in range(1, retries + 1):
        try:
            with _OPENER.open(req, timeout=timeout or config.TIMEOUT_S) as resp:
                bruto = resp.read(config.MAX_RESPOSTA_BYTES + 1)
            if len(bruto) > config.MAX_RESPOSTA_BYTES:
                raise ColetaErro(f"Resposta maior que o limite de {config.MAX_RESPOSTA_BYTES} bytes")
            return json.loads(bruto.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise AutenticacaoExigida(
                    f"A fonte exigiu autenticação (HTTP {exc.code}); coleta interrompida."
                ) from exc
            if exc.code < 500:  # erro da requisição: repetir não adianta
                raise ColetaErro(f"HTTP {exc.code} em {url}") from exc
            erro: Exception = exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            erro = exc
        if tentativa == retries:
            raise ColetaErro(f"Falha ao acessar {url}: {erro}") from erro
        time.sleep(2 * tentativa)
    raise AssertionError("inalcançável")  # pragma: no cover


def listar_quadrimestres() -> list[Json]:
    """Quadrimestres publicados pelo portal (ex.: 2026Q1), do mais antigo ao mais novo."""
    competencias = _request(f"{config.API_BASE}/filtros/competencias")
    if not isinstance(competencias, list):
        raise ColetaErro("Lista de competências em formato inesperado")
    quads = []
    for c in competencias:
        if not isinstance(c, dict) or not c.get("quadrimestre"):
            continue
        if not re.fullmatch(config.QUADRIMESTRE_REGEX, str(c.get("nuCompetencia", ""))):
            log.warning("Competência ignorada (identificador fora do padrão): %r", c.get("nuCompetencia"))
            continue
        quads.append(c)
    return sorted(quads, key=lambda c: c["nuCompetencia"])


def buscar_quadrimestre(nu_quadrimestre: str) -> Json:
    """Relatório do quadrimestre para Pacujá/CE (mesma chamada do botão 'Gerar e baixar')."""
    if not re.fullmatch(config.QUADRIMESTRE_REGEX, nu_quadrimestre):
        raise ValueError(f"Quadrimestre inválido: {nu_quadrimestre!r}")
    resultado = _request(
        f"{config.API_BASE}/componente/indicador-quadrimestre/filtro",
        {
            "uf": [config.UF],
            "coMunicipioIbge": [config.MUNICIPIO_IBGE],
            "nuQuadrimestre": [nu_quadrimestre],
        },
    )
    if not isinstance(resultado, dict):
        raise ColetaErro("Relatório em formato inesperado")
    return resultado
