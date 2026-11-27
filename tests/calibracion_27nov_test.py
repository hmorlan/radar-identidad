"""27 nov: lo que la verificación corrigió a mano pasa a código."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from agents.analyzers.social_analyzer import publishable_social
from agents.base import AnalyzedItem, CategoryTheme, CollectedItem, ContinuationInfo
from agents.edition_notes import linked_entries
from agents.gatherers.identity_filter import is_identity_vendor
from generators.json_generator import JSONGenerator
from generators.region import ensure_latam_in_summary, is_latam
from generators.source_names import clean_author, display_source, strip_title_suffix


def _ai(iid, title, score, themes, content="x"):
    it = CollectedItem(id=iid, title=title, content=content, url=f"https://e.com/{iid}", author="a",
                       published="2026-11-26T10:00:00", source="Medio", source_type="rss")
    return AnalyzedItem(item=it, summary="s", importance_score=score, reasoning="r", themes=themes)


class RedesAntesDelRankingTest(unittest.TestCase):
    def test_corta_y_recalcula_temas(self):
        items = [_ai("a", "1Password said it was breached via GitHub", 68, ["Brechas de credenciales"]),
                 _ai("b", "EFF thanks our co-counsel for the lawsuit", 32, ["Vigilancia y libertades digitales"]),
                 _ai("c", "Scientists equipped birds with audio recorders", 10, ["Ajeno al radar"])]
        themes = [CategoryTheme("Brechas de credenciales", "d", 1, [], 70),
                  CategoryTheme("Vigilancia y libertades digitales", "d", 7, [], 60),
                  CategoryTheme("Ajeno al radar", "d", 1, [], 5)]
        kept, t = publishable_social(items, themes)
        self.assertEqual([k.item.id for k in kept], ["a"])
        self.assertEqual([(x.name, x.item_count) for x in t], [("Brechas de credenciales", 1)])


class EnlacesRotosTest(unittest.TestCase):
    def test_desenlaza_entradas_no_publicadas(self):
        gen = JSONGenerator(output_dir=tempfile.mkdtemp())
        gen._unlinked = 0
        known = {"social": {"edef9f0c5e93"}, "news": {"n1"}}
        text = ("La [EFF reivindica](/?date=2026-11-27&category=social#item-2aa685ed5a09) y "
                "[1Password](/?date=2026-11-27&category=social#item-edef9f0c5e93); "
                "[ayer](/?date=2026-11-25&category=news#item-zz).")
        out = gen._unlink_missing(text, "2026-11-27", known)
        self.assertIn("La EFF reivindica y", out)
        self.assertIn("[1Password](/?date=2026-11-27&category=social#item-edef9f0c5e93)", out)
        self.assertIn("[ayer](/?date=2026-11-25&category=news#item-zz)", out)
        self.assertEqual(gen._unlinked, 1)


class VerificacionDelResumenTest(unittest.TestCase):
    def test_entradas_enlazadas_con_aviso_y_seguimiento(self):
        spice = _ai("a6262a84569b", "draft-ietf-spice-sd-cwt-05", 37, [],
                    content="New version available: draft-ietf-spice-sd-cwt-05.txt")
        spice.continuation = ContinuationInfo("x", "2026-11-25", "research", "t", "rehash", True, "")
        otro = _ai("b1c2d3e4f5a6", "1Password breach", 85, [], content="The attacker also copied source code. " * 10)
        derived = {"executive_summary": "SPICE [avanza](/?date=2026-11-27&category=research#item-a6262a84569b) y "
                                        "[1Password](/?date=2026-11-27&category=news#item-b1c2d3e4f5a6)."}
        out = linked_entries(derived, {"a6262a84569b": ("research", spice), "b1c2d3e4f5a6": ("news", otro)})
        self.assertEqual([e["id"] for e in out], ["a6262a84569b", "b1c2d3e4f5a6"])
        self.assertTrue(out[0]["solo_aviso"])
        self.assertEqual(out[0]["seguimiento"], {"tipo": "rehash", "fecha_original": "2026-11-25"})
        self.assertFalse(out[1]["solo_aviso"])
        self.assertIn("copied source code", out[1]["texto"])


class RegionTest(unittest.TestCase):
    def test_agrega_la_nota_que_falta_sin_tocar_las_que_estan(self):
        notas = [{"item_id": "i1", "title": "Indecopi multa a Compartamos", "url": "https://gestion.pe/x",
                  "source": "Diario Gestión", "category": "news"},
                 {"item_id": "t1", "title": "trii conecta ChatGPT por MCP", "url": "https://bloomberglinea.com/x",
                  "source": "Bloomberg Línea", "category": "news", "que_paso": "En Colombia, Chile y Perú…"},
                 {"item_id": "x1", "title": "1Password", "url": "https://thehackernews.com/x",
                  "source": "The Hacker News", "category": "news", "que_paso": "GitHub"}]
        self.assertEqual([is_latam(n) for n in notas], [True, True, False])
        resumen = ("#### Lo principal\nAlgo.\n\n#### Regulación y Latinoamérica\n"
                   "- [Indecopi](/?date=2026-11-27&category=news#item-i1).\n\n#### Investigación\n- Otra.\n")
        out = ensure_latam_in_summary(resumen, notas, "2026-11-27")
        self.assertIn("#item-t1", out)
        self.assertLess(out.index("#item-t1"), out.index("#### Investigación"))
        self.assertEqual(out.count("#item-i1"), 1)
        self.assertEqual(ensure_latam_in_summary(out, notas, "2026-11-27"), out)


class ProveedoresTest(unittest.TestCase):
    def test_politica_b(self):
        self.assertTrue(is_identity_vendor("https://www.osd.at/news/youniqx"))
        self.assertTrue(is_identity_vendor("https://www.biometricupdate.com/x", "Persona"))
        self.assertFalse(is_identity_vendor("https://www.biometricupdate.com/x", "Chris Burt"))
        self.assertFalse(is_identity_vendor("https://blog.talosintelligence.com/the-great-escape/"))
        self.assertFalse(is_identity_vendor("https://www.theregister.com/x"))


class MecanicosTest(unittest.TestCase):
    def test_autor_titulo_y_fuente(self):
        self.assertEqual(clean_author("info@thehackernews.com (The Hacker News)", "The Hacker News"), "")
        self.assertEqual(clean_author("Newsletter"), "")
        self.assertEqual(clean_author("@zackwhittaker.com"), "@zackwhittaker.com")
        self.assertEqual(clean_author("Chris Burt"), "Chris Burt")
        self.assertEqual(strip_title_suffix("Nueva estafa de Coppel - E-Tlaxcala", "E-Tlaxcala"), "Nueva estafa de Coppel")
        self.assertEqual(strip_title_suffix("youniqx entrega componentes • OSD", "x"), "youniqx entrega componentes")
        self.assertEqual(strip_title_suffix("Policía Cibernética alerta (16:00 h)", "x"), "Policía Cibernética alerta")
        self.assertEqual(strip_title_suffix("Phishing - What to know", "BleepingComputer"), "Phishing - What to know")
        self.assertEqual(display_source("El Piñero, Periodismo y Debate.", "https://elpinero.mx/x"), "El Piñero")
        self.assertEqual(display_source("Meganoticias.mx", "https://www.meganoticias.mx/x"), "Meganoticias")


if __name__ == "__main__":
    unittest.main()
