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
            "DIF publishes a verifiable credentials interop profile",
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


class EmpresasYReguladoresTest(unittest.TestCase):
    def test_parse_empresas_and_search_url(self):
        from urllib.parse import unquote, urlparse, parse_qs
        from agents.gatherers import regulator_sources as rs
        specs = rs.parse_empresas([
            "# comentario",
            'MX | Coppel y BanCoppel | "Coppel" OR "BanCoppel"',
            "MX | incompleta",
        ])
        self.assertEqual(len(specs), 1)
        url = rs.search_url(specs[0], 2)
        q = parse_qs(urlparse(url).query)["q"][0]
        self.assertEqual(q, '("Coppel" OR "BanCoppel") when:2d')  # sin site: ni palabras clave
        self.assertIn("gl=MX", url)

    def test_us_regulators_search_in_english(self):
        from urllib.parse import urlparse, parse_qs
        from agents.gatherers import regulator_sources as rs
        [ftc] = rs.parse_regulators(["US | FTC | ftc.gov"])
        url = rs.search_url(ftc, 3)
        q = parse_qs(urlparse(url).query)["q"][0]
        self.assertTrue(q.startswith("site:ftc.gov ("))
        self.assertIn('"identity theft"', q)
        self.assertIn("gl=US", url)
        self.assertTrue(rs.is_evergreen("What should I do when a debt collector contacts me?", ftc))
        self.assertTrue(rs.TOPIC_RE.search("FTC sues data broker over location data"))

    def test_max_per_spec(self):
        from datetime import datetime
        from agents.gatherers import regulator_sources as rs
        [spec] = rs.parse_empresas(["MX | Meta (Muse) | Muse Meta"])
        items = "".join(
            f"<item><title>Muse, el agente de IA de Meta, nota {i} - Medio</title>"
            f"<link>https://news.google.com/rss/articles/x{i}</link>"
            "<pubDate>Wed, 11 Nov 2026 10:00:00 GMT</pubDate></item>" for i in range(8))
        rss = f'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>{items}</channel></rss>'
        session = mock.Mock()
        session.headers = {}
        session.get.return_value = mock.Mock(content=rss.encode(), raise_for_status=lambda: None)
        with mock.patch.object(rs, "decode_google_news_url", side_effect=lambda link, s: link.replace(
                "news.google.com/rss/articles", "medio.example")):
            got = rs.collect([spec], datetime(2026, 11, 10), datetime(2026, 11, 12),
                             session=session, pause=0, max_per_spec=4)
        self.assertEqual(len(got), 4)

    def test_press_wires_and_english_watches(self):
        from urllib.parse import urlparse, parse_qs
        from agents.gatherers import regulator_sources as rs
        self.assertTrue(rs.is_press_wire("Acme Joins Agentic AI Foundation - GlobeNewswire"))
        self.assertTrue(rs.is_press_wire("Acme launches agent ID - PR Newswire"))
        self.assertFalse(rs.is_press_wire("Linux Foundation launches Agent Name Service - IT Brief Australia"))
        [watch] = rs.parse_empresas(['GLOBAL | Protocolos | "Agent Name Service"'])
        self.assertIn("gl=US", rs.search_url(watch, 2))
        self.assertTrue(rs.TOPIC_RE.search("Linux Foundation launches Agent Name Service for AI agents"))

    def test_config_files_parse(self):
        from agents.gatherers import regulator_sources as rs
        root = Path(__file__).resolve().parent.parent / "config"
        empresas = rs.load_empresas(str(root))
        self.assertGreaterEqual(len(empresas), 10)
        self.assertTrue(all(e.query for e in empresas))
        regs = rs.load_regulators(str(root))
        self.assertTrue({"FTC", "CFPB", "FinCEN", "SUGEF"} <= {r.name for r in regs})


class TituloEnEspanolTest(unittest.TestCase):
    def test_schema_keeps_titulo_and_drops_it_when_empty(self):
        from agents.analysis_schema import AnalyzedItemModel
        row = AnalyzedItemModel.model_validate(
            {"id": "a", "source_title": "Session theft", "titulo": "Robo de sesiones", "summary": "x"}
        ).model_dump()
        self.assertEqual(row["titulo"], "Robo de sesiones")

    def test_site_shows_spanish_title_and_keeps_original(self):
        from generators.json_generator import JSONGenerator
        gen = JSONGenerator.__new__(JSONGenerator)
        gen._markdown_to_html = lambda t: t
        items = gen._simplify_items([
            {"item": {"id": "1", "title": "Passkeys reach 1B users", "content": "c", "url": "https://a.example"},
             "titulo": "Las passkeys llegan a mil millones de usuarios", "summary": "s"},
            {"item": {"id": "2", "title": "Ya en español", "content": "c", "url": "https://b.example"},
             "titulo": "", "summary": "s"},
        ])
        by_id = {i["id"]: i for i in items}
        self.assertEqual(by_id["1"]["title"], "Las passkeys llegan a mil millones de usuarios")
        self.assertEqual(by_id["1"]["title_original"], "Passkeys reach 1B users")
        self.assertEqual(by_id["2"]["title"], "Ya en español")
        self.assertNotIn("title_original", by_id["2"])

    def test_analyzed_item_roundtrip(self):
        from agents.base import AnalyzedItem, CollectedItem
        it = CollectedItem(id="1", title="T", content="c", url="https://a.example", author="",
                           published="2026-11-11T00:00:00", source="s", source_type="news")
        a = AnalyzedItem(item=it, summary="s", importance_score=60, reasoning="r", themes=[], titulo="Título")
        self.assertEqual(AnalyzedItem.from_dict(a.to_dict()).titulo, "Título")


if __name__ == "__main__":
    unittest.main()
