"""Tests sin red del recolector de reguladores."""
import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from agents.gatherers import regulator_sources as rs


GOBMX = r'''<div>\n<article>\n <p><time datetime=\"2026-11-03 10:00:00\">3 de noviembre de 2026</time></p>\n <h2>La CONDUSEF alerta sobre la posible suplantación de identidad de dos Instituciones Financieras</h2>\n <a class=\"small-link\" href=\"/condusef/prensa/alerta-suplantacion?idiom=es\">Continuar leyendo<\/a>\n<\/article>\n<article>\n <p><time datetime=\"2026-11-02 10:00:00\">2 de noviembre de 2026</time></p>\n <h2>Índice de Capitalización de la banca múltiple</h2>\n <a href=\"/cnbv/prensa/icap\">Continuar leyendo<\/a>\n<\/article>'''

ARGOB = '''<div class="row"><a href="/noticias/la-aaip-sanciono" class="panel panel-default"><div class="panel-body">
<time datetime='2026-11-02 09:46:34'>02 de noviembre de 2026</time> <h3>La AAIP sancionó a empresas por datos personales</h3>
<p class="text-muted"><p>Tratamiento ilegítimo de datos personales.</p></div></a>
<a href="/noticias/otra" class="panel panel-default"><div class="panel-body">
<time datetime='2026-10-28 09:00:00'>28 de octubre de 2026</time> <h3>Asamblea del Consejo Federal</h3></div></a></div>'''

WORDPRESS = '''<article id="post-1" class="et_pb_post"><p class="post-meta"><span class="published">29 de octubre de 2026</span></p>
<h2 class="entry-title"><a href="https://www.bcra.gob.ar/noticias/fraude-virtual/">Recomendaciones para evitar estafas virtuales</a></h2></article>'''


class ParseTest(unittest.TestCase):
    def test_parse_regulators_with_optional_page(self):
        specs = rs.parse_regulators([
            "# comentario", "", "mx | CNBV | https://gob.mx/cnbv/ | https://www.gob.mx/cnbv/archivo/prensa",
            "ES | AEPD | aepd.es", "línea inválida",
        ])
        self.assertEqual(len(specs), 2)
        self.assertEqual(specs[0].country, "MX")
        self.assertEqual(specs[0].site, "gob.mx/cnbv")
        self.assertEqual(specs[0].page, "https://www.gob.mx/cnbv/archivo/prensa")
        self.assertIsNone(specs[1].page)

    def test_evergreen_filter(self):
        spec = rs.RegulatorSpec("CL", "CMF", "cmfchile.cl")
        self.assertTrue(rs.is_evergreen("Formulario de Registro - CMF Chile", spec))
        self.assertTrue(rs.is_evergreen("Glosario - CCN-CERT", spec))
        self.assertTrue(rs.is_evergreen("CMF - CMF Chile", spec))
        self.assertFalse(rs.is_evergreen(
            "CMF emite normativa que ajusta los requisitos de autenticación reforzada - CMF Chile", spec))

    def test_dates(self):
        self.assertEqual(rs._parse_any_date("2026-10-19 11:22:00"), datetime(2026, 10, 19, 11, 22))
        self.assertEqual(rs._parse_any_date("29 de octubre de 2026"), datetime(2026, 10, 29, 12, 0))
        self.assertIsNone(rs._parse_any_date("sin fecha"))


class ScrapeTest(unittest.TestCase):
    def test_gobmx_escaped_listing(self):
        rows = rs.scrape_press_page(GOBMX, "https://www.gob.mx/condusef/archivo/prensa")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["url"], "https://www.gob.mx/condusef/prensa/alerta-suplantacion")
        self.assertIn("suplantación", rows[0]["title"])
        self.assertEqual(rows[0]["published"].date().isoformat(), "2026-11-03")

    def test_argentina_gob_listing(self):
        rows = rs.scrape_press_page(ARGOB, "https://www.argentina.gob.ar/aaip/noticias")
        self.assertEqual([r["url"] for r in rows], [
            "https://www.argentina.gob.ar/noticias/la-aaip-sanciono",
            "https://www.argentina.gob.ar/noticias/otra",
        ])
        self.assertIn("datos personales", rows[0]["summary"])

    def test_wordpress_listing(self):
        rows = rs.scrape_press_page(WORDPRESS, "https://www.bcra.gob.ar/noticias/")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], "https://www.bcra.gob.ar/noticias/fraude-virtual/")
        self.assertEqual(rows[0]["published"].date().isoformat(), "2026-10-29")


class FakeResponse:
    def __init__(self, text="", content=b""):
        self.text = text
        self.content = content or text.encode()

    def raise_for_status(self):
        pass


class CollectTest(unittest.TestCase):
    def test_press_page_applies_topic_filter_window_and_seen_cache(self):
        spec = rs.RegulatorSpec("MX", "CONDUSEF", "gob.mx/condusef", "https://www.gob.mx/condusef/archivo/prensa")
        session = mock.Mock()
        session.headers = {}
        session.get.return_value = FakeResponse(GOBMX)
        with TemporaryDirectory() as d:
            seen = rs.SeenCache(Path(d) / "seen.json")
            items = rs.collect([spec], datetime(2026, 11, 1), datetime(2026, 11, 4), session=session,
                               seen=seen, today="2026-11-04", pause=0)
            # Solo la alerta de suplantación: el índice de capitalización no pasa el filtro temático.
            self.assertEqual([i.url for i in items], ["https://www.gob.mx/condusef/prensa/alerta-suplantacion"])
            seen.save("2026-11-04")
            # Al día siguiente la misma nota ya no se repite.
            seen2 = rs.SeenCache(Path(d) / "seen.json")
            again = rs.collect([spec], datetime(2026, 11, 1), datetime(2026, 11, 5), session=session,
                               seen=seen2, today="2026-11-05", pause=0)
            self.assertEqual(again, [])

    def test_google_news_path_resolves_and_skips_evergreen(self):
        spec = rs.RegulatorSpec("CL", "CMF", "cmfchile.cl")
        rss = """<?xml version="1.0"?><rss><channel>
<item><title>CMF ajusta requisitos de autenticación reforzada - CMF Chile</title>
<link>https://news.google.com/rss/articles/ABC?oc=5</link><pubDate>Tue, 03 Nov 2026 12:00:00 GMT</pubDate></item>
<item><title>Formulario de Registro - CMF Chile</title>
<link>https://news.google.com/rss/articles/DEF?oc=5</link><pubDate>Tue, 03 Nov 2026 12:00:00 GMT</pubDate></item>
<item><title>Nota vieja sobre fraude con tarjetas - CMF Chile</title>
<link>https://news.google.com/rss/articles/GHI?oc=5</link><pubDate>Tue, 03 Mar 2020 12:00:00 GMT</pubDate></item>
</channel></rss>"""
        session = mock.Mock()
        session.headers = {}
        session.get.return_value = FakeResponse(rss)
        with mock.patch.object(rs, "decode_google_news_url", return_value="https://www.cmfchile.cl/noticia-1") as dec:
            items = rs.collect([spec], datetime(2026, 11, 1), datetime(2026, 11, 4), session=session, pause=0)
        self.assertEqual(dec.call_count, 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://www.cmfchile.cl/noticia-1")
        self.assertEqual(items[0].title, "CMF ajusta requisitos de autenticación reforzada")

    def test_decode_google_news_url(self):
        session = mock.Mock()
        session.get.return_value = FakeResponse('<div data-n-a-sg="SIG" data-n-a-ts="1700000000"></div>')
        inner = json.dumps(["garturlres", "https://www.gob.mx/condusef/prensa/x", 1])
        session.post.return_value = FakeResponse(")]}'\n\n" + json.dumps([["wrb.fr", "Fbv4je", inner]]))
        url = rs.decode_google_news_url("https://news.google.com/rss/articles/XYZ?oc=5", session)
        self.assertEqual(url, "https://www.gob.mx/condusef/prensa/x")
        self.assertEqual(rs.decode_google_news_url("https://example.com/a", session), "https://example.com/a")


if __name__ == "__main__":
    unittest.main()
