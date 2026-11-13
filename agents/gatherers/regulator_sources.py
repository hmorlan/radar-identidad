"""Recolector de reguladores y organismos públicos sin RSS utilizable.

Muchos reguladores de México, España y Latinoamérica no publican RSS o bloquean a
los lectores automáticos. Este módulo los consulta a través del RSS de búsqueda de
Google News (``site:<dominio>`` + palabras clave de identidad, fraude y
ciberseguridad), descarta páginas fijas (glosarios, formularios, registros) y
resuelve el enlace de redirección de Google al enlace original del regulador, que
es el que debe citarse.

La lista de reguladores vive en ``config/regulators.txt``.

El mismo mecanismo sirve para las **empresas observadas** (``config/empresas.txt``):
bancos, retailers, aerolíneas y plataformas que adoptan identidad digital o agentes
de IA. Para ellas no se busca ``site:`` sino el nombre de la empresa en toda la
prensa de los últimos días y se filtran los títulos por tema (TOPIC_RE): así llega
tanto su comunicado como la nota independiente que lo cubre.

Uso independiente (sin LLM, sin costo) para revisar qué traería:

    python3 -m agents.gatherers.regulator_sources --hours 72
"""
from __future__ import annotations

import json
import logging
import math
import re
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Optional

import feedparser
import requests

logger = logging.getLogger(__name__)

GOOGLE_NEWS_SEARCH = "https://news.google.com/rss/search"
GOOGLE_BATCHEXECUTE = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
BROWSER_UA = "Mozilla/5.0 (compatible; Radar-de-Identidad/1.0)"

COUNTRY_NAMES = {
    "MX": "México",
    "ES": "España",
    "CO": "Colombia",
    "AR": "Argentina",
    "CL": "Chile",
    "PE": "Perú",
    "CR": "Costa Rica",
    "GT": "Guatemala",
    "US": "EE. UU.",
    "EU": "Unión Europea",
    "GLOBAL": "Global",
    "LATAM": "Latinoamérica",
}

# Palabras clave en la consulta: reducen lo que Google devuelve a temas del radar.
QUERY_KEYWORDS = (
    '(identidad OR suplantación OR "robo de identidad" OR fraude OR estafa OR phishing '
    'OR autenticación OR contraseña OR biometría OR "firma electrónica" OR ciberseguridad '
    'OR "datos personales" OR "inteligencia artificial" OR credenciales)'
)

# Países y ámbitos que se buscan en inglés (Google News de EE. UU.).
ENGLISH_COUNTRIES = {"US", "EU", "GLOBAL"}

# Consulta en inglés (reguladores de EE. UU. y la UE).
QUERY_KEYWORDS_EN = (
    '(identity OR "identity theft" OR impersonation OR fraud OR scam OR phishing OR '
    'authentication OR password OR biometric OR deepfake OR "account takeover" OR '
    '"data broker" OR "personal data" OR privacy OR "artificial intelligence" OR "AI agent")'
)

# Mismo criterio aplicado a lo que se lee directo de las páginas de prensa y a los
# títulos que devuelve Google News (español e inglés).
TOPIC_RE = re.compile(
    r"identidad|suplant|fraude|estafa|phishing|autentic|contraseñ|biom[eé]tr|firma electr[oó]n|"
    r"ciberseg|ciberataque|hackeo|datos personales|inteligencia artificial|credencial|"
    r"robo de cuenta|verificaci[oó]n|deepfake|criptograf|agentes? de ia|\bIA\b|\bmuse\b|"
    r"reconocimiento facial|passkey|"
    r"identity|impersonat|fraud|scam|authenticat|password|biometric|account takeover|"
    r"data broker|personal data|privacy|artificial intelligence|\bAI\b|cyber|"
    r"agentic|\bai agents?\b|verifiable credential|digital wallet|identity wallet|\beudi\b",
    re.I,
)

SPANISH_MONTHS = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}

# Páginas fijas que Google reindexa y no son noticias.
EVERGREEN_TITLE = re.compile(
    r"^(glosario|formulario|registro|registros|reportar|about|funciones|responsable|"
    r"buscador|preguntas frecuentes|contacto|inicio|leyes|dictámenes|alertas|csirt|"
    r"sala de prensa|noticias|comunicados|transparencia|"
    r"what (?:should|is|are|to do)|get help|how to|key terms|frequently asked|"
    r"credit reports and scores|consumer advice)\b",
    re.I,
)


@dataclass(frozen=True)
class RegulatorSpec:
    country: str
    name: str
    site: str
    page: Optional[str] = None  # página de prensa legible directamente (scraping)
    query: Optional[str] = None  # empresas observadas: búsqueda libre en vez de site:

    @property
    def label(self) -> str:
        return f"{self.name} ({COUNTRY_NAMES.get(self.country, self.country)})"


@dataclass
class RegulatorItem:
    spec: RegulatorSpec
    title: str
    url: str
    published: datetime
    google_link: str


def parse_regulators(lines: Iterable[str]) -> List[RegulatorSpec]:
    """Parse ``PAÍS | Nombre | sitio [| página de prensa]`` lines, ignoring comments."""
    specs = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) not in (3, 4) or not all(parts):
            logger.warning(f"Línea de regulador inválida, se omite: {line!r}")
            continue
        country, name, site = parts[:3]
        page = parts[3] if len(parts) == 4 else None
        site = re.sub(r"^https?://", "", site).strip("/")
        specs.append(RegulatorSpec(country.upper(), name, site, page))
    return specs


def load_regulators(config_dir: str) -> List[RegulatorSpec]:
    path = Path(config_dir) / "regulators.txt"
    if not path.exists():
        return []
    return parse_regulators(path.read_text(encoding="utf-8").splitlines())


def parse_empresas(lines: Iterable[str]) -> List[RegulatorSpec]:
    """Parse ``PAÍS | Nombre | consulta`` lines (empresas observadas), ignoring comments.

    La consulta es texto libre de Google News, p. ej. ``"Coppel" OR "BanCoppel"``.
    """
    specs = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3 or not all(parts):
            logger.warning(f"Línea de empresa inválida, se omite: {line!r}")
            continue
        country, name, query = parts
        specs.append(RegulatorSpec(country.upper(), name, "", None, query))
    return specs


def load_empresas(config_dir: str) -> List[RegulatorSpec]:
    path = Path(config_dir) / "empresas.txt"
    if not path.exists():
        return []
    return parse_empresas(path.read_text(encoding="utf-8").splitlines())


# Agencias de comunicados de prensa: son comunicados de empresas tal cual (política
# agnóstica), no cobertura independiente. Google News las pone tras " - ".
PRESS_WIRE_RE = re.compile(
    r"\s-\s(?:GlobeNewswire|PR Newswire|PRNewswire|Business Wire|BusinessWire|Accesswire|"
    r"ACCESS Newswire|EIN Presswire|Newsfile|PRWeb|Cision|Morningstar)\b[^-]*$",
    re.I,
)


def is_press_wire(title: str) -> bool:
    return bool(PRESS_WIRE_RE.search(title or ""))


def clean_title(title: str) -> str:
    """Drop the ' - Source name' suffix Google News appends."""
    return re.sub(r"\s+-\s+[^-]{2,80}$", "", title or "").strip()


def is_evergreen(title: str, spec: RegulatorSpec) -> bool:
    """True for static pages (forms, glossaries, the site's own name)."""
    t = clean_title(title)
    if len(t) < 15:
        return True
    if EVERGREEN_TITLE.match(t):
        return True
    low = t.lower()
    if low == spec.name.lower() or low.startswith(spec.name.lower() + " |"):
        return True
    return False


def search_url(spec: RegulatorSpec, days: int) -> str:
    english = spec.country in ENGLISH_COUNTRIES
    if spec.query:
        # Sin palabras clave: con ellas Google ordena por relevancia y devuelve notas
        # de hace meses. Solo el nombre y la ventana; el tema lo filtra TOPIC_RE.
        query = f"({spec.query}) when:{max(days, 1)}d"
    else:
        keywords = QUERY_KEYWORDS_EN if english else QUERY_KEYWORDS
        query = f"site:{spec.site} {keywords} when:{max(days, 1)}d"
    locale = "&hl=en-US&gl=US&ceid=US:en" if english else "&hl=es-419&gl=MX&ceid=MX:es-419"
    return f"{GOOGLE_NEWS_SEARCH}?q={urllib.parse.quote(query)}{locale}"


def decode_google_news_url(link: str, session: requests.Session, timeout: int = 20) -> Optional[str]:
    """Resolve a news.google.com/rss/articles/... link to the publisher URL.

    Google no longer redirects these links over HTTP. The article page carries a
    signature and timestamp that the ``batchexecute`` endpoint exchanges for the
    original URL. Returns None if anything in that exchange fails.
    """
    if "news.google.com" not in (link or ""):
        return link or None
    try:
        article_id = urllib.parse.urlparse(link).path.rsplit("/", 1)[-1]
        page = session.get(f"https://news.google.com/rss/articles/{article_id}", timeout=timeout)
        page.raise_for_status()
        sig = re.search(r'data-n-a-sg="([^"]+)"', page.text)
        ts = re.search(r'data-n-a-ts="([^"]+)"', page.text)
        if not (sig and ts):
            return None
        inner = [
            "garturlreq",
            [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None,
              None, None, 0, 1], "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
            article_id,
            int(ts.group(1)),
            sig.group(1),
        ]
        payload = [[["Fbv4je", json.dumps(inner), None, "generic"]]]
        resp = session.post(
            GOOGLE_BATCHEXECUTE,
            data={"f.req": json.dumps(payload)},
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            timeout=timeout,
        )
        resp.raise_for_status()
        body = resp.text.split("\n\n", 1)[1]
        url = json.loads(json.loads(body)[0][2])[1]
        return url if isinstance(url, str) and url.startswith("http") else None
    except Exception as e:  # noqa: BLE001 - any failure means "unresolved"
        logger.debug(f"No se pudo resolver {link[:80]}: {e}")
        return None


def _parse_any_date(text: str) -> Optional[datetime]:
    """Parse ISO-like ('2026-10-19 11:22:00') or Spanish ('19 de octubre de 2026') dates."""
    m = re.search(r"(20\d\d)-(\d\d)-(\d\d)(?:[ T](\d\d):(\d\d))?", text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        h, mi = int(m.group(4) or 12), int(m.group(5) or 0)
        return datetime(y, mo, d, h, mi)
    m = re.search(r"(\d{1,2})\s+de\s+([a-zé]+)\s+de\s+(20\d\d)", text, re.I)
    if m and m.group(2).lower() in SPANISH_MONTHS:
        return datetime(int(m.group(3)), SPANISH_MONTHS[m.group(2).lower()], int(m.group(1)), 12, 0)
    return None


def scrape_press_page(html: str, base_url: str) -> List[dict]:
    """Extract (title, url, published, summary) from a regulator's press listing.

    Works on block-based listings: gob.mx (<article> with <time> and <h2>),
    argentina.gob.ar (panel links with <time> and <h3>) and WordPress themes
    (<article> with .published and h2.entry-title). Unescapes gob.mx's
    JSON-embedded HTML first.
    """
    html = html.replace('\\"', '"').replace("<\\/", "</").replace("\\n", "\n")
    blocks = re.split(r"(?=<article\b)|(?=<a\s[^>]*class=\"panel panel-default\")", html)[1:]
    out = []
    for block in blocks:
        block = block[:6000]
        title_m = re.search(r"<h[23][^>]*>(?:\s*<a[^>]*>)?\s*(.*?)\s*(?:</a>\s*)?</h[23]>", block, re.S)
        # Prefer the link inside the headline; fall back to the block's first link.
        href_m = (re.search(r'href=["\']([^"\']+)["\']', title_m.group(0)) if title_m else None) \
            or re.search(r'href=["\']([^"\']+)["\']', block)
        if not (title_m and href_m):
            continue
        time_m = re.search(r"<time[^>]*datetime=[\"']([^\"']+)[\"']", block)
        published = _parse_any_date(time_m.group(1)) if time_m else _parse_any_date(block)
        if not published:
            continue
        title = re.sub(r"<[^>]+>", "", title_m.group(1))
        title = " ".join(title.split())
        summary_m = re.search(r"<p[^>]*>(.*?)</p>", block[title_m.end():], re.S)
        summary = " ".join(re.sub(r"<[^>]+>", " ", summary_m.group(1)).split())[:400] if summary_m else ""
        url = urllib.parse.urljoin(base_url, href_m.group(1)).split("?idiom=")[0]
        out.append({"title": title, "url": url, "published": published, "summary": summary})
    return out


class SeenCache:
    """Remembers regulator URLs already collected, so re-indexed pages don't repeat."""

    def __init__(self, path: Path, keep_days: int = 120):
        self.path = path
        self.keep_days = keep_days
        try:
            self.data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}

    def seen_before(self, url: str, today: str) -> bool:
        first = self.data.get(url)
        return bool(first and first < today)

    def mark(self, url: str, today: str) -> None:
        self.data.setdefault(url, today)

    def save(self, today: str) -> None:
        cutoff = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=self.keep_days)).strftime("%Y-%m-%d")
        self.data = {u: d for u, d in self.data.items() if d >= cutoff}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=0, sort_keys=True), encoding="utf-8")
        except OSError as e:
            logger.warning(f"No se pudo guardar la caché de reguladores: {e}")


def collect(
    specs: List[RegulatorSpec],
    start: datetime,
    end: datetime,
    session: Optional[requests.Session] = None,
    seen: Optional[SeenCache] = None,
    today: Optional[str] = None,
    on_spec: Optional[Callable[[RegulatorSpec, int], None]] = None,
    pause: float = 0.3,
    max_per_spec: Optional[int] = None,
) -> List[RegulatorItem]:
    """Collect regulator items published in [start, end] (naive UTC datetimes).

    ``max_per_spec`` limita las notas por fuente (empresas observadas: una campaña
    como el Buen Fin no debe inundar el triage).
    """
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", BROWSER_UA)
    today = today or end.strftime("%Y-%m-%d")
    days = math.ceil((end - start).total_seconds() / 86400) + 1
    items: List[RegulatorItem] = []
    seen_urls = set()

    for spec in specs:
        found = 0
        if spec.page:
            try:
                resp = session.get(spec.page, timeout=30)
                resp.raise_for_status()
                rows = scrape_press_page(resp.text, spec.page)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Reguladores: falló la página de prensa de {spec.label}: {e}")
                rows = []
            if not rows:
                logger.warning(f"Reguladores: la página de {spec.label} no devolvió notas (¿cambió el sitio?)")
            for row in rows:
                if not (start.date() <= row["published"].date() <= end.date()):
                    continue
                if not TOPIC_RE.search(row["title"] + " " + row["summary"]):
                    continue
                url = row["url"]
                if url in seen_urls or (seen and seen.seen_before(url, today)):
                    continue
                seen_urls.add(url)
                if seen:
                    seen.mark(url, today)
                items.append(RegulatorItem(spec, row["title"], url, row["published"], ""))
                found += 1
            if on_spec:
                on_spec(spec, found)
            time.sleep(pause)
            continue

        try:
            resp = session.get(search_url(spec, days), timeout=30)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Reguladores: falló la búsqueda de {spec.label}: {e}")
            if on_spec:
                on_spec(spec, 0)
            continue

        for entry in feed.entries:
            if max_per_spec is not None and found >= max_per_spec:
                break
            when = entry.get("published_parsed") or entry.get("updated_parsed")
            if not when:
                continue
            published = datetime(*when[:6])
            if not (start <= published <= end):
                continue
            title = entry.get("title", "")
            if is_evergreen(title, spec) or is_press_wire(title) or not TOPIC_RE.search(clean_title(title)):
                continue
            url = decode_google_news_url(entry.get("link", ""), session)
            time.sleep(pause)
            if not url:
                logger.info(f"Reguladores: sin enlace original, se omite: {clean_title(title)[:80]}")
                continue
            if url in seen_urls or (seen and seen.seen_before(url, today)):
                continue
            seen_urls.add(url)
            if seen:
                seen.mark(url, today)
            items.append(RegulatorItem(spec, clean_title(title), url, published, entry.get("link", "")))
            found += 1

        if on_spec:
            on_spec(spec, found)
        time.sleep(pause)

    return items


def _main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Muestra lo que traería el recolector de reguladores.")
    ap.add_argument("--hours", type=int, default=72, help="ventana hacia atrás (default 72)")
    ap.add_argument("--config-dir", default=str(Path(__file__).resolve().parents[2] / "config"))
    ap.add_argument("--empresas", action="store_true", help="revisa las empresas observadas en vez de los reguladores")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)

    end = datetime.now(timezone.utc).replace(tzinfo=None)
    start = end - timedelta(hours=args.hours)
    specs = load_empresas(args.config_dir) if args.empresas else load_regulators(args.config_dir)
    counts = {}
    items = collect(specs, start, end, on_spec=lambda s, n: counts.__setitem__(s.label, n),
                    max_per_spec=4 if args.empresas else None)
    for spec in specs:
        print(f"{counts.get(spec.label, 0):>3}  {spec.label}")
    print(f"\n{len(items)} notas en las últimas {args.hours} horas:\n")
    for it in sorted(items, key=lambda i: i.published, reverse=True):
        print(f"- [{it.spec.label}] {it.title}\n  {it.url}")


if __name__ == "__main__":
    _main()
