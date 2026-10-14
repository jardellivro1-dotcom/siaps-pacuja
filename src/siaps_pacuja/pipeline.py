"""Orquestração: gera o painel (JSON + data.js + CSV) a partir dos dados brutos já baixados."""

import json
import shutil
from datetime import datetime, timezone

from . import config, metrics
from .config import Json


def build() -> Json:
    painel = metrics.construir_painel(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    (config.PROCESSED_DIR / "painel.json").write_text(
        json.dumps(painel, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # dashboard autocontido: dados embutidos (abre até por file://) + cópia dos CSV para download
    destino_csv = config.DASHBOARD_DIR / "csv"
    shutil.rmtree(destino_csv, ignore_errors=True)
    shutil.copytree(config.CSV_DIR, destino_csv)
    painel["csv"] = sorted(p.name for p in destino_csv.glob("*.csv"))
    (config.DASHBOARD_DIR / "data.js").write_text(
        "window.PAINEL = " + json.dumps(painel, ensure_ascii=False) + ";\n", encoding="utf-8"
    )
    return painel
