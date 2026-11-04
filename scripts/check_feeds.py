#!/usr/bin/env python3
"""Verifica que las fuentes configuradas respondan y estén vivas.

No usa la API de Anthropic ni cuesta nada: solo descarga cada feed y reporta
estado HTTP, número de entradas y fecha de la más reciente.

Uso:
    python3 scripts/check_feeds.py              # fuentes activas
    python3 scripts/check_feeds.py --pending    # incluye las líneas "# https://..." pendientes
    python3 scripts/check_feeds.py --days 60    # umbral para marcar una fuente como inactiva
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import feedparser
except ImportError:  # pragma: no cover
    sys.exit("Falta feedparser: pip install -r requirements.txt")

CONFIG = Path(__file__).resolve().parent.parent / "config"
UA = "Radar-de-Identidad/1.0 (+feed-check)"
TIMEOUT = 25


def is_source_token(token: str, filename: str) -> bool:
    """Whether a commented-out token looks like a source (URL, account or handle)."""
    if token.startswith("http"):
        return True
    if filename.startswith("mastodon"):
        return "@" in token
    if filename.startswith("bluesky"):
        return "." in token and token[0].isalnum() and not token[0].isdigit()
    return False


def read_entries(path: Path, include_pending: bool) -> list[tuple[str, bool]]:
    """Return (value, is_pending) pairs from a source list file."""
    out = []
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        pending = False
        if line.startswith("#"):
            token = line.lstrip("#").strip().split()[0] if line.lstrip("#").strip() else ""
            if not (include_pending and is_source_token(token, path.name)):
                continue
            line, pending = token, True
        out.append((line.split()[0], pending))
    return out


def fetch(url: str) -> tuple[int | None, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read(), ""
    except urllib.error.HTTPError as e:
        return e.code, b"", str(e.reason)
    except Exception as e:  # noqa: BLE001 - report any network failure
        return None, b"", type(e).__name__ + ": " + str(e)[:80]


def newest_feed_date(body: bytes) -> tuple[int, datetime | None]:
    parsed = feedparser.parse(body)
    newest = None
    for e in parsed.entries:
        t = e.get("published_parsed") or e.get("updated_parsed")
        if t:
            d = datetime(*t[:6], tzinfo=timezone.utc)
            newest = d if newest is None or d > newest else newest
    return len(parsed.entries), newest


def check_feed(url: str):
    status, body, err = fetch(url)
    if status != 200:
        return status, 0, None, err or "HTTP error"
    n, newest = newest_feed_date(body)
    return status, n, newest, "" if n else "no parece un feed RSS/Atom"


def check_mastodon(account: str):
    user, _, instance = account.lstrip("@").partition("@")
    return check_feed(f"https://{instance}/@{user}.rss")


def check_bluesky(handle: str):
    url = ("https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
           f"?actor={handle}&limit=20&filter=posts_no_replies")
    status, body, err = fetch(url)
    if status != 200:
        return status, 0, None, err or "HTTP error"
    items = json.loads(body).get("feed", [])
    dates = []
    for it in items:
        ts = it.get("post", {}).get("record", {}).get("createdAt")
        if ts:
            dates.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
    return status, len(items), max(dates) if dates else None, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pending", action="store_true", help="incluye fuentes comentadas como pendientes")
    ap.add_argument("--days", type=int, default=60, help="días sin publicar para marcar INACTIVA")
    args = ap.parse_args()

    groups = [
        ("rss_feeds.txt", check_feed),
        ("research_feeds.txt", check_feed),
        ("mastodon_accounts.txt", check_mastodon),
        ("bluesky_accounts.txt", check_bluesky),
    ]
    now = datetime.now(timezone.utc)
    problems = 0
    for filename, checker in groups:
        entries = read_entries(CONFIG / filename, args.pending)
        print(f"\n== {filename} ({len(entries)})")
        for value, pending in entries:
            status, n, newest, err = checker(value)
            age = (now - newest).days if newest else None
            if err or status != 200:
                verdict = "FALLA"
            elif age is None:
                verdict = "SIN FECHAS"
            elif age > args.days:
                verdict = "INACTIVA"
            else:
                verdict = "OK"
            if verdict != "OK" and not pending:
                problems += 1
            tag = " [pendiente]" if pending else ""
            when = newest.strftime("%Y-%m-%d") if newest else "-"
            print(f"  {verdict:<10} {str(status or '-'):<4} {n:>3} entradas  última {when}  {value}{tag}"
                  + (f"  ({err})" if err else ""))
    print(f"\nFuentes activas con problemas: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
