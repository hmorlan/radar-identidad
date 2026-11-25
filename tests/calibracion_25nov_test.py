"""25 nov: lo que corrigió la edición a mano pasa a código (verificación e Instinct)."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.continuity.coordinator import seguimiento_text
from agents.gatherers.regulator_sources import (RegulatorSpec, names_subject, other_country_domain,
                                                query_terms)
from generators.json_generator import JSONGenerator
from generators.source_names import display_source
from generators.themes import merge_themes

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FuenteVisibleTest(unittest.TestCase):
    def test_nombres_crudos(self):
        casos = {
            ("Lo último", "https://www.eleconomista.com.mx/sectorfinanciero/x"): "El Economista",
            ("Page 2 – Biometric Update", "https://www.biometricupdate.com/x"): "Biometric Update",
            ("www.theregister.com - Articles", "https://www.theregister.com/x"): "The Register",
            ("infosecurity-magazine.com", "https://www.infosecurity-magazine.com/x"): "Infosecurity Magazine",
            ("correctiv.org", "https://correctiv.org/x"): "CORRECTIV",
            ("BleepingComputer", "https://www.bleepingcomputer.com/x"): "BleepingComputer",
        }
        for (name, url), esperado in casos.items():
            self.assertEqual(display_source(name, url), esperado, name)


class GoogleNewsTest(unittest.TestCase):
    def test_teletica_no_queda_atribuida_al_bcr(self):
        bcr = RegulatorSpec("CR", "Banco de Costa Rica (BCR)", "", query='"Banco de Costa Rica" OR "SINPE Móvil"')
        self.assertEqual(query_terms(bcr.query), ["Banco de Costa Rica", "SINPE Móvil"])
        self.assertFalse(names_subject(
            "Empresa investigada por presunta filtración de datos en 'dark web' niega extracción masiva", bcr))
        self.assertTrue(names_subject("El Banco de Costa Rica refuerza la verificación en SINPE", bcr))

    def test_notas_dominicanas_fuera_de_la_busqueda_de_mexico(self):
        self.assertTrue(other_country_domain("https://policianacional.gob.do/detienen", "MX"))
        self.assertTrue(other_country_domain("https://elnuevodiario.com.do/x", "MX"))
        self.assertFalse(other_country_domain("https://www.abcnoticias.mx/x", "MX"))
        self.assertFalse(other_country_domain("https://www.reuters.com/x", "MX"))
        self.assertFalse(other_country_domain("https://policianacional.gob.do/x", "GLOBAL"))


class SeguimientoTest(unittest.TestCase):
    def test_en_espanol_y_con_fecha_real(self):
        t = seguimiento_text("2026-11-23", "social", "c16d7d501a7b")
        self.assertEqual(t, "Seguimiento de [Redes](/?date=2026-11-23&category=social#item-c16d7d501a7b) "
                            "del 23 de noviembre:")
        self.assertNotIn("yesterday", t)
        self.assertEqual(seguimiento_text("", "news", "x"), "")


class TemasTest(unittest.TestCase):
    def test_funde_casi_iguales_y_quita_los_de_una_nota(self):
        temas = [{"name": "Phishing y toma de cuentas", "item_count": 1, "importance": 92},
                 {"name": "Robo de credenciales y SSO", "item_count": 5},
                 {"name": "Robo de credenciales y secretos", "item_count": 9},
                 {"name": "Agentes de IA con accesos delegados", "item_count": 10},
                 {"name": "Agentes de IA con acceso delegado", "item_count": 7},
                 {"name": "Herramientas de hacking con IA", "item_count": 5}]
        out = merge_themes(temas)
        self.assertEqual([(t["name"], t["item_count"]) for t in out],
                         [("Agentes de IA con accesos delegados", 17), ("Robo de credenciales y secretos", 14),
                          ("Herramientas de hacking con IA", 5)])


class GeneradorTest(unittest.TestCase):
    def test_autor_unknown_y_tambien_en_limpios(self):
        item = {"id": "a1", "title": "t", "url": "https://www.eleconomista.com.mx/x", "source": "Lo último",
                "author": "Unknown", "summary": "s", "importance_score": 70, "themes": [],
                "metadata": {"tambien_en": [
                    {"source": "www.theregister.com - Articles", "url": "https://www.theregister.com/a", "title": "x"},
                    {"source": "www.theregister.com - Articles", "url": "https://www.theregister.com/b", "title": "y"},
                    {"source": "infosecurity-magazine.com", "url": "https://www.infosecurity-magazine.com/c", "title": "z"}]}}
        out = JSONGenerator(output_dir=tempfile.mkdtemp())._simplify_items([item])[0]
        self.assertEqual(out["source"], "El Economista")
        self.assertEqual(out["author"], "")
        self.assertEqual([a["source"] for a in out["tambien_en"]], ["The Register", "Infosecurity Magazine"])


class RevisionMecanicaTest(unittest.TestCase):
    def test_encuentra_lo_que_corrigio_el_parche_del_25(self):
        lint = _load("lint_edicion")
        summary = {"executive_summary": "## Regulación y Latinoamérica\n- **CORRECTIV** publicó algo en Alemania.",
                   "edition": {"notas": [{"item_id": "r1", "title": "Reniec habilita el DNI digital en PerúPass",
                                          "url": "https://gestion.pe/x", "source": "Lo último",
                                          "que_paso": "Reniec…"}]}}
        news = {"items": [{"id": "n1", "source": "Page 2 – Biometric Update", "author": "Unknown",
                           "summary": "Also flagged in yesterday's Social roundup, Alemania…"},
                          {"id": "n2", "source": "PYMNTS.com", "author": "",
                           "summary": "La etiqueta del origen atribuye la nota a un banco."}]}
        with tempfile.TemporaryDirectory() as d:
            day = Path(d)
            (day / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            (day / "news.json").write_text(json.dumps(news), encoding="utf-8")
            tipos = sorted({f["tipo"] for f in lint.lint(day)})
        self.assertEqual(tipos, ["autor_generico", "comentario_interno", "fuente_cruda", "ingles",
                                 "latam_fuera_del_resumen", "seccion_latam_vacia"])


class CorreccionesVisiblesTest(unittest.TestCase):
    def test_la_reparacion_registra_notas_y_aviso(self):
        repair = _load("repair_edition")
        summary = {"executive_summary": "Resumen viejo.", "edition": {"titular": "t", "notas": [
            {"item_id": "a1", "title": "t", "que_paso": "dato malo", "por_que_importa": "p", "senal": "media"},
            {"item_id": "b2", "title": "u", "que_paso": "bien", "por_que_importa": "p", "senal": "media"}]}}
        with tempfile.TemporaryDirectory() as d:
            day = Path(d)
            (day / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            repair.apply_patch({"motivo": "interno", "notas": {"a1": {"que_paso": "dato bueno"}}}, day)
            reg = json.loads((day / "summary.json").read_text(encoding="utf-8"))["reparaciones"][-1]
        self.assertEqual(reg["notas_corregidas"], ["a1"])
        self.assertFalse(reg["resumen_corregido"])
        self.assertIn("1 nota", reg["aviso"])


class RedditApagadoTest(unittest.TestCase):
    def test_no_se_intenta_sin_bandera(self):
        from agents import orchestrator
        with patch.dict(os.environ, {"REDDIT_ENABLED": "", "REDDIT_REQUIRED": ""}):
            self.assertFalse(orchestrator._reddit_enabled())
        with patch.dict(os.environ, {"REDDIT_ENABLED": "1"}):
            self.assertTrue(orchestrator._reddit_enabled())


if __name__ == "__main__":
    unittest.main()
