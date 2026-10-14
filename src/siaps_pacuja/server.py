"""Servidor local do painel: arquivos estáticos + API mínima.

  GET  /api/estado      -> versão, se a atualização está habilitada e dados da última coleta
  POST /api/atualizar   -> dispara uma coleta (botão "Atualizar dados")

Controles: escuta só em 127.0.0.1; valida o cabeçalho Host (contra DNS rebinding) e a Origin;
exige cabeçalho personalizado nas alterações (CSRF); 1 coleta por vez e no máximo 1 por minuto;
modo somente leitura que desliga a escrita; respostas de erro sem detalhes internos.
"""

import http.server
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, cast

from . import config, extract, pipeline
from .config import Json

log = logging.getLogger("siaps")

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
)


class Handler(http.server.SimpleHTTPRequestHandler):
    server_version = "PainelAPS"
    sys_version = ""
    timeout = 30  # conexões lentas/ociosas são encerradas
    somente_leitura = False
    _lock = threading.Lock()
    _ultima_coleta = -1e9

    def __init__(self, *a: Any, **kw: Any) -> None:
        super().__init__(*a, directory=str(config.DASHBOARD_DIR), **kw)

    # ------------------------------------------------------------ acesso a arquivos
    def translate_path(self, path: str) -> str:
        """Só serve arquivos dentro de dashboard/ (inclusive contra '\' e '..' no Windows)."""
        raiz = config.DASHBOARD_DIR.resolve()
        caminho = super().translate_path(path)
        if chr(0) in caminho:  # byte nulo: nunca é um nome de arquivo válido
            return str(raiz / "__fora_do_dashboard__")
        try:
            Path(caminho).resolve().relative_to(raiz)
        except ValueError:
            return str(raiz / "__fora_do_dashboard__")  # inexistente => 404
        return caminho

    def list_directory(self, path: Any) -> None:
        self.send_error(404, "Not Found")  # sem listagem de diretórios
        return None

    # ------------------------------------------------------------ cabeçalhos / validações
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        super().end_headers()

    def _json(self, status: int, obj: Json, extra: dict[str, str] | None = None) -> None:
        corpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(corpo)

    def _hosts_validos(self, prefixo: str = "") -> set[str]:
        porta = cast(tuple[str, int], self.server.server_address)[1]
        return {f"{prefixo}127.0.0.1:{porta}", f"{prefixo}localhost:{porta}"}

    def _barrar_host(self) -> bool:
        if self.headers.get("Host") in self._hosts_validos():
            return False
        self._json(421, {"ok": False, "erro": "Host não permitido."})
        return True

    def _origem_valida(self) -> bool:
        origem = self.headers.get("Origin")
        return origem is None or origem in self._hosts_validos("http://")

    # ------------------------------------------------------------ rotas
    def do_GET(self) -> None:
        if self._barrar_host():
            return
        if self.path == "/api/estado":
            manifesto = extract.carregar_manifesto()
            return self._json(
                200,
                {
                    "versao": config.VERSAO_APP,
                    "atualizacaoHabilitada": not self.somente_leitura,
                    "coleta": manifesto["coleta"],
                    "diasDesdeUltimaColeta": extract.dias_desde_ultima_coleta(manifesto),
                },
            )
        super().do_GET()

    def do_HEAD(self) -> None:
        if not self._barrar_host():
            super().do_HEAD()

    def do_POST(self) -> None:
        if self._barrar_host():
            return
        # Cabeçalho custom: páginas de outros sites não conseguem enviá-lo sem pré-verificação CORS.
        if self.path != "/api/atualizar" or self.headers.get("X-Requested-With") != "painel":
            return self._json(404, {"ok": False, "erro": "não encontrado"})
        if not self._origem_valida():
            return self._json(403, {"ok": False, "erro": "Origem não permitida."})
        if self.somente_leitura:
            return self._json(403, {"ok": False, "erro": "Servidor em modo somente leitura."})
        if not Handler._lock.acquire(blocking=False):
            return self._json(409, {"ok": False, "erro": "Atualização já em andamento."})
        try:
            espera = config.INTERVALO_MIN_ATUALIZACAO_S - (time.monotonic() - Handler._ultima_coleta)
            if espera > 0:
                segundos = int(espera) + 1
                return self._json(
                    429,
                    {"ok": False, "erro": f"Aguarde {segundos}s para atualizar de novo."},
                    {"Retry-After": str(segundos)},
                )
            Handler._ultima_coleta = time.monotonic()
            alterados = extract.atualizar()
            pipeline.build()
            self._json(200, {"ok": True, "alterados": alterados})
        except extract.ColetaEmAndamento:
            self._json(409, {"ok": False, "erro": "Já existe uma coleta em andamento."})
        except Exception:  # noqa: BLE001 - o detalhe vai só para o log; o painel recebe msg genérica
            log.exception("falha ao atualizar")
            self._json(
                502,
                {
                    "ok": False,
                    "erro": "Não foi possível atualizar agora (Siaps indisponível ou formato dos dados "
                    "mudou). Os dados anteriores foram mantidos. Veja o log do servidor.",
                },
            )
        finally:
            Handler._lock.release()


class _Servidor(http.server.ThreadingHTTPServer):
    request_queue_size = 128  # o padrão (5) derruba/atrasa conexões simultâneas (medido em tools/teste_carga.py)
    daemon_threads = True


def criar_servidor(port: int, somente_leitura: bool = False) -> http.server.ThreadingHTTPServer:
    Handler._ultima_coleta = -1e9
    handler = type("HandlerConfigurado", (Handler,), {"somente_leitura": somente_leitura})
    return _Servidor(("127.0.0.1", port), handler)  # só localhost


def serve(port: int, somente_leitura: bool = False) -> None:
    with criar_servidor(port, somente_leitura) as srv:
        modo = " [somente leitura]" if somente_leitura else ""
        print(f"Painel em http://127.0.0.1:{port}{modo}  (Ctrl+C para sair)")
        srv.serve_forever()
