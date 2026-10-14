import json
import unittest
from unittest import mock

from helpers import config, dados_temporarios, fonte_simulada, linha_ind, relatorio_exemplo
from siaps_pacuja import client, extract


class Esquema(unittest.TestCase):
    def test_valido(self):
        extract.validar_esquema(relatorio_exemplo())

    def test_campo_faltando(self):
        r = relatorio_exemplo()
        del r["conceitoPorIndicadorQualidade"][0]["qtdClassificacaoBom"]
        with self.assertRaisesRegex(ValueError, "Esquema mudou"):
            extract.validar_esquema(r)

    def test_valor_negativo_ou_tipo_errado(self):
        for ruim in (-1, "3", None, True, 2.5):
            r = relatorio_exemplo()
            r["conceitoPorIndicadorQualidade"][0]["qtdClassificacaoBom"] = ruim
            with self.assertRaises(ValueError):
                extract.validar_esquema(r)

    def test_secao_ou_linha_com_tipo_errado(self):
        with self.assertRaises(ValueError):
            extract.validar_esquema({"classificacaoFinalComponente": {"a": 1}})
        with self.assertRaises(ValueError):
            extract.validar_esquema({"classificacaoFinalComponente": ["texto"]})

    def test_recusa_outro_municipio_ou_uf(self):
        for campo, valor in (("coMunicipioIbge", "230960"), ("sgUf", "SP")):
            r = relatorio_exemplo()
            r["conceitoPorIndicadorQualidade"].append(linha_ind(**{campo: valor}))
            with self.assertRaisesRegex(ValueError, "fora de Pacujá"):
                extract._so_pacuja(r)


class Integridade(unittest.TestCase):
    def test_valido(self):
        extract.validar_integridade(relatorio_exemplo(), "2026Q1")

    def test_periodo_divergente(self):
        with self.assertRaisesRegex(ValueError, "Período divergente"):
            extract.validar_integridade(relatorio_exemplo("2025Q3"), "2026Q1")

    def test_linha_duplicada(self):
        r = relatorio_exemplo()
        r["conceitoPorIndicadorQualidade"].append(dict(r["conceitoPorIndicadorQualidade"][0]))
        with self.assertRaisesRegex(ValueError, "duplicada"):
            extract.validar_integridade(r, "2026Q1")

    def test_total_nao_bate_com_contagens(self):
        r = relatorio_exemplo()
        r["classificacaoFinalComponente"][0]["totalEquipesValidasParaComponente"] = 4
        with self.assertRaisesRegex(ValueError, "Total de equipes"):
            extract.validar_integridade(r, "2026Q1")

    def test_indicador_com_mais_equipes_que_o_total(self):
        r = relatorio_exemplo()
        r["conceitoPorIndicadorQualidade"][0]["qtdClassificacaoRegular"] = 1
        with self.assertRaisesRegex(ValueError, "inconsistente"):
            extract.validar_integridade(r, "2026Q1")

    def test_indicador_sem_linha_final_da_equipe(self):
        r = relatorio_exemplo()
        r["conceitoPorIndicadorQualidade"].append(linha_ind(105, eq="eSB"))
        with self.assertRaisesRegex(ValueError, "inconsistente"):
            extract.validar_integridade(r, "2026Q1")


class Csv(unittest.TestCase):
    def test_neutraliza_formulas(self):
        for perigoso in ("=1+1", "+cmd", "-2+3", "@SUM(A1)", "\tx", "\rx"):
            self.assertEqual(extract.celula_segura(perigoso), "'" + perigoso)
        for ok in ("Cuidado da pessoa", "", 5, -3, None):
            self.assertEqual(extract.celula_segura(ok), ok)

    def test_arquivo_gravado_sem_formulas_e_com_bom(self):
        with dados_temporarios():
            r = relatorio_exemplo()
            r["conceitoPorIndicadorQualidade"][0]["noIndicador"] = '=HYPERLINK("http://x")'
            extract._gravar_csv("2026Q1", r)
            conteudo = (config.CSV_DIR / "pacuja_2026Q1_indicadores_qualidade.csv").read_bytes()
        self.assertTrue(conteudo.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b"'=HYPERLINK", conteudo)
        self.assertIn(b";", conteudo.splitlines()[0])


class Atualizar(unittest.TestCase):
    def test_baixa_so_com_dados_acima_do_piso_e_e_idempotente(self):
        fonte = {"2025Q2": relatorio_exemplo("2025Q2"), "2026Q1": {}}  # 2026Q1 sem dados; 2025Q1 abaixo do piso
        with dados_temporarios(), fonte_simulada(fonte) as buscar:
            self.assertEqual(extract.atualizar(), ["2025Q2"])
            self.assertEqual(sorted(p.name for p in config.RAW_DIR.glob("*.json")), ["2025Q2.json"])
            self.assertEqual(len(list(config.CSV_DIR.glob("*.csv"))), 3)
            self.assertEqual(extract.atualizar(), [])  # 2ª rodada: nada mudou, nenhuma revisão nova
            self.assertEqual(extract.carregar_manifesto()["quadrimestres"]["2025Q2"]["revisao"], 1)
        self.assertNotIn("2025Q1", [c.args[0] for c in buscar.call_args_list])

    def test_manifesto_registra_origem_e_assinaturas(self):
        with dados_temporarios(), fonte_simulada({"2025Q2": relatorio_exemplo("2025Q2")}):
            extract.atualizar()
            m = extract.carregar_manifesto()
            q = m["quadrimestres"]["2025Q2"]
            self.assertEqual(q["filtros"], {"uf": ["CE"], "coMunicipioIbge": ["230990"], "nuQuadrimestre": ["2025Q2"]})
            self.assertEqual(q["metodologia"], config.METODOLOGIA["id"])
            self.assertTrue(q["fonte"].startswith("https://apisiaps.saude.gov.br/"))
            self.assertEqual(q["linhas"]["indicadores_qualidade"], 2)
            self.assertEqual(len(q["sha256"]), 64)
            self.assertEqual(len(q["arquivos"]), 4)  # raw + 3 csv, cada um com SHA-256
            self.assertIsNotNone(m["coleta"]["ultimaBemSucedida"])
            self.assertIsNone(m["coleta"]["ultimoErro"])
            raw = json.loads((config.RAW_DIR / "2025Q2.json").read_text(encoding="utf-8"))
            self.assertEqual(extract.hash_relatorio(raw), q["sha256"])  # assinatura confere com o arquivo

    def test_dado_oficial_alterado_gera_revisao_e_arquiva_a_anterior(self):
        fonte = {"2025Q2": relatorio_exemplo("2025Q2")}
        with dados_temporarios(), fonte_simulada(fonte):
            extract.atualizar()
            antigo = (config.RAW_DIR / "2025Q2.json").read_bytes()
            fonte["2025Q2"]["conceitoPorIndicadorQualidade"][0]["qtdClassificacaoOtimo"] = 0
            fonte["2025Q2"]["conceitoPorIndicadorQualidade"][0]["qtdClassificacaoBom"] = 3
            self.assertEqual(extract.atualizar(), ["2025Q2"])
            self.assertEqual(extract.carregar_manifesto()["quadrimestres"]["2025Q2"]["revisao"], 2)
            arquivadas = list((config.revisoes_dir() / "2025Q2").glob("rev001_*.json"))
            self.assertEqual(len(arquivadas), 1)
            self.assertEqual(arquivadas[0].read_bytes(), antigo)  # histórico oficial preservado byte a byte

    def test_arquivo_anterior_ao_manifesto_nao_gera_revisao_falsa(self):
        fonte = {"2025Q2": relatorio_exemplo("2025Q2")}
        with dados_temporarios() as tmp, fonte_simulada(fonte):
            config.RAW_DIR.mkdir(parents=True)
            (config.RAW_DIR / "2025Q2.json").write_text(json.dumps(fonte["2025Q2"]), encoding="utf-8")
            self.assertEqual(extract.atualizar(), [])
            self.assertEqual(extract.carregar_manifesto()["quadrimestres"]["2025Q2"]["revisao"], 1)
            self.assertTrue((tmp / "manifest.json").exists())

    def test_falha_preserva_ultima_revisao_valida_e_registra_erro(self):
        fonte = {"2025Q2": relatorio_exemplo("2025Q2"), "2025Q3": relatorio_exemplo("2025Q3")}
        with dados_temporarios(), fonte_simulada(fonte):
            extract.atualizar()
            antes = {p.name: p.read_bytes() for p in config.RAW_DIR.glob("*.json")}
            fonte["2025Q2"]["conceitoPorIndicadorQualidade"][0]["qtdClassificacaoBom"] = 99  # mas Q3 ok
            with self.assertRaises(ValueError):
                extract.atualizar()
            depois = {p.name: p.read_bytes() for p in config.RAW_DIR.glob("*.json")}
            self.assertEqual(antes, depois)  # nada foi publicado, nem o quadrimestre válido
            coleta = extract.carregar_manifesto()["coleta"]
            self.assertIn("ValueError", coleta["ultimoErro"])
            self.assertIsNotNone(coleta["ultimaBemSucedida"])  # a última coleta boa continua registrada

    def test_mudanca_de_formato_interrompe(self):
        fonte = {"2025Q2": relatorio_exemplo("2025Q2")}
        del fonte["2025Q2"]["classificacaoFinalComponente"][0]["totalEquipesValidasParaComponente"]
        with dados_temporarios(), fonte_simulada(fonte):
            with self.assertRaisesRegex(ValueError, "Esquema mudou"):
                extract.atualizar()
            self.assertFalse(list(config.RAW_DIR.glob("*.json")))

    def test_fonte_sem_nenhum_dado_nao_apaga_nem_publica(self):
        with dados_temporarios(), fonte_simulada({"2025Q2": {}}), self.assertRaises(client.ColetaErro):
            extract.atualizar()

    def test_fonte_exigindo_autenticacao_interrompe_a_coleta(self):
        with (
            dados_temporarios(),
            fonte_simulada({"2025Q2": relatorio_exemplo("2025Q2")}) as buscar,
            self.assertRaises(client.AutenticacaoExigida),
        ):
            buscar.side_effect = client.AutenticacaoExigida("HTTP 401")
            extract.atualizar()

    def test_respeita_intervalo_entre_consultas(self):
        fonte = {"2025Q2": relatorio_exemplo("2025Q2"), "2025Q3": relatorio_exemplo("2025Q3")}
        with dados_temporarios(), fonte_simulada(fonte), mock.patch("siaps_pacuja.extract.time.sleep") as sleep:
            extract.atualizar()
        sleep.assert_called_once_with(config.INTERVALO_ENTRE_CONSULTAS_S)


class Trava(unittest.TestCase):
    def test_impede_coletas_simultaneas(self):
        with dados_temporarios(), extract._trava():
            with self.assertRaises(extract.ColetaEmAndamento), extract._trava():
                pass
            with fonte_simulada({"2025Q2": relatorio_exemplo("2025Q2")}), self.assertRaises(extract.ColetaEmAndamento):
                extract.atualizar()
            self.assertTrue(config.lock_path().exists())  # a trava do 1º processo não foi removida pelo 2º

    def test_trava_e_liberada_apos_uso_mesmo_com_erro(self):
        with dados_temporarios():
            with self.assertRaises(RuntimeError), extract._trava():
                raise RuntimeError("falhou")
            self.assertFalse(config.lock_path().exists())

    def test_trava_abandonada_expira(self):
        with dados_temporarios():
            config.RAW_DIR.mkdir(parents=True)
            config.lock_path().write_text("123")
            with mock.patch.object(config, "LOCK_EXPIRA_S", -1), extract._trava():
                pass


class Obsolescencia(unittest.TestCase):
    def test_dias_desde_ultima_coleta(self):
        self.assertIsNone(extract.dias_desde_ultima_coleta({"coleta": {"ultimaBemSucedida": None}}))
        dias = extract.dias_desde_ultima_coleta({"coleta": {"ultimaBemSucedida": "2020-01-01T00:00:00Z"}})
        self.assertGreater(dias, 365)


if __name__ == "__main__":
    unittest.main()
