"""Hacker News en Redes (20 nov): búsquedas de identidad, filtro y vía."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from agents.edition_notes import note_origin
from agents.gatherers.social_gatherer import SocialGatherer


def _hit(oid, title, points=50, url="https://example.org/a", ts=1795564800):
    return {"objectID": oid, "title": title, "url": url, "points": points,
            "num_comments": 12, "author": "pg", "created_at_i": ts}


class HackerNewsTest(unittest.TestCase):
    def _gatherer(self, queries):
        d = Path(tempfile.mkdtemp())
        (d / "hackernews.txt").write_text("# comentario\n" + "\n".join(queries) + "\n", encoding="utf-8")
        g = SocialGatherer(config_dir=str(d), data_dir=str(d), lookback_hours=72, target_date="2026-11-20")
        return g

    def test_lee_busquedas_de_varias_palabras(self):
        g = self._gatherer(["passkey", "account takeover"])
        self.assertEqual(g.hackernews_queries, ["passkey", "account takeover"])

    def test_filtra_identidad_lanzamientos_y_duplicados(self):
        g = self._gatherer(["passkey", "OAuth"])
        hits = [_hit("1", "Attackers abuse OAuth consent to take over accounts"),
                _hit("2", "A new Rust web framework"),
                _hit("3", "Show HN: My passkey manager"),
                _hit("1", "Attackers abuse OAuth consent to take over accounts")]
        resp = SimpleNamespace(json=lambda: {"hits": hits}, raise_for_status=lambda: None)
        with mock.patch("agents.gatherers.social_gatherer.requests.get", return_value=resp) as get:
            items = g._collect_hackernews()
        self.assertEqual([i.metadata["platform_id"] for i in items], ["1"])
        it = items[0]
        self.assertEqual((it.source, it.source_type), ("Hacker News", "hackernews"))
        self.assertEqual(it.url, "https://news.ycombinator.com/item?id=1")
        self.assertEqual(it.metadata["enlace_original"], "https://example.org/a")
        params = get.call_args.kwargs["params"]
        self.assertIn("points>=20", params["numericFilters"])
        self.assertEqual(g.collection_status["hackernews"]["status"], "success")

    def test_busqueda_caida_no_tumba_las_demas(self):
        g = self._gatherer(["passkey", "OAuth"])
        ok = SimpleNamespace(json=lambda: {"hits": [_hit("9", "Passkey phishing via fake enrollment")]},
                             raise_for_status=lambda: None)
        with mock.patch("agents.gatherers.social_gatherer.requests.get",
                        side_effect=[RuntimeError("caída"), ok]):
            items = g._collect_hackernews()
        self.assertEqual(len(items), 1)
        self.assertEqual(g.collection_status["hackernews"]["status"], "partial")

    def test_la_nota_enlaza_al_original_y_hn_es_la_via(self):
        it = SimpleNamespace(url="https://news.ycombinator.com/item?id=1", source="Hacker News",
                             source_type="hackernews", author="pg", published="2026-11-19T10:00:00",
                             metadata={"enlace_original": "https://www.theregister.com/x",
                                       "author_display_name": "Hacker News",
                                       "fecha_original": "2026-11-18"})
        o = note_origin(it)
        self.assertEqual((o["url"], o["source"], o["published"]),
                         ("https://www.theregister.com/x", "The Register", "2026-11-18"))
        self.assertEqual(o["via"]["url"], "https://news.ycombinator.com/item?id=1")


if __name__ == "__main__":
    unittest.main()


class FiltroPorCuentaTest(unittest.TestCase):
    def test_cuenta_generalista_solo_aporta_identidad(self):
        from agents.gatherers import social_gatherer as sg
        g = sg.SocialGatherer.__new__(sg.SocialGatherer)
        g.is_in_date_range = lambda d: True
        g.generate_id = lambda *a: "|".join(a)
        g.extract_keywords = lambda t: []
        g.account_filters = {"campuscodi.risky.biz": "identidad"}

        def post(i, text):
            return {"post": {"uri": f"at://did/app.bsky.feed.post/{i}",
                             "author": {"handle": "campuscodi.risky.biz"},
                             "record": {"text": text, "createdAt": "2026-11-19T10:00:00Z"}}}
        feed = {"feed": [post(1, "New ransomware gang hits a hospital"),
                         post(2, "Attackers bypass MFA with stolen session tokens")]}
        resp = mock.Mock()
        resp.json.return_value = feed
        resp.raise_for_status = lambda: None
        with mock.patch.object(sg.requests, "get", return_value=resp):
            posts = g._fetch_bluesky_user("campuscodi.risky.biz")
        self.assertEqual([p.title for p in posts], ["Attackers bypass MFA with stolen session tokens"])
