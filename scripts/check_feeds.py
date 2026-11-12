#!/usr/bin/env python3
"""Verifica que las fuentes configuradas respondan y estén vivas.

No usa la API de Anthropic ni cuesta nada: solo descarga cada fuente y reporta
estado HTTP, número de entradas y fecha de la más reciente.

Revisa: feeds RSS de noticias e investigación, arXiv (cs.CR), Mastodon, Bluesky y
los reguladores de ``config/regulators.txt`` (página de prensa directa o
búsqueda en Google News).

Uso:
    python3 scripts/check_feeds.py              # fuentes activas
    python3 scripts/check_feeds.py --pending    # incluye las líneas "# https://..." pendientes
    python3 scripts/check_feeds.py --days 60    # umbral para marcar una fuente como inactiva
    python3 scripts/check_feeds.py --json       # salida para máquinas (la usa source_health_alert.py)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List, Optional

try:
    import feedparser
except ImportError:  # pragma: no cover
    sys.exit("Falta feedparser: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
UA = "Radar-de-Identidad/1.0 (+feed-check)"
TIMEOUT = 25
ARXIV_URL = ("https://export.arxiv.org/api/query?search_query=cat:cs.CR"
             "&sortBy=submittedDate&sortOrder=descending&max_results=10")
# Ventana para preguntar a Google News por un regulador sin página de prensa.
REGULATOR_SEARCH_DAYS = 30

# Veredictos. Solo FALLA dispara la alerta; los demás son informativos.
OK, FAIL, INACTIVE, NO_DATES, NO_RESULTS = "OK", "FALLA", "INACTIVA", "SIN FECHAS", "SIN RESULTADOS"


@dataclass
class Result:
    group: str
    source: str
    verdict: str
    status: Optional[int]
    entries: int
    newest: Optional[str]  # YYYY-MM-DD
    error: str = ""
    pending: bool = False

    @property
    def key(self) -> str:
        return f"{self.group}|{self.source}"


def _load_regulator_module():
    """Load regulator_sources.py without importing the agents package (heavy deps)."""
    path = ROOT / "agents" / "gatherers" / "regulator_sources.py"
    spec = importlib.util.spec_from_file_location("regulator_sources_standalone", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def _fetch_once(url: str, ua: str) -> tuple[int | None, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read(), ""
    except urllib.error.HTTPError as e:
        return e.code, b"", str(e.reason)
    except Exception as e:  # noqa: BLE001 - report any network failure
        return None, b"", type(e).__name__ + ": " + str(e)[:80]


def fetch(url: str, ua: str = UA, attempts: int = 3) -> tuple[int | None, bytes, str]:
    """GET con reintentos: algunos sitios (INCIBE) rechazan a veces una visita con una
    redirección de seguridad o un 404 falso; un fallo aislado no es una fuente caída."""
    result = _fetch_once(url, ua)
    for _ in range(attempts - 1):
        if result[0] == 200:
            break
        time.sleep(2)
        result = _fetch_once(url, ua)
    return result


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


def verdict_for(status, n, newest, err, now, days) -> str:
    if err or status != 200:
        return FAIL
    if newest is None:
        return NO_DATES
    if (now - newest).days > days:
        return INACTIVE
    return OK


def _result(group, source, status, n, newest, err, verdict, pending=False) -> Result:
    return Result(group, source, verdict, status, n,
                  newest.strftime("%Y-%m-%d") if newest else None, err, pending)


def check_arxiv(now: datetime) -> Result:
    status, n, newest, err = check_feed(ARXIV_URL)
    # arXiv cs.CR publica todos los días hábiles: una semana sin nada es una falla.
    v = verdict_for(status, n, newest, err, now, 7)
    return _result("investigación", "arXiv cs.CR", status, n, newest, err, FAIL if v == INACTIVE else v)


def check_regulators(now: datetime, days: int) -> List[Result]:
    """Each regulator: its press page must still parse; its Google search must answer.

    A press page that returns zero rows means the site changed and the scraper is
    blind (FALLA). A Google search with zero results in 30 days is normal for a
    quiet regulator (SIN RESULTADOS), not a failure.
    """
    reg = _load_regulator_module()
    specs = reg.load_regulators(str(CONFIG))
    out = []
    for spec in specs:
        if spec.page:
            status, body, err = fetch(spec.page, reg.BROWSER_UA)
            rows = reg.scrape_press_page(body.decode("utf-8", "replace"), spec.page) if status == 200 else []
            newest = max((r["published"] for r in rows), default=None)
            newest = newest.replace(tzinfo=timezone.utc) if newest else None
            if status == 200 and not rows:
                err = "la página de prensa no devolvió notas (¿cambió el sitio?)"
            v = verdict_for(status, len(rows), newest, err, now, days)
            out.append(_result("reguladores", f"{spec.label} · página", status, len(rows), newest, err, v))
        else:
            status, body, err = fetch(reg.search_url(spec, REGULATOR_SEARCH_DAYS), reg.BROWSER_UA)
            if status != 200:
                out.append(_result("reguladores", f"{spec.label} · Google News", status, 0, None,
                                   err or "HTTP error", FAIL))
                continue
            n, newest = newest_feed_date(body)
            v = OK if n else NO_RESULTS
            out.append(_result("reguladores", f"{spec.label} · Google News", status, n, newest, "", v))
    return out


def check_empresas() -> List[Result]:
    """Empresas observadas: cada búsqueda de Google News debe responder.

    Que no haya notas de identidad sobre una empresa en una semana es normal
    (SIN RESULTADOS); solo una búsqueda que no responde es FALLA.
    """
    reg = _load_regulator_module()
    out = []
    for spec in reg.load_empresas(str(CONFIG)):
        status, body, err = fetch(reg.search_url(spec, 7), reg.BROWSER_UA)
        if status != 200:
            out.append(_result("empresas", spec.label, status, 0, None, err or "HTTP error", FAIL))
            continue
        n, newest = newest_feed_date(body)
        out.append(_result("empresas", spec.label, status, n, newest, "", OK if n else NO_RESULTS))
    return out


def run_checks(include_pending: bool = False, days: int = 60,
               now: Optional[datetime] = None) -> List[Result]:
    now = now or datetime.now(timezone.utc)
    groups: list[tuple[str, str, Callable]] = [
        ("noticias", "rss_feeds.txt", check_feed),
        ("investigación", "research_feeds.txt", check_feed),
        ("mastodon", "mastodon_accounts.txt", check_mastodon),
        ("bluesky", "bluesky_accounts.txt", check_bluesky),
    ]
    results: List[Result] = []
    for group, filename, checker in groups:
        for value, pending in read_entries(CONFIG / filename, include_pending):
            status, n, newest, err = checker(value)
            results.append(_result(group, value, status, n, newest, err,
                                   verdict_for(status, n, newest, err, now, days), pending))
        if group == "investigación":
            results.append(check_arxiv(now))

    results.extend(check_regulators(now, days))
    results.extend(check_empresas())
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pending", action="store_true", help="incluye fuentes comentadas como pendientes")
    ap.add_argument("--days", type=int, default=60, help="días sin publicar para marcar INACTIVA")
    ap.add_argument("--json", action="store_true", help="imprime los resultados como JSON")
    args = ap.parse_args()

    results = run_checks(args.pending, args.days)
    if args.json:
        print(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=1))
    else:
        group = None
        for r in results:
            if r.group != group:
                group = r.group
                print(f"\n== {group}")
            tag = " [pendiente]" if r.pending else ""
            print(f"  {r.verdict:<14} {str(r.status or '-'):<4} {r.entries:>3} entradas  "
                  f"última {r.newest or '-'}  {r.source}{tag}" + (f"  ({r.error})" if r.error else ""))
    problems = sum(1 for r in results if r.verdict == FAIL and not r.pending)
    if not args.json:
        print(f"\nFuentes activas que fallan: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
