import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from helpers import config  # noqa: F401
from siaps_pacuja import server


class Servidor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = server.criar_servidor(0)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def post(self, headers=None):
        req = urllib.request.Request(self.base + "/api/atualizar", method="POST", headers=headers or {})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_escuta_so_em_localhost(self):
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")

    def test_cabecalhos_de_seguranca(self):
        with urllib.request.urlopen(self.base + "/") as r:
            h = r.headers
        self.assertIn("default-src 'self'", h["Content-Security-Policy"])
        self.assertEqual(h["X-Content-Type-Options"], "nosniff")
        self.assertEqual(h["X-Frame-Options"], "DENY")
        self.assertEqual(h["Cache-Control"], "no-store")

    def test_post_sem_cabecalho_e_rejeitado(self):
        with mock.patch("siaps_pacuja.extract.atualizar") as m:
            self.assertEqual(self.post()[0], 404)
        m.assert_not_called()

    def test_post_ok(self):
        with (
            mock.patch("siaps_pacuja.extract.atualizar", return_value=["2026Q1"]),
            mock.patch("siaps_pacuja.pipeline.build"),
        ):
            self.assertEqual(self.post({"X-Requested-With": "painel"}), (200, {"ok": True, "alterados": ["2026Q1"]}))

    def test_erro_nao_vaza_detalhes(self):
        with mock.patch("siaps_pacuja.extract.atualizar", side_effect=RuntimeError("C:\\segredo\\caminho")):
            status, corpo = self.post({"X-Requested-With": "painel"})
        self.assertEqual(status, 502)
        self.assertNotIn("segredo", json.dumps(corpo))

    def test_nao_serve_arquivos_fora_do_dashboard(self):
        for caminho in ("/../src/siaps_pacuja/config.py", "/%2e%2e/src/siaps_pacuja/config.py"):
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(urllib.request.Request(self.base + caminho))


if __name__ == "__main__":
    unittest.main()
