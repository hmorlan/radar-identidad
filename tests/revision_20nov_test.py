"""Revisión de Hiram del 20 nov: enlaces, fechas y nombres de fuente."""
import unittest
from types import SimpleNamespace

from agents.edition_notes import note_origin
from generators.source_names import clean_source


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
    def _post(self, **meta):
        base = {"enlace_original": "https://es.wired.com/articulos/a",
                "author_display_name": "Derechos Digitales"}
        base.update(meta)
        return _item(url="https://bsky.app/profile/x/post/1", source="Bluesky", source_type="bluesky",
                     author="@derechosdigitales.org", published="2026-11-19T16:25:39", metadata=base)

    def test_post_que_difunde_un_articulo(self):
        o = note_origin(self._post(fecha_original="2026-11-17"))
        self.assertEqual(o["url"], "https://es.wired.com/articulos/a")
        self.assertEqual(o["source"], "WIRED en Español")
        self.assertEqual(o["published"], "2026-11-17")   # la del artículo, no la del post
        self.assertEqual(o["via"], {"source": "Bluesky (Derechos Digitales)",
                                    "url": "https://bsky.app/profile/x/post/1",
                                    "published": "2026-11-19T16:25:39"})

    def test_sin_fecha_del_original_no_hereda_la_del_post(self):
        o = note_origin(self._post())
        self.assertEqual(o["published"], "")
        self.assertEqual(o["via"]["published"], "2026-11-19T16:25:39")

    def test_post_sin_enlace_queda_igual(self):
        o = note_origin(_item(url="https://bsky.app/p/1", source="Bluesky", source_type="bluesky"))
        self.assertEqual((o["url"], o["source"], o["via"]), ("https://bsky.app/p/1", "Bluesky", None))

    def test_arxiv_usa_la_fecha_de_envio(self):
        o = note_origin(_item(source="arXiv (criptografía y seguridad)", source_type="arxiv",
                              published="2026-11-20T00:00:00-05:00", metadata={"enviado": "2026-11-18"}))
        self.assertEqual((o["published"], o["fecha_tipo"]), ("2026-11-18", "publicacion"))

    def test_arxiv_sin_fecha_de_envio_se_marca_como_anuncio(self):
        o = note_origin(_item(source="arXiv", source_type="arxiv",
                              published="2026-11-20T00:00:00-05:00", metadata={}))
        self.assertEqual((o["published"], o["fecha_tipo"]), ("2026-11-20T00:00:00-05:00", "anuncio"))


class FechaDeLaPaginaTest(unittest.TestCase):
    def test_metadatos_estandar(self):
        from bs4 import BeautifulSoup
        from agents.edition_notes import published_date
        html = lambda h: BeautifulSoup(h, "html.parser")
        self.assertEqual(published_date(html('<meta property="article:published_time" '
                                             'content="2026-11-17T13:00:00.000Z">')), "2026-11-17")
        self.assertEqual(published_date(html('<script type="application/ld+json">'
                                             '{"datePublished":"2026-11-16T07:00:00-06:00"}</script>')),
                         "2026-11-16")
        self.assertEqual(published_date(html('<time datetime="2026-11-15">x</time>')), "2026-11-15")
        self.assertEqual(published_date(html("<p>sin fecha</p>")), "")

    def test_el_post_baja_el_original(self):
        import asyncio
        from unittest import mock
        from agents import edition_notes as en
        post = SimpleNamespace(item=self_item(), importance_score=70)
        with mock.patch.object(en, "_fetch_page", return_value=("x" * 3000, "2026-11-17")) as fetch:
            asyncio.run(en.enrich_full_text([("social", post)]))
        fetch.assert_called_once_with("https://es.wired.com/articulos/a")
        self.assertEqual(post.item.metadata["fecha_original"], "2026-11-17")


def self_item():
    return _item(url="https://bsky.app/profile/x/post/1", source="Bluesky", source_type="bluesky",
                 content="post corto", metadata={"enlace_original": "https://es.wired.com/articulos/a"})


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
