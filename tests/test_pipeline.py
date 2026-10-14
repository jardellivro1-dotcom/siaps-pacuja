import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import config, relatorio_exemplo
from siaps_pacuja import metrics, pipeline


def com_meta(nu="2026Q1"):
    return {**relatorio_exemplo(), "_meta": {"nuQuadrimestre": nu, "descricao": "1º Quadrimestre/2026"}}


class Processamento(unittest.TestCase):
    def test_quadrimestre(self):
        q = metrics.processar_quadrimestre(com_meta())
        esf = q["componente3"]["eSF"]
        # C4 e C5 (peso 1): 1 Ótimo + 2 Bom => pontuação média 0,8333 cada => nota parcial 1,67
        self.assertEqual([i["codigo"] for i in esf["indicadores"]], ["C4", "C5"])
        self.assertEqual(esf["notaMedia"], 1.67)
        self.assertEqual(esf["classificacaoNotaMedia"], "Regular")
        self.assertEqual(q["rotulo"], "1º quad/2026")
        self.assertEqual(q["componente2"]["eSF"]["dimensoes"][0]["nome"], "Dimensão Cadastro")

    def test_prioridades_ordenadas_por_ganho(self):
        q = metrics.processar_quadrimestre(com_meta())
        ganhos = [p["potencial"] for p in metrics._prioridades(q)]
        self.assertEqual(ganhos, sorted(ganhos, reverse=True))
        self.assertTrue(all(g > 0 for g in ganhos))

    def test_indicador_sem_equipes_nao_gera_nota(self):
        r = com_meta()
        for linha in r["conceitoPorIndicadorQualidade"]:
            for campo in config.CAMPOS_CONCEITO.values():
                linha[campo] = 0
        esf = metrics.processar_quadrimestre(r)["componente3"]["eSF"]
        self.assertIsNone(esf["notaMedia"])

    def test_indicador_desconhecido_e_ignorado(self):
        r = com_meta()
        r["conceitoPorIndicadorQualidade"][0]["coTipoIndicador"] = 999
        esf = metrics.processar_quadrimestre(r)["componente3"]["eSF"]
        self.assertEqual(len(esf["indicadores"]), 1)


class Build(unittest.TestCase):
    def test_gera_painel_e_dados_embutidos(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "raw").mkdir()
        (tmp / "csv").mkdir()
        (tmp / "dash").mkdir()
        (tmp / "raw" / "2026Q1.json").write_text(json.dumps(com_meta()), encoding="utf-8")
        (tmp / "csv" / "pacuja_2026Q1_x.csv").write_text("a;b\n", encoding="utf-8")
        with (
            mock.patch.object(config, "RAW_DIR", tmp / "raw"),
            mock.patch.object(config, "CSV_DIR", tmp / "csv"),
            mock.patch.object(config, "PROCESSED_DIR", tmp / "proc"),
            mock.patch.object(config, "DASHBOARD_DIR", tmp / "dash"),
        ):
            painel = pipeline.build()
        self.assertEqual(painel["meta"]["ibge"], "230990")
        self.assertEqual(painel["csv"], ["pacuja_2026Q1_x.csv"])
        data_js = (tmp / "dash" / "data.js").read_text(encoding="utf-8")
        self.assertTrue(data_js.startswith("window.PAINEL = "))
        self.assertTrue((tmp / "proc" / "painel.json").exists())


if __name__ == "__main__":
    unittest.main()
