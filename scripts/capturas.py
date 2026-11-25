#!/usr/bin/env python3
"""Capturas del sitio compilado, para la revisión editorial (sin costo).

El sitio publicado está detrás de Cloudflare Access; el revisor (Fable) ve la
edición con estas capturas, que salen del mismo build que se sube a Pages.
Levanta ``web/`` en un servidor local (con el respaldo SPA de adapter-static:
``index.html``) y toma capturas de página completa de la portada (con todas las
notas abiertas), cada categoría y el archivo, en escritorio y móvil, claro y oscuro.

Uso:
    python3 scripts/capturas.py --web-dir web --date 2026-11-23 --out capturas
Requiere: pip install playwright && python3 -m playwright install --with-deps chromium
"""
from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

VISTAS = {
    "escritorio": {"viewport": {"width": 1440, "height": 900}},
    "movil": {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2,
              "is_mobile": True, "has_touch": True},
}
TEMAS = ("light", "dark")


def paginas(date: str) -> dict[str, str]:
    return {
        "portada": f"/?date={date}",
        "noticias": f"/?date={date}&category=news",
        "investigacion": f"/?date={date}&category=research",
        "redes": f"/?date={date}&category=social",
        "archivo": "/archive",
    }


class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # silencio
        pass

    def send_head(self):
        path = Path(self.translate_path(self.path))
        if not path.exists():
            self.path = "/index.html"
        return super().send_head()


def serve(web_dir: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(SPAHandler, directory=str(web_dir))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def abrir_notas(page) -> int:
    """Abre las notas colapsadas ("Leer nota →") para que salgan completas."""
    botones = page.locator("button.leer")
    n = botones.count()
    for i in range(n):
        try:
            botones.nth(0).click(timeout=2000)   # al abrirse, el botón desaparece
        except Exception:  # noqa: BLE001
            break
    return n


def max_tramos(nombre: str, tema: str) -> int:
    """La portada en claro se captura completa (es lo que se revisa a fondo); lo
    demás, sus dos primeros tramos: basta para ver diseño, modo oscuro y móvil sin
    mandar 200 imágenes al revisor."""
    return 99 if (nombre == "portada" and tema == "light") else 2


def capturar(page, base: Path, viewport: dict, limite: int = 99) -> int:
    """Página completa en tramos de ~2 pantallas (una captura de 19,000 px de alto
    se vuelve ilegible al reducirla para revisarla)."""
    alto = page.evaluate("document.documentElement.scrollHeight")
    paso = viewport["height"] * 2
    n = 0
    for i, y in enumerate(range(0, alto, paso), start=1):
        if i > limite:
            break
        page.screenshot(path=f"{base}-{i:02d}.png", full_page=True,
                        clip={"x": 0, "y": y, "width": viewport["width"],
                              "height": min(paso, alto - y)})
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--web-dir", default="web")
    ap.add_argument("--date", required=True)
    ap.add_argument("--out", default="capturas")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    web_dir, out = Path(args.web_dir), Path(args.out)
    if not (web_dir / "index.html").exists():
        print(f"No hay sitio compilado en {web_dir} (falta index.html).", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    httpd, port = serve(web_dir)
    hechas, errores = 0, []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for vista, opts in VISTAS.items():
                for tema in TEMAS:
                    ctx = browser.new_context(color_scheme=tema, locale="es-MX", **opts)
                    page = ctx.new_page()
                    for nombre, ruta in paginas(args.date).items():
                        try:
                            page.goto(f"http://127.0.0.1:{port}{ruta}", wait_until="networkidle",
                                      timeout=30000)
                            if nombre == "portada":
                                abrir_notas(page)
                            # 25 nov: el menú es position: sticky; tras abrir las notas
                            # la página queda desplazada y el menú se pintaba fuera del
                            # recorte (en la portada móvil no aparecía). Arriba y quieto.
                            page.add_style_tag(content="nav.menu{position:static !important;top:auto !important}")
                            page.evaluate("window.scrollTo(0, 0)")
                            page.wait_for_timeout(600)
                            hechas += capturar(page, out / f"{nombre}-{vista}-{tema}",
                                               opts["viewport"], max_tramos(nombre, tema))
                        except Exception as e:  # noqa: BLE001
                            errores.append(f"{nombre}-{vista}-{tema}: {type(e).__name__}: {e}")
                    ctx.close()
            browser.close()
    finally:
        httpd.shutdown()
    print(f"{hechas} capturas en {out} (tramos de 2 pantallas)")
    for e in errores:
        print("FALLA", e)
    return 0 if hechas else 1


if __name__ == "__main__":
    sys.exit(main())
