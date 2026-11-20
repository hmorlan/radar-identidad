"""Recolección continua (20 nov: Help Net y Biometric Update solo muestran 10 notas)."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import feedparser

from agents.gatherers import feed_cache
from agents.gatherers.news_gatherer import NewsGatherer

NOW = datetime(2026, 11, 20, 11, 0)


def _rss(items):
    body = "".join(
        f"<item><title>{t}</title><link>{l}</link><description>{d}</description>"
        f"<pubDate>{p}</pubDate></item>" for t, l, d, p in items)
    return f"<?xml version='1.0'?><rss version='2.0'><channel><title>Help Net</title>{body}</channel></rss>"


OLD = ("Fraudsters feed the right face into identity checks", "https://h.test/entrust",
       "deepfake identity verification", "Wed, 18 Nov 2026 09:00:00 GMT")
NEW = ("Something else today", "https://h.test/today", "nada", "Thu, 19 Nov 2026 20:00:00 GMT")
ANCIENT = ("Viejo", "https://h.test/viejo", "x", "Sun, 01 Nov 2026 09:00:00 GMT")


class FeedCacheTest(unittest.TestCase):
    def test_merge_prune_y_rows(self):
        cache = {"version": 1, "feeds": {}}
        parsed = feedparser.parse(_rss([OLD, NEW, ANCIENT]))
        self.assertEqual(feed_cache.merge(cache, "u", "Help Net", parsed.entries, NOW), 2)
        self.assertEqual(feed_cache.merge(cache, "u", "Help Net", parsed.entries, NOW), 0)
        rows = feed_cache.cached_rows(cache, "u", {"https://h.test/today"})
        self.assertEqual([r["link"] for r in rows], ["https://h.test/entrust"])
        self.assertEqual(rows[0]["published"], datetime(2026, 11, 18, 9, 0))
        self.assertEqual(feed_cache.prune(cache, NOW + timedelta(days=10)), 2)
        self.assertEqual(cache["feeds"], {})

    def test_save_y_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.json"
            self.assertEqual(feed_cache.load(path), {"version": 1, "feeds": {}})
            feed_cache.save({"version": 1, "feeds": {"u": {"title": "t", "entries": {}}}}, path)
            self.assertIn("u", feed_cache.load(path)["feeds"])
            path.write_text("{roto")
            self.assertEqual(feed_cache.load(path)["feeds"], {})


class GathererUsaLaCacheTest(unittest.TestCase):
    def _gatherer(self, cache, live_xml):
        g = NewsGatherer.__new__(NewsGatherer)
        g.feed_cache = cache
        g.start_time = datetime(2026, 11, 18, 6, 0)
        g.end_time = datetime(2026, 11, 20, 5, 59)
        resp = SimpleNamespace(content=live_xml.encode(), headers={}, raise_for_status=lambda: None)
        g.feed_session = g.direct_session = SimpleNamespace(get=lambda *a, **k: resp)
        return g

    def test_la_nota_que_ya_no_trae_el_feed_entra_desde_la_cache(self):
        cache = {"version": 1, "feeds": {}}
        feed_cache.merge(cache, "https://h.test/feed", "Help Net",
                         feedparser.parse(_rss([OLD])).entries, NOW)
        g = self._gatherer(cache, _rss([NEW]))
        spec = SimpleNamespace(url="https://h.test/feed", use_proxy=None, filtro="identidad")
        arts = g._fetch_feed(spec)
        self.assertEqual([a.url for a in arts], ["https://h.test/entrust"])  # NEW no pasa el filtro
        self.assertEqual(arts[0].source, "Help Net")

    def test_si_el_feed_falla_queda_lo_guardado(self):
        cache = {"version": 1, "feeds": {}}
        feed_cache.merge(cache, "https://h.test/feed", "Help Net",
                         feedparser.parse(_rss([OLD])).entries, NOW)
        g = self._gatherer(cache, "")
        def boom(*a, **k):
            raise __import__("requests").RequestException("caído")
        g.feed_session = g.direct_session = SimpleNamespace(get=boom)
        with mock.patch("time.sleep"):
            arts = g._fetch_feed(SimpleNamespace(url="https://h.test/feed", use_proxy=None, filtro=None))
        self.assertEqual(len(arts), 1)


if __name__ == "__main__":
    unittest.main()
