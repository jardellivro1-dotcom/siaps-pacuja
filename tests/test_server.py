import http.client
import json
import threading
import unittest
from unittest import mock

from helpers import config
from siaps_pacuja import extract, server

H = {"X-Requested-With": "painel"}


class Base(unittest.TestCase):
    somente_leitura = False

    @classmethod
    def setUpClass(cls):
        cls.srv = server.criar_servidor(0, cls.somente_leitura)
        cls.porta = cls.srv.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.porta}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        server.Handler._ultima_coleta = -1e9
        p = mock.patch.object(config, "INTERVALO_MIN_ATUALIZACAO_S", 0)
        p.start()
        self.addCleanup(p.stop)

    def requisicao(self, metodo="POST", caminho="/api/atualizar", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=5)
        conn.request(metodo, caminho, headers=headers or {})
        r = conn.getresponse()
        corpo = r.read()
        conn.close()
        return r.status, (json.loads(corpo) if corpo[:1] == b"{" else corpo), r

    def post(self, headers=None, **kw):
        status, corpo, _ = self.requisicao("POST", headers=H if headers is None else headers, **kw)
        return status, corpo


class Servidor(Base):
    def test_escuta_so_em_localhost(self):
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")

    def test_cabecalhos_de_seguranca(self):
        _, _, r = self.requisicao("GET", "/")
        csp = r.getheader("Content-Security-Policy")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("script-src 'self';", csp)  # sem CDN: só scripts da própria origem
        self.assertNotIn("unsafe-eval", csp)
        self.assertEqual(r.getheader("X-Content-Type-Options"), "nosniff")
        self.assertEqual(r.getheader("X-Frame-Options"), "DENY")
        self.assertEqual(r.getheader("Cache-Control"), "no-store")
        self.assertEqual(r.getheader("Referrer-Policy"), "no-referrer")

    def test_nao_revela_versao_do_python(self):
        _, _, r = self.requisicao("GET", "/")
        self.assertNotIn("Python", r.getheader("Server"))

    def test_post_sem_cabecalho_csrf_e_rejeitado(self):
        with mock.patch("siaps_pacuja.extract.atualizar") as m:
            self.assertEqual(self.post({})[0], 404)
        m.assert_not_called()

    def test_post_em_outra_rota_e_rejeitado(self):
        self.assertEqual(self.post(H, caminho="/api/outra")[0], 404)

    def test_post_ok(self):
        with (
            mock.patch("siaps_pacuja.extract.atualizar", return_value=["2026Q1"]),
            mock.patch("siaps_pacuja.pipeline.build"),
        ):
            self.assertEqual(self.post(), (200, {"ok": True, "alterados": ["2026Q1"]}))

    def test_erro_nao_vaza_detalhes(self):
        with mock.patch("siaps_pacuja.extract.atualizar", side_effect=RuntimeError("C:\\segredo\\caminho")):
            status, corpo = self.post()
        self.assertEqual(status, 502)
        self.assertNotIn("segredo", json.dumps(corpo))

    def test_coleta_em_andamento_retorna_409(self):
        with mock.patch("siaps_pacuja.extract.atualizar", side_effect=extract.ColetaEmAndamento("x")):
            self.assertEqual(self.post()[0], 409)

    def test_estado_da_coleta(self):
        status, corpo, _ = self.requisicao("GET", "/api/estado")
        self.assertEqual(status, 200)
        self.assertEqual(corpo["versao"], config.VERSAO_APP)
        self.assertTrue(corpo["atualizacaoHabilitada"])
        self.assertIn("coleta", corpo)

    def test_nao_serve_arquivos_fora_do_dashboard(self):
        caminhos = (
            "/../src/siaps_pacuja/config.py",
            "/%2e%2e/src/siaps_pacuja/config.py",
            "/..%5csrc",
            "/..%5c..%5csrc%5csiaps_pacuja%5cconfig.py",
            "/%2e%2e%5c%2e%2e%5cdata%5cmanifest.json",
            "/..%2fdata%2fmanifest.json",
            "/data/manifest.json",
            "/C:/Windows/win.ini",
            "/%00",
        )
        for caminho in caminhos:
            status, corpo, r = self.requisicao("GET", caminho)
            if status in (301, 302):  # segue o redirecionamento: o destino também não pode vazar nada
                status, corpo, r = self.requisicao("GET", r.getheader("Location").replace(self.base, ""))
            corpo = corpo if isinstance(corpo, bytes) else b""
            # Pode devolver 404 ou, no máximo, a própria página inicial; nunca arquivos de src/ ou data/.
            self.assertTrue(status == 404 or b"Painel de desempenho" in corpo, (caminho, status))
            for segredo in (b"MUNICIPIO_IBGE", b"schemaVersao", b"Index of", b"siaps_pacuja"):
                self.assertNotIn(segredo, corpo, caminho)

    def test_sem_listagem_de_diretorios(self):
        self.assertEqual(self.requisicao("GET", "/vendor/")[0], 404)
        self.assertEqual(self.requisicao("GET", "/csv/")[0], 404)

    def test_serve_arquivos_do_painel(self):
        for caminho in ("/", "/app.js", "/style.css", "/vendor/chart.umd.min.js"):
            self.assertEqual(self.requisicao("GET", caminho)[0], 200, caminho)


class HostOrigem(Base):
    def test_host_diferente_e_barrado_contra_dns_rebinding(self):
        for host in ("evil.example.com", f"evil.example.com:{self.porta}", f"127.0.0.1.evil.com:{self.porta}"):
            for metodo, caminho in (("GET", "/"), ("GET", "/api/estado"), ("POST", "/api/atualizar")):
                status, _, _ = self.requisicao(metodo, caminho, {**H, "Host": host})
                self.assertEqual(status, 421, (host, metodo, caminho))

    def test_localhost_e_aceito(self):
        with mock.patch("siaps_pacuja.extract.atualizar", return_value=[]), mock.patch("siaps_pacuja.pipeline.build"):
            self.assertEqual(self.post({**H, "Host": f"localhost:{self.porta}"})[0], 200)

    def test_origem_externa_e_rejeitada(self):
        with mock.patch("siaps_pacuja.extract.atualizar") as m:
            self.assertEqual(self.post({**H, "Origin": "https://evil.example.com"})[0], 403)
            self.assertEqual(self.post({**H, "Origin": "null"})[0], 403)
        m.assert_not_called()

    def test_origem_propria_e_aceita(self):
        with mock.patch("siaps_pacuja.extract.atualizar", return_value=[]), mock.patch("siaps_pacuja.pipeline.build"):
            self.assertEqual(self.post({**H, "Origin": self.base})[0], 200)


class LimiteDeTaxa(Base):
    def test_no_maximo_uma_coleta_por_intervalo(self):
        with (
            mock.patch.object(config, "INTERVALO_MIN_ATUALIZACAO_S", 60),
            mock.patch("siaps_pacuja.extract.atualizar", return_value=[]) as m,
            mock.patch("siaps_pacuja.pipeline.build"),
        ):
            self.assertEqual(self.post()[0], 200)
            status, corpo, r = self.requisicao("POST", headers=H)
            self.assertEqual(status, 429)
            self.assertTrue(int(r.getheader("Retry-After")) > 0)
        self.assertEqual(m.call_count, 1)

    def test_requisicoes_simultaneas_sao_serializadas(self):
        liberar, iniciou = threading.Event(), threading.Event()

        def lenta():
            iniciou.set()
            liberar.wait(5)
            return []

        resultados = []
        with mock.patch("siaps_pacuja.extract.atualizar", side_effect=lenta), mock.patch("siaps_pacuja.pipeline.build"):
            t = threading.Thread(target=lambda: resultados.append(self.post()[0]))
            t.start()
            self.assertTrue(iniciou.wait(5))
            self.assertEqual(self.post()[0], 409)  # a 2ª chamada não inicia outra coleta
            liberar.set()
            t.join(5)
        self.assertEqual(resultados, [200])


class SomenteLeitura(Base):
    somente_leitura = True

    def test_escrita_desligada(self):
        with mock.patch("siaps_pacuja.extract.atualizar") as m:
            self.assertEqual(self.post()[0], 403)
        m.assert_not_called()

    def test_estado_informa_que_atualizacao_esta_desabilitada(self):
        _, corpo, _ = self.requisicao("GET", "/api/estado")
        self.assertFalse(corpo["atualizacaoHabilitada"])


if __name__ == "__main__":
    unittest.main()
