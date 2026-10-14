"""Correção da metodologia (NT 8/2026): fronteiras, ausência de dado, linearidade e desempenho."""

import itertools
import time
import unittest

from helpers import config, linha_ind
from siaps_pacuja import metrics

CONC = ["Ótimo", "Bom", "Suficiente", "Regular"]


def dist_de(conceitos):
    d = dict.fromkeys(config.CAMPOS_CONCEITO.values(), 0)
    for c in conceitos:
        d[config.CAMPOS_CONCEITO[c]] += 1
    return d


class Fronteiras(unittest.TestCase):
    def test_faixas_do_componente_iii_nos_limites_exatos(self):
        # Quadro 6: > 7,5 Ótimo | >= 5 e <= 7,5 Bom | > 2,5 e < 5 Suficiente | <= 2,5 Regular
        casos = [(10, "Ótimo"), (7.51, "Ótimo"), (7.5, "Bom"), (5.0, "Bom"), (4.99, "Suficiente"),
                 (2.51, "Suficiente"), (2.5, "Regular"), (0, "Regular")]  # fmt: skip
        for nota, esperado in casos:
            self.assertEqual(config.classificar_componente_iii(nota), esperado, nota)

    def test_faixa_visual_da_pontuacao_media(self):
        casos = [(1.0, "Ótimo"), (0.99, "Bom"), (0.75, "Bom"), (0.74, "Suficiente"), (0.5, "Suficiente"),
                 (0.49, "Regular"), (0.25, "Regular"), (None, None)]  # fmt: skip
        for pm, esperado in casos:
            self.assertEqual(metrics.faixa_pontuacao(pm), esperado, pm)

    def test_conceito_predominante_e_empate_conservador(self):
        self.assertEqual(metrics.conceito_predominante({"Ótimo": 3, "Bom": 0, "Suficiente": 0, "Regular": 0}), "Ótimo")
        self.assertEqual(metrics.conceito_predominante({"Ótimo": 1, "Bom": 1, "Suficiente": 0, "Regular": 0}), "Bom")
        self.assertIsNone(metrics.conceito_predominante({"Ótimo": 0, "Bom": 0, "Suficiente": 0, "Regular": 0}))

    def test_pesos_e_pontos_da_nt(self):
        self.assertEqual(config.PONTOS, {"Ótimo": 1.0, "Bom": 0.75, "Suficiente": 0.5, "Regular": 0.25})
        pesos_esf = {c: p for c, p, _ in config.INDICADORES["eSF"].values()}
        self.assertEqual(pesos_esf, {"C1": 1, "C2": 2, "C3": 2, "C4": 1, "C5": 1, "C6": 1, "C7": 2})
        pesos_esb = {c: p for c, p, _ in config.INDICADORES["eSB"].values()}
        self.assertEqual(pesos_esb, {"B1": 2, "B2": 2, "B3": 2, "B4": 1, "B5": 2, "B6": 1})
        pesos_em = {c: p for c, p, _ in config.INDICADORES["eMulti"].values()}
        self.assertEqual(pesos_em, {"M1": 6, "M2": 4})

    def test_janelas_de_monitoramento_da_figura_2(self):
        self.assertEqual(config.JANELAS["C1"], "30 dias")
        self.assertEqual(config.JANELAS["C2"], "24 meses")
        self.assertEqual({config.JANELAS[f"C{i}"] for i in (3, 4, 5, 6)}, {"12 meses"})
        self.assertEqual(config.JANELAS["C7"], "60 meses")
        self.assertEqual({config.JANELAS["M1"], config.JANELAS["M2"]}, {"4 meses"})
        self.assertEqual({config.JANELAS[f"B{i}"] for i in range(1, 7)}, {"30 dias"})


class AusenciaDeDado(unittest.TestCase):
    def test_indicador_sem_equipes_nao_e_zero(self):
        """Sem equipes avaliadas o indicador fica indefinido (None) e fora da média: não vira nota 0."""
        ind = metrics._indicador("eSF", linha_ind(108, qtdClassificacaoOtimo=0, qtdClassificacaoBom=0))
        self.assertIsNone(ind["pontuacaoMedia"])
        self.assertIsNone(ind["contribuicao"])
        self.assertIsNone(ind["faixa"])

    def test_nota_aproximada_quando_equipes_variam_entre_indicadores(self):
        final = {**linha_ind(), "totalEquipesValidasParaComponente": 3}
        completo = linha_ind(105)  # 3 equipes
        parcial = linha_ind(108, qtdClassificacaoOtimo=0, qtdClassificacaoBom=1, qtdClassificacaoSuficiente=0)
        self.assertFalse(metrics._equipe_qualidade("eSF", [completo], final)["notaAproximada"])
        self.assertTrue(metrics._equipe_qualidade("eSF", [completo, parcial], final)["notaAproximada"])


class Linearidade(unittest.TestCase):
    def test_media_das_notas_individuais_igual_ao_calculo_por_contagens(self):
        """Quando todas as equipes têm todos os indicadores, Σ(peso × pontuação média) é exatamente a média
        das notas individuais calculadas pela fórmula da NT (para qualquer combinação de conceitos)."""
        cos = list(config.INDICADORES["eSB"])
        pesos = [config.INDICADORES["eSB"][c][1] for c in cos]
        equipes = [  # 3 equipes, cada uma com um conceito por indicador B1..B6
            ["Ótimo", "Bom", "Regular", "Suficiente", "Bom", "Ótimo"],
            ["Regular", "Regular", "Bom", "Ótimo", "Suficiente", "Bom"],
            ["Bom", "Ótimo", "Ótimo", "Bom", "Regular", "Suficiente"],
        ]  # fmt: skip
        notas = [sum(config.PONTOS[c] * p for c, p in zip(eq, pesos, strict=True)) for eq in equipes]
        linhas = [linha_ind(co, "eSB", **dist_de([eq[i] for eq in equipes])) for i, co in enumerate(cos)]
        final = {**linha_ind(eq="eSB"), "totalEquipesValidasParaComponente": 3}
        calculada = metrics._equipe_qualidade("eSB", linhas, final)
        self.assertAlmostEqual(calculada["notaMedia"], sum(notas) / 3, places=2)
        self.assertFalse(calculada["notaAproximada"])

    def test_todas_as_combinacoes_de_um_indicador(self):
        for combo in itertools.combinations_with_replacement(CONC, 3):
            d = metrics._dist(linha_ind(**dist_de(combo)))
            esperado = sum(config.PONTOS[c] for c in combo) / 3
            self.assertAlmostEqual(metrics._pontuacao_media(d), esperado)


class Desempenho(unittest.TestCase):
    def test_historico_grande_processa_rapido(self):
        """Meta: 40 quadrimestres (~13 anos) processados em menos de 2 s."""
        relatorio = {
            "_meta": {"nuQuadrimestre": "2026Q1", "descricao": "x"},
            "classificacaoFinalComponente": [
                {**linha_ind(), "tipoOrigem": "QUALIDADE", "totalEquipesValidasParaComponente": 3}
            ],
            "conceitoPorIndicadorQualidade": [linha_ind(co) for co in config.INDICADORES["eSF"]],
            "classificacaoFinalPorDimensaoCvat": [],
        }
        inicio = time.perf_counter()
        for _ in range(40):
            metrics.processar_quadrimestre(relatorio)
        self.assertLess(time.perf_counter() - inicio, 2.0)


if __name__ == "__main__":
    unittest.main()
