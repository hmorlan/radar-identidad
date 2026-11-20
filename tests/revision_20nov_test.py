"""Revisión de Hiram del 20 nov: enlaces, fechas y nombres de fuente."""
import unittest
from types import SimpleNamespace

from agents.edition_notes import note_origin
from agents.source_names import clean_source


def _item(**kw):
    base = dict(url="https://x.test/a", source="Fuente", published="2026-11-19T10:00:00",
                source_type="rss", author="", metadata={})
    base.update(kw)
    return SimpleNamespace(**base)


class NombresTest(unittest.TestCase):
    def test_nombres(self):
        self.assertEqual(clean_source("Security News | TechCrunch"), "TechCrunch")
        self.assertEqual(clean_source("www.theregister.com - Articles"), "The Register")
        self.assertEqual(clean_source("I-D list for Web Authorization Protocol RSS Feed"), "IETF (OAuth)")
        self.assertEqual(clean_source("I-D list for Workload Identity in Multi System Environments RSS Feed"),
                         "IETF (Workload Identity in Multi System Environments)")
        self.assertEqual(clean_source("Banking Dive - Latest News"), "Banking Dive")
        self.assertEqual(clean_source("BleepingComputer"), "BleepingComputer")
        self.assertEqual(clean_source(""), "")


class OrigenDeLaNotaTest(unittest.TestCase):
    def test_post_que_difunde_un_articulo(self):
        it = _item(url="https://bsky.app/profile/x/post/1", source="Bluesky", source_type="bluesky",
                   author="@derechosdigitales.org",
                   metadata={"enlace_original": "https://es.wired.com/articulos/a",
                             "author_display_name": "Derechos Digitales"})
        url, source, _, via = note_origin(it)
        self.assertEqual(url, "https://es.wired.com/articulos/a")
        self.assertEqual(source, "WIRED en Español")
        self.assertEqual(via, {"source": "Bluesky (Derechos Digitales)",
                               "url": "https://bsky.app/profile/x/post/1"})

    def test_post_sin_enlace_queda_igual(self):
        it = _item(url="https://bsky.app/p/1", source="Bluesky", source_type="bluesky")
        self.assertEqual(note_origin(it)[:2], ("https://bsky.app/p/1", "Bluesky"))
        self.assertIsNone(note_origin(it)[3])

    def test_arxiv_usa_la_fecha_de_envio(self):
        it = _item(source="arXiv (criptografía y seguridad)", source_type="arxiv",
                   published="2026-11-20T00:00:00-05:00", metadata={"enviado": "2026-11-18"})
        self.assertEqual(note_origin(it)[2], "2026-11-18")


class EnlaceRelativoTest(unittest.TestCase):
    def test_news_resuelve_enlaces_relativos(self):
        from datetime import datetime
        from agents.gatherers.news_gatherer import NewsGatherer
        xml = ("<?xml version='1.0'?><rss version='2.0'><channel><title>IETF</title><item>"
               "<title>Security Events for Revocation of Agent Delegations</title>"
               "<link>/doc/draft-x/</link><pubDate>Thu, 19 Nov 2026 14:59:40 GMT</pubDate>"
               "</item></channel></rss>")
        g = NewsGatherer.__new__(NewsGatherer)
        g.feed_cache = {}
        g.start_time, g.end_time = datetime(2026, 11, 18), datetime(2026, 11, 20)
        resp = SimpleNamespace(content=xml.encode(), headers={}, raise_for_status=lambda: None)
        g.feed_session = g.direct_session = SimpleNamespace(get=lambda *a, **k: resp)
        arts = g._fetch_feed(SimpleNamespace(url="https://datatracker.ietf.org/group/oauth/documents/feed/",
                                             use_proxy=None, filtro=None))
        self.assertEqual(arts[0].url, "https://datatracker.ietf.org/doc/draft-x/")


if __name__ == "__main__":
    unittest.main()
