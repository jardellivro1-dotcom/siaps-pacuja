"""Teste de carga local do servidor em modo somente leitura (não use contra servidores de terceiros).

Uso:  PYTHONPATH=src python tools/teste_carga.py [requisicoes] [concorrencia]
Meta (docs/REQUISITOS.md §3): 0 erros e p95 < 250 ms com 25 acessos simultâneos.
"""

import http.client
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from siaps_pacuja import server

CAMINHOS = ["/", "/data.js", "/app.js", "/style.css", "/vendor/chart.umd.min.js", "/api/estado"]


def main(total: int = 600, concorrencia: int = 25) -> int:
    srv = server.criar_servidor(0, somente_leitura=True)
    porta = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def uma(i: int) -> tuple[bool, float]:
        inicio = time.perf_counter()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", porta, timeout=10)
            conn.request("GET", CAMINHOS[i % len(CAMINHOS)])
            ok = conn.getresponse().status == 200
            conn.close()
        except OSError:
            ok = False
        return ok, (time.perf_counter() - inicio) * 1000

    inicio = time.perf_counter()
    with ThreadPoolExecutor(concorrencia) as pool:
        resultados = list(pool.map(uma, range(total)))
    duracao = time.perf_counter() - inicio
    srv.shutdown()
    srv.server_close()

    tempos = sorted(t for _, t in resultados)
    erros = sum(1 for ok, _ in resultados if not ok)
    p95 = tempos[int(len(tempos) * 0.95) - 1]
    print(f"{total} requisições, {concorrencia} simultâneas, {duracao:.1f}s ({total / duracao:.0f} req/s)")
    print(f"erros={erros}  mediana={statistics.median(tempos):.1f}ms  p95={p95:.1f}ms  máx={tempos[-1]:.1f}ms")
    return 0 if erros == 0 and p95 < 250 else 1


if __name__ == "__main__":
    sys.exit(main(*(int(a) for a in sys.argv[1:3])))
