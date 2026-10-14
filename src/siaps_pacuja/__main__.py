"""CLI:  python -m siaps_pacuja [update | build | serve | status]"""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler

from . import config, extract, pipeline, server


def _configurar_logs() -> None:
    """Console + arquivo rotativo (logs/). Os registros não contêm dados pessoais nem segredos."""
    formato = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(message)s"))
    raiz.addHandler(console)
    pasta = config.ROOT / "logs"
    pasta.mkdir(exist_ok=True)
    arquivo = RotatingFileHandler(pasta / "siaps.log", maxBytes=500_000, backupCount=3, encoding="utf-8")
    arquivo.setFormatter(formato)
    raiz.addHandler(arquivo)


def status() -> int:
    """Resumo da última coleta. Código de saída 1 se nunca houve coleta, se falhou ou se os dados estão velhos."""
    coleta = extract.carregar_manifesto()["coleta"]
    dias = extract.dias_desde_ultima_coleta()
    print(f"Versão do app: {config.VERSAO_APP} | metodologia: {config.METODOLOGIA['id']}")
    print(f"Última coleta bem-sucedida: {coleta.get('ultimaBemSucedida') or 'nunca'}")
    print(f"Última tentativa: {coleta.get('ultimaTentativa') or 'nunca'}")
    if coleta.get("ultimoErro"):
        print(f"Último erro: {coleta['ultimoErro']}")
    obsoleto = dias is None or dias > config.DADOS_OBSOLETOS_APOS_DIAS
    if obsoleto:
        print(f"ALERTA: dados desatualizados (limite: {config.DADOS_OBSOLETOS_APOS_DIAS} dias).")
    return 1 if obsoleto or coleta.get("ultimoErro") else 0


def main() -> None:
    p = argparse.ArgumentParser(prog="siaps_pacuja", description=__doc__)
    p.add_argument("comando", nargs="?", default="update", choices=["update", "build", "serve", "status"])
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--somente-leitura", action="store_true", help="serve: desliga o botão/endpoint de atualização")
    args = p.parse_args()
    _configurar_logs()
    if args.comando == "status":
        sys.exit(status())
    if args.comando == "update":
        alterados = extract.atualizar()
        print("Novos/atualizados:", ", ".join(alterados) or "nenhum")
    if args.comando in ("update", "build"):
        painel = pipeline.build()
        print(f"Painel gerado: {len(painel['quadrimestres'])} quadrimestre(s) -> dashboard/index.html")
    else:
        server.serve(args.port, args.somente_leitura)


if __name__ == "__main__":
    main()
