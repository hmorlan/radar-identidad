"""23 nov (revisión de Instinct, P1): Redes no publica lo ajeno al radar."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from generators import social_filter
from generators.json_generator import JSONGenerator


def _it(i, title, score, themes):
    return {"id": f"s{i}", "title": title, "url": f"https://bsky.app/p/{i}", "source": "Bluesky",
            "importance_score": score, "themes": themes, "summary": "x", "content": "x"}


ITEMS = [
    _it(1, "Lo bloquearon de su página de Facebook tras dar acceso a su agente", 72, ["agentes de IA"]),
    _it(2, "Científicos descubrieron que las águilas cazan babuinos adultos", 2, ["ciencia ajena al radar"]),
    _it(3, "Esta semana hablamos de fisiología de hipopótamos", 25, ["Ajeno al radar"]),
    _it(4, "papoi\nwww.404media.co/scientists-m...", 55, ["neurociencia"]),
    _it(5, "📢 ¡Las solicitudes cierran pronto! #ApplyNow", 1, ["anuncio"]),
    _it(6, "Lee nuestro balance de la sesión legislativa sobre verificación de edad", 38, ["verificación de edad"]),
]


class SocialFilterTest(unittest.TestCase):
    def test_motivos(self):
        r = {it["id"]: social_filter.reason_to_drop(it, 20) for it in ITEMS}
        self.assertEqual(r, {"s1": "", "s2": "ajeno", "s3": "ajeno", "s4": "sin_texto",
                             "s5": "puntaje", "s6": ""})

    def test_umbral_configurable(self):
        with patch.dict(os.environ, {"SOCIAL_MIN_SCORE": "40"}):
            self.assertEqual([i["id"] for i in social_filter.publishable(ITEMS)], ["s1"])

    def test_temas_ajenos_fuera(self):
        themes = [{"name": "Agentes de IA"}, {"name": "Contenido ajeno al radar", "item_count": 12}]
        self.assertEqual(social_filter.publishable_themes(themes), [{"name": "Agentes de IA"}])


class JsonRedesTest(unittest.TestCase):
    def test_social_json_y_summary_sin_ajenos_y_noticias_intactas(self):
        report = {"all_items": ITEMS, "top_items": ITEMS[:3], "themes": [{"name": "Ajeno al radar"}],
                  "category_summary": ""}
        news = {"all_items": [_it(9, "Águilas ajenas pero en Noticias", 2, ["ciencia ajena al radar"])],
                "top_items": [], "themes": [], "category_summary": ""}
        result = {"date": "2026-11-23", "category_reports": {"social": report, "news": news},
                  "edition": {"titular": "t", "notas": [{
                      "item_id": "s1", "category": "social", "title": "t", "url": "https://404media.co/a",
                      "source": "404 Media", "published": "2026-11-17", "que_paso": "q", "por_que_importa": "p",
                      "senal": "media", "verificacion": "verificada", "fecha_tipo": "publicacion",
                      "via": {"source": "Bluesky (404 Media)", "url": "https://bsky.app/p/1",
                              "published": "2026-11-22T23:30:00"}}]}}
        with tempfile.TemporaryDirectory() as d:
            gen = JSONGenerator(output_dir=d)
            day = os.path.join(d, "2026-11-23"); os.makedirs(day)
            gen._generate_category_files(day, result)
            gen._generate_summary_json(day, result)
            social = json.load(open(os.path.join(day, "social.json")))
            self.assertEqual([i["id"] for i in social["items"]], ["s1", "s6"])
            self.assertEqual(social["themes"], [])
            self.assertEqual(len(json.load(open(os.path.join(day, "news.json")))["items"]), 1)
            summary = json.load(open(os.path.join(day, "summary.json")))
            self.assertEqual(summary["categories"]["social"]["count"], 2)
            nota = summary["edition"]["notas"][0]
            self.assertEqual(nota["via"]["source"], "Bluesky (404 Media)")
            self.assertEqual(nota["fecha_tipo"], "publicacion")


if __name__ == "__main__":
    unittest.main()
