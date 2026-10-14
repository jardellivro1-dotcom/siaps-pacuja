"""CLI:  python -m siaps_pacuja [update | build | serve]"""

import argparse
import logging

from . import extract, pipeline, server


def main() -> None:
    p = argparse.ArgumentParser(prog="siaps_pacuja", description=__doc__)
    p.add_argument("comando", nargs="?", default="update", choices=["update", "build", "serve"])
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.comando == "update":
        alterados = extract.atualizar()
        print("Novos/atualizados:", ", ".join(alterados) or "nenhum")
    if args.comando in ("update", "build"):
        painel = pipeline.build()
        print(f"Painel gerado: {len(painel['quadrimestres'])} quadrimestre(s) -> dashboard/index.html")
    else:
        server.serve(args.port)


if __name__ == "__main__":
    main()
