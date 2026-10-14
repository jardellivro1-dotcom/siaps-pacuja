import json
import unittest
import urllib.error
from unittest import mock

from helpers import config  # noqa: F401  (ajusta sys.path)
from siaps_pacuja import client


def resposta(obj):
    r = mock.MagicMock()
    r.read.return_value = json.dumps(obj).encode()
    r.__enter__.return_value = r
    return r


class Cliente(unittest.TestCase):
    def test_lista_so_quadrimestres_ordenados(self):
        dados = [
            {"nuCompetencia": "202501", "quadrimestre": False},
            {"nuCompetencia": "2026Q1", "quadrimestre": True},
            {"nuCompetencia": "2025Q2", "quadrimestre": True},
        ]
        with mock.patch("urllib.request.urlopen", return_value=resposta(dados)):
            self.assertEqual([q["nuCompetencia"] for q in client.listar_quadrimestres()], ["2025Q2", "2026Q1"])

    def test_filtro_envia_apenas_pacuja(self):
        with mock.patch("urllib.request.urlopen", return_value=resposta({})) as m:
            client.buscar_quadrimestre("2026Q1")
        req = m.call_args.args[0]
        self.assertEqual(
            json.loads(req.data), {"uf": ["CE"], "coMunicipioIbge": ["230990"], "nuQuadrimestre": ["2026Q1"]}
        )
        self.assertTrue(req.full_url.startswith("https://apisiaps.saude.gov.br/api/public/"))

    def test_retry_e_sucesso(self):
        falha = urllib.error.URLError("fora")
        with mock.patch("urllib.request.urlopen", side_effect=[falha, resposta([])]) as m, mock.patch("time.sleep"):
            self.assertEqual(client._request("https://x"), [])
        self.assertEqual(m.call_count, 2)

    def test_falha_apos_tentativas(self):
        with (
            mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("fora")),
            mock.patch("time.sleep"),
            self.assertRaises(RuntimeError),
        ):
            client._request("https://x", retries=2)


if __name__ == "__main__":
    unittest.main()
