"""Tests de scripts/repair_edition.py (sin red)."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import repair_edition as re_


def _day(tmp: Path) -> Path:
    d = tmp / "data" / "2026-11-17"
    d.mkdir(parents=True)
    summary = {
        "executive_summary": "El FBI [alerta](/?date=x#a) y deepfakes que superan verificaciones.",
        "executive_summary_html": "<p>viejo</p>",
        "top_topics": [{"name": "Deepfakes que burlan", "description": "Deepfakes que superan verificaciones [x](/?date=x#b).",
                        "description_html": "viejo"}],
        "edition": {"titular": "T", "notas": [{"item_id": "n1", "que_paso": "No detalla.", "senal": "media"}]},
    }
    news = {"category_summary": "y deepfakes que superan verificaciones.", "category_summary_html": "<p>viejo</p>",
            "items": [{"id": "n1", "reasoning": "deepfakes que superan verificaciones"}]}
    (d / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (d / "news.json").write_text(json.dumps(news), encoding="utf-8")
    return d


PATCH = {
    "date": "2026-11-17", "motivo": "prueba",
    "reemplazos": [{"antes": "que superan verificaciones", "despues": "contra verificaciones"},
                   {"antes": "Deepfakes que burlan", "despues": "Deepfakes contra"}],
    "notas": {"n1": {"que_paso": "Sí detalla.", "verificacion": "corregida"}},
}


class RepairEditionTest(unittest.TestCase):
    def test_applies_everywhere_rerenders_html_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            d = _day(Path(t))
            rep = re_.apply_patch(PATCH, d)
            s = json.loads((d / "summary.json").read_text())
            n = json.loads((d / "news.json").read_text())
            self.assertNotIn("superan", json.dumps(s) + json.dumps(n))
            self.assertIn("contra verificaciones", s["executive_summary_html"])
            self.assertIn('href="/?date=x#a"', s["executive_summary_html"].replace("&amp;", "&"))
            self.assertIn('<a href="/?date=x#b"', s["top_topics"][0]["description_html"])
            self.assertEqual(s["top_topics"][0]["name"], "Deepfakes contra")
            self.assertEqual(s["edition"]["notas"][0]["que_paso"], "Sí detalla.")
            self.assertEqual(len(s["reparaciones"]), 1)
            self.assertGreaterEqual(rep["html"], 3)
            again = re_.apply_patch(PATCH, d)
            self.assertTrue(again.get("sin_cambios"))
            self.assertEqual(len(json.loads((d / "summary.json").read_text())["reparaciones"]), 1)

    def test_multiline_replacement_is_idempotent(self):
        # 25 nov: un "despues" con salto de línea (una viñeta nueva) hacía fallar
        # la segunda aplicación porque se buscaba en json.dumps.
        patch = {"date": "2026-11-17", "motivo": "prueba",
                 "reemplazos": [{"antes": "El FBI [alerta](/?date=x#a)",
                                 "despues": "Nueva viñeta.\n- El FBI [avisa](/?date=x#a)",
                                 "archivos": ["summary.json"]}]}
        with tempfile.TemporaryDirectory() as t:
            d = _day(Path(t))
            re_.apply_patch(patch, d)
            again = re_.apply_patch(patch, d)
            self.assertTrue(again.get("sin_cambios"))
            s = json.loads((d / "summary.json").read_text())
            self.assertEqual(s["executive_summary"].count("Nueva viñeta."), 1)

    def test_real_patches_never_contain_their_own_antes(self):
        for path in sorted(Path("config/reparaciones").glob("*.json")):
            patch = json.loads(path.read_text(encoding="utf-8"))
            for r in patch.get("reemplazos") or []:
                self.assertNotIn(r["antes"], r["despues"], f"{path.name}: {r['antes'][:60]}")
                self.assertTrue(set(r) <= {"antes", "despues", "archivos"}, path.name)
            for fields in (patch.get("notas") or {}).values():
                self.assertTrue(set(fields) <= set(re_.NOTE_FIELDS), path.name)

    def test_unknown_text_or_note_cancels_without_writing(self):
        with tempfile.TemporaryDirectory() as t:
            d = _day(Path(t))
            before = (d / "summary.json").read_text()
            with self.assertRaises(re_.RepairError):
                re_.apply_patch({**PATCH, "reemplazos": [{"antes": "no existe", "despues": "x"}]}, d)
            with self.assertRaises(re_.RepairError):
                re_.apply_patch({**PATCH, "reemplazos": [], "notas": {"zz": {"que_paso": "x"}}}, d)
            self.assertEqual((d / "summary.json").read_text(), before)

    def test_real_patch_file_is_well_formed(self):
        patch = json.loads(Path("config/reparaciones/2026-11-17.json").read_text(encoding="utf-8"))
        self.assertEqual(patch["date"], "2026-11-17")
        for r in patch["reemplazos"]:
            self.assertTrue(r["antes"] and r["despues"] and r["antes"] != r["despues"])
        for fields in patch["notas"].values():
            self.assertTrue(set(fields) <= set(re_.NOTE_FIELDS))


if __name__ == "__main__":
    unittest.main()
