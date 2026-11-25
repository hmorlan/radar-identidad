#!/usr/bin/env python3
"""Texto completo de las fuentes de cada nota, para la revisión editorial (sin costo).

Las tareas programadas de revisión (Fable y la verificación) no pueden abrir páginas
con WebFetch: en una corrida programada nadie aprueba la lectura (23 nov: las 14
lecturas fallaron con "permission request ... not answered in time"). GitHub Actions
sí tiene red, así que tras publicar se baja aquí la página de cada nota (y la de su
"vía", si llegó por una red) y se sube como artefacto ``fuentes``. No se publica.

Salida (``--out``):
    fuentes.json          una entrada por enlace: nota, papel (fuente/via), url pedida,
                          url final, estado HTTP, título, fecha declarada, caracteres
                          y archivo de texto (o el error)
    NN-<item_id>-<papel>.txt   el texto principal de la página

Uso:
    python3 scripts/fuentes_notas.py --web-dir web --date 2026-11-25 --out fuentes
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

UA = "Mozilla/5.0 (compatible; RadarDeIdentidad/1.0; +https://radar.hirammorlan.com)"
MAX_CHARS = 60000
TIMEOUT = 25
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_JSONLD_DATE = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_CANDIDATE_RE = re.compile(r"article|content|post|entry|story|abstract", re.I)


def links_de_la_edicion(summary: Dict[str, Any]) -> List[Dict[str, str]]:
    """Enlaces a revisar: la fuente de cada nota y, si la hay, su vía."""
    out: List[Dict[str, str]] = []
    vistos = set()
    for n, nota in enumerate((summary.get("edition") or {}).get("notas") or [], start=1):
        item_id = str(nota.get("item_id") or f"nota{n}")
        pares = [("fuente", nota.get("url"))]
        via = nota.get("via")
        if isinstance(via, dict):
            pares.append(("via", via.get("url")))
        for papel, url in pares:
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                continue
            if urlparse(url).hostname and urlparse(url).hostname.endswith(".onion"):
                continue  # nunca
            if (url, papel) in vistos:
                continue
            vistos.add((url, papel))
            out.append({"nota": n, "item_id": item_id, "papel": papel, "url": url,
                        "titulo_nota": str(nota.get("title") or "")[:200]})
    return out


def published_date(soup: Any) -> str:
    for attrs in ({"property": "article:published_time"}, {"property": "og:published_time"},
                  {"name": "article:published_time"}, {"itemprop": "datePublished"},
                  {"name": "citation_date"}, {"name": "date"}, {"name": "pubdate"}):
        tag = soup.find("meta", attrs=attrs)
        m = _DATE_RE.search((tag.get("content") or "").strip()) if tag else None
        if m:
            return m.group(1)
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        m = _JSONLD_DATE.search(script.string or script.get_text() or "")
        if m:
            return m.group(1)
    tag = soup.find("time", attrs={"datetime": True})
    m = _DATE_RE.search(tag["datetime"].strip()) if tag else None
    return m.group(1) if m else ""


def texto_principal(soup: Any) -> str:
    """El texto del artículo: el candidato más largo entre <article>, <main> y los
    bloques de contenido; si ninguno pasa de 200 caracteres, el <body>."""
    for el in soup.find_all(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
        el.decompose()
    candidatos = [soup.find("article"), soup.find("main"),
                  soup.find(class_=_CANDIDATE_RE), soup.find(id=_CANDIDATE_RE)]
    textos = [c.get_text(separator=" ", strip=True) for c in candidatos if c]
    textos = [t for t in textos if len(t) > 200]
    if textos:
        texto = max(textos, key=len)
    else:
        body = soup.find("body")
        texto = body.get_text(separator=" ", strip=True) if body else ""
    return re.sub(r"\s+", " ", texto)[:MAX_CHARS]


def bajar(url: str, session: Optional[Any] = None) -> Dict[str, Any]:
    import requests
    from bs4 import BeautifulSoup

    s = session or requests
    try:
        resp = s.get(url, timeout=TIMEOUT, allow_redirects=True, headers={
            "User-Agent": UA, "Accept-Language": "es,en;q=0.8"})
    except Exception as e:  # noqa: BLE001 - se reporta, no detiene
        return {"estado": None, "error": f"{type(e).__name__}: {e}"[:300]}
    info: Dict[str, Any] = {"estado": resp.status_code, "url_final": resp.url}
    if resp.status_code >= 400:
        info["error"] = f"HTTP {resp.status_code}"
        return info
    tipo = resp.headers.get("content-type", "")
    if "html" not in tipo and "xml" not in tipo:
        info["error"] = f"no es HTML ({tipo[:60]})"
        return info
    soup = BeautifulSoup(resp.content, "html.parser")
    info["titulo"] = (soup.title.get_text(strip=True) if soup.title else "")[:300]
    info["fecha_declarada"] = published_date(soup)
    info["texto"] = texto_principal(soup)
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--web-dir", default="web")
    ap.add_argument("--date", required=True)
    ap.add_argument("--out", default="fuentes")
    args = ap.parse_args()

    summary_path = Path(args.web_dir) / "data" / args.date / "summary.json"
    if not summary_path.exists():
        print(f"No existe {summary_path}", file=sys.stderr)
        return 1
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    import requests
    session = requests.Session()
    registro, completos = [], 0
    for link in links_de_la_edicion(summary):
        info = bajar(link["url"], session)
        texto = info.pop("texto", "") or ""
        entrada = {**link, **info, "caracteres": len(texto)}
        if texto:
            nombre = f"{link['nota']:02d}-{link['item_id']}-{link['papel']}.txt"
            (out / nombre).write_text(
                f"URL: {link['url']}\nURL final: {info.get('url_final', '')}\n"
                f"Título: {info.get('titulo', '')}\nFecha declarada: {info.get('fecha_declarada', '')}\n\n{texto}\n",
                encoding="utf-8")
            entrada["archivo"] = nombre
            if len(texto) >= 1000:
                completos += 1
        else:
            entrada["aviso"] = "sin texto completo: verificar contra el texto recolectado"
        registro.append(entrada)
        estado = entrada.get("error") or f"{len(texto)} caracteres"
        print(f"nota {link['nota']} {link['papel']:<6} {estado:<24} {link['url'][:90]}")
        time.sleep(1)

    (out / "fuentes.json").write_text(json.dumps(
        {"date": args.date, "enlaces": registro,
         "con_texto_completo": completos, "total": len(registro)},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{completos} de {len(registro)} enlaces con texto completo (≥1000 caracteres) en {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
