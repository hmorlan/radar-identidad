#!/usr/bin/env python3
"""Recolección continua: guarda lo que muestran los feeds RSS (sin API, sin costo).

Corre cada 6 horas (workflow "Recolección continua"). Baja cada feed de
config/rss_feeds.txt y guarda sus entradas en la caché de agents/gatherers/feed_cache.py
(sin filtrar: el filtro de identidad y la ventana de fechas se aplican en la edición).
Así un feed que solo muestra 10 notas no pierde las de ayer antes de las 5 a.m.

Uso:
    python3 scripts/snapshot_feeds.py [--config config/rss_feeds.txt] [--cache data/recoleccion_cache.json]
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.gatherers import feed_cache  # noqa: E402

UA = "Mozilla/5.0 (compatible; RadarDeIdentidad/1.0; +https://radar.hirammorlan.com)"


def feed_urls(config: Path) -> list[str]:
    urls = []
    for line in config.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url = line.split()[0]
        if url.startswith(("http://", "https://")) and url not in urls:
            urls.append(url)
    return urls


def fetch(url: str):
    last = None
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": UA})
            resp.raise_for_status()
            return feedparser.parse(resp.content, response_headers={
                "content-type": resp.headers.get("content-type", "")})
        except requests.RequestException as e:
            last = e
            time.sleep(2)
    raise last  # type: ignore[misc]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(ROOT / "config" / "rss_feeds.txt"))
    ap.add_argument("--cache", default=None, help="por defecto RECOLECCION_CACHE o data/recoleccion_cache.json")
    args = ap.parse_args()

    path = Path(args.cache) if args.cache else feed_cache.cache_path()
    cache = feed_cache.load(path)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    urls = feed_urls(Path(args.config))

    def one(url):
        try:
            parsed = fetch(url)
            return url, parsed, None
        except Exception as e:  # noqa: BLE001
            return url, None, e

    new_total, failed = 0, []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for url, parsed, err in pool.map(one, urls):
            if err is not None or parsed is None:
                failed.append(url)
                print(f"FALLA  {url}: {err}")
                continue
            title = (parsed.feed.get("title") or "").strip() or urlparse(url).netloc.removeprefix("www.")
            new = feed_cache.merge(cache, url, title, parsed.entries, now)
            new_total += new
            if new:
                print(f"+{new:<3}  {title[:50]}")

    removed = feed_cache.prune(cache, now)
    feed_cache.save(cache, path)
    stored = sum(len(f.get("entries", {})) for f in cache["feeds"].values())
    print(f"\n{len(urls)} feeds · {new_total} entradas nuevas · {removed} viejas quitadas · "
          f"{stored} guardadas · {len(failed)} feeds con falla")
    return 0


if __name__ == "__main__":
    sys.exit(main())
