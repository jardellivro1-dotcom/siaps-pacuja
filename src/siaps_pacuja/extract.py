"""Extração: descobre quadrimestres publicados, valida e publica os dados de Pacujá.

Garantias:
- tudo é coletado e validado em memória antes de gravar qualquer arquivo; se algo falhar, a última
  revisão válida em disco permanece intacta;
- a resposta original é preservada (data/raw) e, se o dado oficial mudar, a versão anterior vai para
  data/raw/revisoes/ (resultados históricos nunca são sobrescritos sem cópia);
- data/manifest.json registra fonte, filtros, horário, revisão e assinatura (SHA-256) de cada arquivo;
- uma trava impede coletas simultâneas (botão, linha de comando e agendador).
"""

import csv
import hashlib
import io
import json
import logging
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import client, config
from .client import ColetaErro
from .config import Json

log = logging.getLogger("siaps")

SECOES = {
    "classificacao_final": "classificacaoFinalComponente",
    "indicadores_qualidade": "conceitoPorIndicadorQualidade",
    "dimensoes_cvat": "classificacaoFinalPorDimensaoCvat",
}

_BASE = {"nuQuadrimestre", "sgUf", "coMunicipioIbge", "sgEquipe", *config.CAMPOS_CONCEITO.values()}
# Campos mínimos que o restante do pipeline usa; se a API mudar, falhamos alto em vez de gerar painel errado.
CAMPOS_OBRIGATORIOS = {
    "classificacaoFinalComponente": {*_BASE, "tipoOrigem", "totalEquipesValidasParaComponente"},
    "conceitoPorIndicadorQualidade": {*_BASE, "coTipoIndicador", "noIndicador"},
    "classificacaoFinalPorDimensaoCvat": {*_BASE, "coTipoIndicador", "noDimensao"},
}


class ColetaEmAndamento(ColetaErro):
    """Já existe uma coleta em execução."""


# ---------------------------------------------------------------- validação


def validar_esquema(relatorio: Json) -> Json:
    """Detecta mudança de formato da API e valida tipos básicos das contagens."""
    for secao, campos in CAMPOS_OBRIGATORIOS.items():
        linhas = relatorio.get(secao, [])
        if not isinstance(linhas, list):
            raise ValueError(f"Esquema inesperado: '{secao}' deveria ser lista")
        for linha in linhas:
            if not isinstance(linha, dict):
                raise ValueError(f"Esquema inesperado em '{secao}': linha não é objeto")
            faltando = campos - set(linha)
            if faltando:
                raise ValueError(f"Esquema mudou em '{secao}': faltam {sorted(faltando)}")
            for campo in config.CAMPOS_CONCEITO.values():
                valor = linha[campo]
                if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
                    raise ValueError(f"Valor inválido em '{secao}.{campo}': {valor!r}")
    return relatorio


def _so_pacuja(relatorio: Json) -> Json:
    """Garante que nada além de Pacujá/CE entre no projeto."""
    for secao in SECOES.values():
        for linha in relatorio.get(secao, []):
            if linha.get("coMunicipioIbge") != config.MUNICIPIO_IBGE or linha.get("sgUf") != config.UF:
                raise ValueError(f"Linha fora de Pacujá/{config.UF} em '{secao}': {linha}")
    return relatorio


def _soma(linha: Json) -> int:
    return int(sum(linha[c] for c in config.CAMPOS_CONCEITO.values()))


def validar_integridade(relatorio: Json, nu: str) -> Json:
    """Confere período, duplicidades e totais (contagens por conceito x total de equipes)."""
    chaves = {
        "classificacaoFinalComponente": ("sgEquipe", "tipoOrigem"),
        "conceitoPorIndicadorQualidade": ("sgEquipe", "coTipoIndicador"),
        "classificacaoFinalPorDimensaoCvat": ("sgEquipe", "coTipoIndicador"),
    }
    for secao, campos in chaves.items():
        vistas = set()
        for linha in relatorio.get(secao, []):
            if linha["nuQuadrimestre"] != nu:
                raise ValueError(f"Período divergente em '{secao}': {linha['nuQuadrimestre']} != {nu}")
            chave = tuple(linha[c] for c in campos)
            if chave in vistas:
                raise ValueError(f"Linha duplicada em '{secao}': {chave}")
            vistas.add(chave)

    totais = {}
    for linha in relatorio.get("classificacaoFinalComponente", []):
        if _soma(linha) != linha["totalEquipesValidasParaComponente"]:
            raise ValueError(f"Total de equipes não bate com as contagens: {linha['sgEquipe']}/{linha['tipoOrigem']}")
        totais[(linha["sgEquipe"], linha["tipoOrigem"])] = linha["totalEquipesValidasParaComponente"]

    for secao, origem in (
        ("conceitoPorIndicadorQualidade", "QUALIDADE"),
        ("classificacaoFinalPorDimensaoCvat", "CVAT"),
    ):
        for linha in relatorio.get(secao, []):
            total = totais.get((linha["sgEquipe"], origem))
            if total is None or _soma(linha) > total:
                raise ValueError(f"Contagem inconsistente em '{secao}': {linha['sgEquipe']}/{linha['coTipoIndicador']}")
    return relatorio


def _tem_dados(relatorio: Json) -> bool:
    return any(relatorio.get(s) for s in SECOES.values())


# ---------------------------------------------------------------- arquivos


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def hash_relatorio(relatorio: Json) -> str:
    """Assinatura da resposta original da API (sem os metadados que adicionamos)."""
    limpo = {k: v for k, v in relatorio.items() if k != "_meta"}
    return _sha(json.dumps(limpo, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _gravar_atomico(destino: Path, dados: bytes) -> str:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    tmp.write_bytes(dados)
    os.replace(tmp, destino)  # troca atômica: nunca deixa arquivo pela metade
    return _sha(dados)


def celula_segura(valor: object) -> object:
    """Neutraliza fórmulas (=, +, -, @) em células de texto abertas no Excel/Planilhas (CSV injection)."""
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + valor
    return valor


def _gravar_csv(nu: str, relatorio: Json) -> dict[str, str]:
    assinaturas = {}
    for nome, secao in SECOES.items():
        linhas = relatorio.get(secao, [])
        if not linhas:
            continue
        caminho = config.CSV_DIR / f"pacuja_{nu}_{nome}.csv"
        # utf-8-sig + ';' => abre corretamente no Excel em português
        buf = io.StringIO(newline="")
        w = csv.DictWriter(buf, fieldnames=list(linhas[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows({k: celula_segura(v) for k, v in linha.items()} for linha in linhas)
        assinaturas[f"csv/{caminho.name}"] = _gravar_atomico(caminho, b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8"))
    return assinaturas


def carregar_manifesto() -> Json:
    caminho = config.manifesto_path()
    if caminho.exists():
        manifesto: Json = json.loads(caminho.read_text(encoding="utf-8"))
        return manifesto
    return {
        "schemaVersao": config.SCHEMA_VERSAO,
        "metodologia": config.METODOLOGIA["id"],
        "municipio": {"nome": config.MUNICIPIO_NOME, "uf": config.UF, "ibge": config.MUNICIPIO_IBGE},
        "coleta": {"ultimaTentativa": None, "ultimaBemSucedida": None, "ultimoErro": None},
        "quadrimestres": {},
    }


def _salvar_manifesto(manifesto: Json) -> None:
    texto = json.dumps(manifesto, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _gravar_atomico(config.manifesto_path(), texto.encode("utf-8"))


@contextmanager
def _trava() -> Iterator[None]:
    caminho = config.lock_path()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    for _ in range(2):
        try:
            fd = os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                velha = time.time() - caminho.stat().st_mtime > config.LOCK_EXPIRA_S
            except FileNotFoundError:
                continue
            if not velha:
                raise ColetaEmAndamento("Já existe uma coleta em andamento.") from None
            caminho.unlink(missing_ok=True)  # trava abandonada por um processo que morreu
    if fd is None:
        raise ColetaEmAndamento("Já existe uma coleta em andamento.")
    try:
        os.write(fd, str(os.getpid()).encode())
        yield
    finally:
        os.close(fd)
        caminho.unlink(missing_ok=True)


# ---------------------------------------------------------------- coleta


def _coletar() -> dict[str, tuple[str, Json]]:
    """Baixa e valida tudo em memória. Qualquer erro aborta sem tocar nos arquivos."""
    candidatos: dict[str, tuple[str, Json]] = {}
    primeira = True
    for quad in client.listar_quadrimestres():
        nu = quad["nuCompetencia"]
        if nu < config.PRIMEIRO_QUADRIMESTRE:
            continue
        if not primeira:
            time.sleep(config.INTERVALO_ENTRE_CONSULTAS_S)  # respeito à fonte
        primeira = False
        relatorio = client.buscar_quadrimestre(nu)
        if not _tem_dados(relatorio):
            log.info("%s (%s): sem dados publicados para Pacujá — ignorado", nu, quad["competencia"])
            continue
        validar_integridade(validar_esquema(_so_pacuja(relatorio)), nu)
        candidatos[nu] = (str(quad["competencia"]), relatorio)
    if not candidatos:
        raise ColetaErro("A fonte não devolveu nenhum quadrimestre com dados; nada foi alterado.")
    return candidatos


def _publicar(candidatos: dict[str, tuple[str, Json]], manifesto: Json, agora: str) -> list[str]:
    alterados = []
    for nu, (descricao, relatorio) in sorted(candidatos.items()):
        sha = hash_relatorio(relatorio)
        destino = config.RAW_DIR / f"{nu}.json"
        entrada = manifesto["quadrimestres"].get(nu)
        if entrada:
            sha_atual, revisao = entrada["sha256"], entrada["revisao"]
        elif destino.exists():  # arquivo anterior à existência do manifesto
            sha_atual, revisao = hash_relatorio(json.loads(destino.read_text(encoding="utf-8"))), 1
        else:
            sha_atual, revisao = None, 0

        if sha_atual != sha:
            if sha_atual is not None and destino.exists():  # dado oficial mudou: guarda a revisão anterior
                antigo = config.revisoes_dir() / nu / f"rev{revisao:03d}_{sha_atual[:8]}.json"
                _gravar_atomico(antigo, destino.read_bytes())
                log.info("%s: dado oficial alterado — revisão %d arquivada", nu, revisao)
            revisao += 1
            alterados.append(nu)
            log.info("%s: %s (revisão %d)", nu, "novo" if sha_atual is None else "atualizado", revisao)
        else:
            log.info("%s: sem alterações (revisão %d)", nu, revisao)

        relatorio["_meta"] = {
            "nuQuadrimestre": nu,
            "descricao": descricao,
            "schemaVersao": config.SCHEMA_VERSAO,
        }
        texto = json.dumps(relatorio, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        arquivos = {f"raw/{destino.name}": _gravar_atomico(destino, texto)}
        arquivos.update(_gravar_csv(nu, relatorio))
        manifesto["quadrimestres"][nu] = {
            "descricao": descricao,
            "revisao": revisao,
            "sha256": sha,
            "coletadoEm": agora,
            "alteradoEm": agora if sha_atual != sha else (entrada or {}).get("alteradoEm", agora),
            "fonte": f"{config.API_BASE}/componente/indicador-quadrimestre/filtro",
            "filtros": {"uf": [config.UF], "coMunicipioIbge": [config.MUNICIPIO_IBGE], "nuQuadrimestre": [nu]},
            "metodologia": config.METODOLOGIA["id"],
            "linhas": {n: len(relatorio.get(s, [])) for n, s in SECOES.items()},
            "arquivos": arquivos,
        }
    return alterados


def atualizar() -> list[str]:
    """Coleta, valida e publica. Devolve os quadrimestres novos ou com dado oficial alterado."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    agora = _agora()
    with _trava():
        manifesto = carregar_manifesto()
        try:
            candidatos = _coletar()
        except Exception as exc:
            manifesto["coleta"].update(ultimaTentativa=agora, ultimoErro=f"{type(exc).__name__}: {str(exc)[:300]}")
            _salvar_manifesto(manifesto)
            raise  # a última revisão válida continua em disco
        alterados = _publicar(candidatos, manifesto, agora)
        manifesto["coleta"].update(ultimaTentativa=agora, ultimaBemSucedida=agora, ultimoErro=None)
        _salvar_manifesto(manifesto)
    return alterados


def dias_desde_ultima_coleta(manifesto: Json | None = None) -> float | None:
    manifesto = manifesto or carregar_manifesto()
    ultima = manifesto["coleta"].get("ultimaBemSucedida")
    if not ultima:
        return None
    delta = datetime.now(timezone.utc) - datetime.strptime(ultima, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return delta.total_seconds() / 86400
