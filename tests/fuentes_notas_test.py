"""24 nov: texto completo de las fuentes para la revisión (artefacto `fuentes`)."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("fuentes_notas", ROOT / "scripts" / "fuentes_notas.py")
fn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fn)

SUMMARY = {"edition": {"notas": [
    {"item_id": "a1", "title": "Entra Connect Health", "url": "https://www.bleepingcomputer.com/news/x/"},
    {"item_id": "b2", "title": "Muse", "url": "https://www.404media.co/muse/",
     "via": {"source": "Bluesky (404 Media)", "url": "https://bsky.app/profile/404media.co/post/1"}},
    {"item_id": "c3", "title": "sin url", "url": "javascript:alert(1)"},
    {"item_id": "d4", "title": "onion", "url": "http://abcdefgh.onion/leak"},
]}}

ARTICULO = "<p>" + "Microsoft confirmó la falla en Entra Connect Health. " * 40 + "</p>"
HTML = f"""<html><head><title>Falla en Entra</title>
<meta property="article:published_time" content="2026-11-21T18:01:58+00:00"></head>
<body><nav>menú</nav><article>{ARTICULO}</article><footer>pie</footer></body></html>"""


class _Resp:
    def __init__(self, status=200, text=HTML, ctype="text/html; charset=utf-8", url=None):
        self.status_code, self.content = status, text.encode()
        self.headers = {"content-type": ctype}
        self.url = url or "https://www.bleepingcomputer.com/news/x/"


class _Session:
    def __init__(self, respuestas):
        self.respuestas = respuestas

    def get(self, url, **kw):
        r = self.respuestas.get(url)
        if isinstance(r, Exception):
            raise r
        return r or _Resp(status=404)


class FuentesNotasTest(unittest.TestCase):
    def test_enlaces_fuente_y_via_sin_onion_ni_esquemas_raros(self):
        links = fn.links_de_la_edicion(SUMMARY)
        self.assertEqual([(l["item_id"], l["papel"]) for l in links],
                         [("a1", "fuente"), ("b2", "fuente"), ("b2", "via")])

    def test_texto_y_fecha_del_articulo(self):
        soup = BeautifulSoup(HTML, "html.parser")
        self.assertEqual(fn.published_date(soup), "2026-11-21")
        texto = fn.texto_principal(soup)
        self.assertIn("Entra Connect Health", texto)
        self.assertNotIn("menú", texto)
        self.assertGreater(len(texto), 1000)

    def test_main_escribe_registro_y_textos(self):
        session = _Session({
            "https://www.bleepingcomputer.com/news/x/": _Resp(),
            "https://www.404media.co/muse/": _Resp(status=403),
            "https://bsky.app/profile/404media.co/post/1": ConnectionError("sin red"),
        })
        with tempfile.TemporaryDirectory() as d:
            web = Path(d) / "web" / "data" / "2026-11-23"
            web.mkdir(parents=True)
            (web / "summary.json").write_text(json.dumps(SUMMARY), encoding="utf-8")
            out = Path(d) / "fuentes"
            with patch("requests.Session", return_value=session), patch.object(fn.time, "sleep"), \
                 patch("sys.argv", ["x", "--web-dir", str(Path(d) / "web"), "--date", "2026-11-23", "--out", str(out)]):
                self.assertEqual(fn.main(), 0)
            reg = json.loads((out / "fuentes.json").read_text(encoding="utf-8"))
            self.assertEqual((reg["total"], reg["con_texto_completo"]), (3, 1))
            e = {(x["item_id"], x["papel"]): x for x in reg["enlaces"]}
            self.assertEqual(e[("a1", "fuente")]["fecha_declarada"], "2026-11-21")
            self.assertTrue((out / e[("a1", "fuente")]["archivo"]).exists())
            self.assertEqual(e[("b2", "fuente")]["error"], "HTTP 403")
            self.assertIn("sin texto completo", e[("b2", "via")]["aviso"])


if __name__ == "__main__":
    unittest.main()
