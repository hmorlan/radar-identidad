"""Recolección continua de RSS: lo que los feeds muestran entre una edición y otra.

Muchos feeds solo muestran sus 10 notas más recientes (Help Net Security, Biometric
Update). Un medio que publica 15 al día ya perdió las del día anterior cuando la
edición corre a las 5 a.m.: el 20 nov se nos fueron Entrust (Help Net, 18 nov) y
Sumsub (Biometric Update, 19 nov).

``scripts/snapshot_feeds.py`` corre cada 6 horas (workflow "Recolección continua",
sin API de Claude ni de Google) y guarda aquí cada entrada que ve. El recolector de
noticias junta, para cada feed, las entradas en vivo con las guardadas; la ventana
de fechas y los filtros se aplican igual a las dos.

Forma del archivo (JSON)::

    {"version": 1,
     "feeds": {"<feed_url>": {"title": "...",
                              "entries": {"<link>": {"title", "content", "author",
                                                     "published", "tags", "seen"}}}}}

``published`` y ``seen`` van en ISO sin zona, en UTC (como ``_parse_date``).
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

CACHE_ENV = "RECOLECCION_CACHE"
DEFAULT_PATH = "data/recoleccion_cache.json"
KEEP_DAYS = 7
MAX_CONTENT = 4000
_TAG_RE = re.compile(r"<[^>]+>")


def cache_path() -> Path:
    return Path(os.getenv(CACHE_ENV) or DEFAULT_PATH)


def load(path: Optional[Path] = None) -> Dict[str, Any]:
    path = path or cache_path()
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("feeds"), dict):
            return data
    except FileNotFoundError:
        pass
    except Exception as e:  # noqa: BLE001 - una caché rota no detiene la recolección
        logger.warning("Caché de recolección ilegible (%s): %s", path, e)
    return {"version": 1, "feeds": {}}


def save(cache: Dict[str, Any], path: Optional[Path] = None) -> None:
    path = Path(path or cache_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _struct_to_iso(struct: Any) -> Optional[str]:
    if struct and hasattr(struct, "tm_year"):
        try:
            return datetime(*struct[:6]).isoformat()
        except Exception:  # noqa: BLE001
            return None
    return None


def entry_record(entry: Any, now: datetime) -> Optional[Dict[str, Any]]:
    """Lo que se guarda de una entrada de feedparser (o ``None`` si no tiene enlace)."""
    link = (entry.get("link") or "").strip()
    if not link:
        return None
    if getattr(entry, "content", None):
        content = entry.content[0].value
    else:
        content = entry.get("summary") or entry.get("description") or ""
    return {
        "title": entry.get("title", "No Title"),
        "content": _TAG_RE.sub("", content or "")[:MAX_CONTENT],
        "author": entry.get("author", "Unknown"),
        "published": _struct_to_iso(entry.get("published_parsed") or entry.get("updated_parsed")),
        "tags": [t.term for t in entry.get("tags", []) if getattr(t, "term", None)][:12],
        "seen": now.isoformat(),
    }


def merge(cache: Dict[str, Any], feed_url: str, feed_title: str,
          entries: Iterable[Any], now: datetime) -> int:
    """Agrega las entradas nuevas de un feed; devuelve cuántas eran nuevas."""
    slot = cache["feeds"].setdefault(feed_url, {"title": feed_title, "entries": {}})
    if feed_title:
        slot["title"] = feed_title
    new = 0
    cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat()
    for entry in entries:
        rec = entry_record(entry, now)
        if rec is None or (rec["published"] and rec["published"] < cutoff):
            continue
        link = (entry.get("link") or "").strip()
        if link not in slot["entries"]:
            new += 1
            slot["entries"][link] = rec
        else:
            rec["seen"] = slot["entries"][link].get("seen") or rec["seen"]
            slot["entries"][link] = rec
    return new


def prune(cache: Dict[str, Any], now: datetime, keep_days: int = KEEP_DAYS) -> int:
    """Quita lo publicado (o visto) hace más de ``keep_days``; devuelve cuántas quitó."""
    cutoff = now - timedelta(days=keep_days)
    removed = 0
    for url in list(cache["feeds"]):
        entries = cache["feeds"][url].get("entries", {})
        for link in list(entries):
            when = entries[link].get("published") or entries[link].get("seen")
            try:
                old = datetime.fromisoformat(when) < cutoff
            except (TypeError, ValueError):
                old = True
            if old:
                del entries[link]
                removed += 1
        if not entries:
            del cache["feeds"][url]
    return removed


def cached_rows(cache: Dict[str, Any], feed_url: str, skip_links: Iterable[str]) -> List[Dict[str, Any]]:
    """Entradas guardadas de un feed que no vinieron en vivo, listas para procesar."""
    slot = (cache.get("feeds") or {}).get(feed_url) or {}
    skip = set(skip_links)
    rows = []
    for link, rec in (slot.get("entries") or {}).items():
        if link in skip:
            continue
        when = rec.get("published") or rec.get("seen")
        try:
            published = datetime.fromisoformat(when) if when else None
        except ValueError:
            published = None
        if published is None:
            continue
        rows.append({
            "link": link, "title": rec.get("title") or "No Title",
            "content": rec.get("content") or "", "author": rec.get("author") or "Unknown",
            "published": published, "tags": rec.get("tags") or [],
            "summary": (rec.get("content") or "")[:500],
        })
    return rows


def feed_title(cache: Dict[str, Any], feed_url: str) -> str:
    return ((cache.get("feeds") or {}).get(feed_url) or {}).get("title") or ""
