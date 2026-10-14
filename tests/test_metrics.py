"""Valida a implementação contra os exemplos numéricos da NT 8/2026 (Quadros 2, 3 e 4)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from siaps_pacuja import config, metrics  # noqa: E402


def linha(co, conceito):
    campos = dict.fromkeys(config.CAMPOS_CONCEITO.values(), 0)
    campos[config.CAMPOS_CONCEITO[conceito]] = 1  # uma equipe naquele conceito
    return {"coTipoIndicador": co, "noIndicador": str(co), **campos}


def nota(equipe, conceitos):
    cos = list(config.INDICADORES[equipe])
    linhas = [linha(co, c) for co, c in zip(cos, conceitos, strict=True)]
    return metrics._equipe_qualidade(equipe, linhas, None)["notaMedia"]


class NotaTecnica(unittest.TestCase):
    def test_quadro2_esf(self):  # C1..C7 do exemplo (ordem das chaves: 110,108,107,105,104,106,109)
        self.assertEqual(nota("eSF", ["Bom", "Ótimo", "Ótimo", "Suficiente", "Regular", "Ótimo", "Ótimo"]), 8.5)

    def test_quadro3_esb(self):
        self.assertEqual(nota("eSB", ["Bom", "Ótimo", "Ótimo", "Suficiente", "Regular", "Ótimo"]), 7.5)

    def test_quadro4_emulti(self):
        self.assertEqual(nota("eMulti", ["Ótimo", "Bom"]), 9.0)

    def test_pesos_somam_10(self):
        for eq, inds in config.INDICADORES.items():
            self.assertEqual(sum(p for _, p, _ in inds.values()), 10, eq)

    def test_faixas_componente_iii(self):
        casos = {7.51: "Ótimo", 7.5: "Bom", 5: "Bom", 4.99: "Suficiente", 2.51: "Suficiente", 2.5: "Regular"}
        for n, esperado in casos.items():
            self.assertEqual(config.classificar_componente_iii(n), esperado, n)

    def test_media_das_equipes_e_linear(self):
        d = {
            "qtdClassificacaoOtimo": 1,
            "qtdClassificacaoBom": 2,
            "qtdClassificacaoSuficiente": 0,
            "qtdClassificacaoRegular": 0,
        }
        self.assertAlmostEqual(metrics._pontuacao_media(metrics._dist(d)), (1 + 2 * 0.75) / 3)


if __name__ == "__main__":
    unittest.main()
