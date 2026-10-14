"""Servidor local do painel: arquivos estáticos + POST /api/atualizar (botão 'Atualizar dados')."""

import http.server
import json
import logging
import threading
from typing import Any

from . import config, extract, pipeline
from .config import Json

_lock = threading.Lock()

CSP = (
    "default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com; "
    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; "
    "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a: Any, **kw: Any) -> None:
        super().__init__(*a, directory=str(config.DASHBOARD_DIR), **kw)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def _json(self, status: int, obj: Json) -> None:
        corpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_POST(self) -> None:
        # Cabeçalho custom: páginas de outros sites não conseguem enviá-lo sem pré-verificação CORS.
        if self.path != "/api/atualizar" or self.headers.get("X-Requested-With") != "painel":
            return self._json(404, {"ok": False, "erro": "não encontrado"})
        if not _lock.acquire(blocking=False):
            return self._json(409, {"ok": False, "erro": "Atualização já em andamento."})
        try:
            alterados = extract.atualizar()
            pipeline.build()
            self._json(200, {"ok": True, "alterados": alterados})
        except Exception:  # noqa: BLE001 - o detalhe vai só para o log; o painel recebe msg genérica
            logging.exception("falha ao atualizar")
            self._json(
                502,
                {
                    "ok": False,
                    "erro": "Não foi possível atualizar agora (Siaps indisponível "
                    "ou formato dos dados mudou). Veja o log do servidor.",
                },
            )
        finally:
            _lock.release()


def criar_servidor(port: int) -> http.server.ThreadingHTTPServer:
    return http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)  # só localhost


def serve(port: int) -> None:
    with criar_servidor(port) as srv:
        print(f"Painel em http://127.0.0.1:{port}  (Ctrl+C para sair)")
        srv.serve_forever()
