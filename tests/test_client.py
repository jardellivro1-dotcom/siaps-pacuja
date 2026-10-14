import io
import json
import unittest
import urllib.error
from unittest import mock

from helpers import config  # noqa: F401  (ajusta sys.path)
from siaps_pacuja import client


def resposta(obj):
    r = mock.MagicMock()
    r.read.side_effect = lambda n=-1: json.dumps(obj).encode()[: n if n >= 0 else None]
    r.__enter__.return_value = r
    return r


def http_erro(codigo):
    return urllib.error.HTTPError("https://x", codigo, "erro", {}, io.BytesIO(b""))


URL = "https://apisiaps.saude.gov.br/api/public/filtros/competencias"


class Cliente(unittest.TestCase):
    def setUp(self):
        sleep = mock.patch("time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    def abrir(self, **kw):
        return mock.patch.object(client._OPENER, "open", **kw)

    def test_lista_so_quadrimestres_validos_e_ordenados(self):
        dados = [
            {"nuCompetencia": "202501", "quadrimestre": False},
            {"nuCompetencia": "2026Q1", "quadrimestre": True},
            {"nuCompetencia": "2025Q2", "quadrimestre": True},
            {"nuCompetencia": "../../etc", "quadrimestre": True},  # identificador malicioso é descartado
            {"nuCompetencia": "2025Q9", "quadrimestre": True},
        ]
        with self.abrir(return_value=resposta(dados)):
            self.assertEqual([q["nuCompetencia"] for q in client.listar_quadrimestres()], ["2025Q2", "2026Q1"])

    def test_filtro_envia_apenas_pacuja(self):
        with self.abrir(return_value=resposta({})) as m:
            client.buscar_quadrimestre("2026Q1")
        req = m.call_args.args[0]
        self.assertEqual(
            json.loads(req.data), {"uf": ["CE"], "coMunicipioIbge": ["230990"], "nuQuadrimestre": ["2026Q1"]}
        )
        self.assertTrue(req.full_url.startswith("https://apisiaps.saude.gov.br/api/public/"))

    def test_recusa_quadrimestre_invalido(self):
        for ruim in ("", "2026", "2026Q4", "2026Q1; drop", "../2026Q1"):
            with self.assertRaises(ValueError):
                client.buscar_quadrimestre(ruim)

    def test_recusa_destinos_nao_autorizados(self):
        for url in (
            "http://apisiaps.saude.gov.br/x",  # sem TLS
            "https://evil.example.com/x",
            "https://apisiaps.saude.gov.br.evil.com/x",
            "https://user:pw@apisiaps.saude.gov.br/x",
            "file:///etc/passwd",
        ):
            with self.abrir() as m, self.assertRaises(ValueError):
                client._request(url)
            m.assert_not_called()

    def test_nao_segue_redirecionamento(self):
        handler = client._SemRedirecionamento()
        self.assertIsNone(handler.redirect_request(mock.Mock(), mock.Mock(), 302, "Found", {}, "https://evil/"))

    def test_certificado_e_verificado(self):
        import ssl

        ctx = next(h for h in client._OPENER.handlers if hasattr(h, "_context"))._context
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)

    def test_autenticacao_exigida_interrompe_sem_repetir(self):
        for codigo in (401, 403):
            with self.abrir(side_effect=http_erro(codigo)) as m, self.assertRaises(client.AutenticacaoExigida):
                client._request(URL)
            self.assertEqual(m.call_count, 1)

    def test_erro_4xx_nao_repete_e_5xx_repete(self):
        with self.abrir(side_effect=http_erro(404)) as m, self.assertRaises(client.ColetaErro):
            client._request(URL)
        self.assertEqual(m.call_count, 1)
        with self.abrir(side_effect=[http_erro(503), resposta([])]) as m:
            self.assertEqual(client._request(URL), [])
        self.assertEqual(m.call_count, 2)

    def test_falha_apos_tentativas_e_resposta_invalida(self):
        with self.abrir(side_effect=urllib.error.URLError("fora")) as m, self.assertRaises(client.ColetaErro):
            client._request(URL, retries=2)
        self.assertEqual(m.call_count, 2)
        lixo = mock.MagicMock()
        lixo.read.return_value = b"<html>nao e json</html>"
        lixo.__enter__.return_value = lixo
        with self.abrir(return_value=lixo), self.assertRaises(client.ColetaErro):
            client._request(URL, retries=1)

    def test_limite_de_tamanho_da_resposta(self):
        grande = mock.MagicMock()
        grande.read.return_value = b"0" * (config.MAX_RESPOSTA_BYTES + 1)
        grande.__enter__.return_value = grande
        with self.abrir(return_value=grande), self.assertRaises(client.ColetaErro):
            client._request(URL, retries=1)

    def test_formato_inesperado(self):
        with self.abrir(return_value=resposta({"a": 1})), self.assertRaises(client.ColetaErro):
            client.listar_quadrimestres()
        with self.abrir(return_value=resposta([1])), self.assertRaises(client.ColetaErro):
            client.buscar_quadrimestre("2026Q1")


if __name__ == "__main__":
    unittest.main()
