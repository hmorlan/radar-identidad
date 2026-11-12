"""Fuentes: filtro previo de identidad, directiva filtro= y enlaces de Bluesky (sin red)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agents.gatherers import identity_filter
from agents.gatherers.news_gatherer import NewsGatherer
from agents.gatherers import social_gatherer as sg


class IdentityFilterTest(unittest.TestCase):
    def test_keeps_identity_topics(self):
        for text in [
            "Ataque de phishing contra clientes de un banco",
            "Robo de cuentas con códigos de doble factor",
            "Le Sénat adopte l'identité numérique européenne",
            "Session token theft bypasses MFA",
            "Estafas con voz clonada por IA",
            "Multiples vulnérabilités dans le greffon OpenID Connect",
            "Airbnb lanzará un agente de viajes con inteligencia artificial",
            "Nueva ley de protección de datos personales en Chile",
        ]:
            self.assertTrue(identity_filter.matches(text), text)

    def test_drops_ambiguous_general_news(self):
        for text in [
            "El Congreso inicia la sesión extraordinaria",
            "La verificación de las obligaciones fiscales del Estado",
            "El partido mantiene una identidad política diferenciada",
            "Bolsa Mexicana espera nuevas emisiones de acciones en 2027",
            "Acceso a financiamiento para pymes",
            "Vulnérabilité dans le noyau Linux",
            "",
        ]:
            self.assertFalse(identity_filter.matches(text), text)


class FeedDirectiveTest(unittest.TestCase):
    def test_filtro_directive_is_parsed(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "rss_feeds.txt").write_text(
            "# comentario\n"
            "https://a.example/feed\n"
            "https://b.example/feed  filtro=identidad\n"
            "https://c.example/feed  proxy=off filtro=identidad  # nota\n"
            "https://d.example/feed  filtro=otra\n",
            encoding="utf-8",
        )
        g = NewsGatherer(config_dir=str(tmp), data_dir=str(tmp))
        got = {s.url: (s.filtro, s.use_proxy) for s in g.feed_specs}
        self.assertEqual(got["https://a.example/feed"], (None, None))
        self.assertEqual(got["https://b.example/feed"], ("identidad", None))
        self.assertEqual(got["https://c.example/feed"], ("identidad", False))
        self.assertEqual(got["https://d.example/feed"], (None, None))  # filtro desconocido: se ignora

    def test_filtered_feed_drops_unrelated_entries(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "rss_feeds.txt").write_text("https://b.example/feed  filtro=identidad\n", encoding="utf-8")
        g = NewsGatherer(config_dir=str(tmp), data_dir=str(tmp), lookback_hours=24 * 3650)
        rss = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
        <item><title>Campa\xc3\xb1a de phishing roba credenciales</title><link>https://b.example/1</link>
          <pubDate>Mon, 09 Nov 2026 10:00:00 GMT</pubDate><description>x</description></item>
        <item><title>Nuevo tel\xc3\xa9fono plegable</title><link>https://b.example/2</link>
          <pubDate>Mon, 09 Nov 2026 10:00:00 GMT</pubDate><description>c\xc3\xa1mara</description></item>
        </channel></rss>"""
        resp = mock.Mock(content=rss, headers={"content-type": "application/rss+xml"})
        resp.raise_for_status = lambda: None
        with mock.patch.object(g.feed_session, "get", return_value=resp):
            arts = g._fetch_feed(g.feed_specs[0])
        self.assertEqual([a.url for a in arts], ["https://b.example/1"])


class BlueskyLinksTest(unittest.TestCase):
    def test_full_links_from_facets_and_card(self):
        record = {
            "text": "Nueva nota: techcrunch.com/2026/11/1...",
            "facets": [{"features": [{"$type": "app.bsky.richtext.facet#link",
                                      "uri": "https://techcrunch.com/2026/11/11/nota-completa/"}]}],
            "embed": {"external": {"uri": "https://techcrunch.com/2026/11/11/nota-completa/"}},
        }
        view = {"embed": {"external": {"uri": "https://example.org/otra"}}}
        self.assertEqual(sg._bluesky_links(record, view),
                         ["https://techcrunch.com/2026/11/11/nota-completa/", "https://example.org/otra"])

    def test_bluesky_skips_reposts_and_caps(self):
        g = sg.SocialGatherer.__new__(sg.SocialGatherer)
        g.is_in_date_range = lambda d: True
        g.generate_id = lambda *a: "|".join(a)
        g.extract_keywords = lambda t: []

        def post(i, repost=False):
            item = {"post": {"uri": f"at://did/app.bsky.feed.post/{i}",
                             "author": {"handle": "otra.bsky.social" if repost else "eff.org"},
                             "record": {"text": f"post {i}", "createdAt": "2026-11-11T10:00:00Z"}}}
            if repost:
                item["reason"] = {"$type": "app.bsky.feed.defs#reasonRepost"}
            return item
        feed = {"feed": [post(0, repost=True)] + [post(i) for i in range(1, 15)]}
        resp = mock.Mock()
        resp.json.return_value = feed
        resp.raise_for_status = lambda: None
        with mock.patch.object(sg.requests, "get", return_value=resp) as get, \
             mock.patch.dict("os.environ", {"BLUESKY_MAX_POSTS_PER_HANDLE": "10"}):
            posts = g._fetch_bluesky_user("eff.org")
        self.assertEqual(get.call_args.kwargs["params"]["filter"], "posts_no_replies")
        self.assertEqual(len(posts), 10)
        self.assertTrue(all(p.author == "@eff.org" for p in posts))


if __name__ == "__main__":
    unittest.main()
