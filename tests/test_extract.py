import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import config, linha_ind, relatorio_exemplo
from siaps_pacuja import extract


class Esquema(unittest.TestCase):
    def test_valido(self):
        extract.validar_esquema(relatorio_exemplo())

    def test_campo_faltando(self):
        r = relatorio_exemplo()
        del r["conceitoPorIndicadorQualidade"][0]["qtdClassificacaoBom"]
        with self.assertRaisesRegex(ValueError, "Esquema mudou"):
            extract.validar_esquema(r)

    def test_valor_negativo_ou_tipo_errado(self):
        for ruim in (-1, "3", None):
            r = relatorio_exemplo()
            r["conceitoPorIndicadorQualidade"][0]["qtdClassificacaoBom"] = ruim
            with self.assertRaises(ValueError):
                extract.validar_esquema(r)

    def test_recusa_outro_municipio(self):
        r = relatorio_exemplo()
        r["conceitoPorIndicadorQualidade"].append(linha_ind(coMunicipioIbge="230960"))
        with self.assertRaisesRegex(ValueError, "fora de Pacujá"):
            extract._so_pacuja(r)


class Atualizar(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for nome in ("RAW_DIR", "CSV_DIR"):
            p = mock.patch.object(config, nome, self.tmp / nome)
            p.start()
            self.addCleanup(p.stop)
        quads = [{"nuCompetencia": q, "competencia": q, "quadrimestre": True} for q in ("2025Q1", "2025Q2", "2026Q1")]
        self.relatorios = {"2025Q2": relatorio_exemplo(), "2026Q1": {}}  # 2026Q1 sem dados
        for patch in (
            mock.patch("siaps_pacuja.client.listar_quadrimestres", return_value=quads),
            mock.patch("siaps_pacuja.client.buscar_quadrimestre", side_effect=lambda nu: self.relatorios.get(nu, {})),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def test_baixa_so_com_dados_e_acima_do_piso_e_e_idempotente(self):
        self.assertEqual(extract.atualizar(), ["2025Q2"])
        self.assertEqual(sorted(p.name for p in config.RAW_DIR.glob("*.json")), ["2025Q2.json"])
        self.assertEqual(len(list(config.CSV_DIR.glob("*.csv"))), 3)
        self.assertEqual(extract.atualizar(), [])  # segunda rodada: nada mudou

    def test_detecta_dado_atualizado(self):
        extract.atualizar()
        self.relatorios["2025Q2"]["conceitoPorIndicadorQualidade"][0]["qtdClassificacaoOtimo"] = 3
        self.assertEqual(extract.atualizar(), ["2025Q2"])

    def test_csv_utf8_bom_e_ponto_e_virgula(self):
        extract.atualizar()
        conteudo = next(config.CSV_DIR.glob("*classificacao_final.csv")).read_bytes()
        self.assertTrue(conteudo.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b";", conteudo.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
