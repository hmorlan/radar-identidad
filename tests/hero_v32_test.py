"""Tests de la imagen v3.2: ejes, memoria, candidatas, respaldo y postproceso (sin red)."""
import asyncio
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

from generators import hero_postprocess as hp
from generators import hero_v32 as hv


def jpeg(gold_fraction=0.03, blue=False, size=(840, 360)):
    """Imagen sintética: fondo marfil, líneas grafito y una franja de oro."""
    w, h = size
    a = np.full((h, w, 3), [222, 214, 198], dtype=np.uint8)
    a[::12, :, :] = [70, 72, 76]
    cols = int(w * gold_fraction)
    if cols:
        a[:, :cols] = [212, 160, 40]
    if blue:
        a[: h // 4, w - 60:] = [30, 90, 255]
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, "JPEG", quality=95)
    return buf.getvalue()


class Resp:
    def __init__(self, data, batch=False):
        self.image_data = data
        self.usage = {"prompt_tokens": 600, "completion_tokens": 1120,
                      "completion_tokens_details": {"image_tokens": 1120}, "batch": batch}
        self.model = "gemini-3-pro-image"


class FakeClient:
    model = "gemini-3-pro-image"

    def __init__(self, batch_images, direct_images):
        self.batch_images = list(batch_images)
        self.direct_images = list(direct_images)
        self.prompts = []

    async def generate_batch(self, prompts, reference_images=None, max_wait_seconds=0):
        self.prompts.extend(prompts)
        return [Resp(d, batch=True) for d in self.batch_images]

    async def generate(self, prompt, reference_images=None, **_):
        self.prompts.append(prompt)
        return Resp(self.direct_images.pop(0))


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


class AxesAndMemoryTest(unittest.TestCase):
    def setUp(self):
        self.bank = hv.load_bank()

    def test_memory_constraints(self):
        history = [
            {"fecha": "2026-09-01", "motivo": "Argos", "registro": "mito", "composicion": "vista cenital"},
            {"fecha": "2026-11-09", "motivo": "Cerbero", "registro": "emblema", "composicion": "figura centrada"},
        ]
        c = hv.memory_constraints(history, "2026-11-11")
        self.assertEqual(c["motivos_prohibidos"], ["cerbero"])  # Argos ya pasó de 8 semanas
        self.assertEqual(c["ultima_composicion"], "figura centrada")
        self.assertEqual(c["ultimo_registro"], "emblema")

    def test_validate_axes_enforces_memory(self):
        c = {"motivos_prohibidos": ["cerbero"], "ultima_composicion": "figura centrada",
             "ultimo_registro": "emblema", "escenas_usadas": {}}
        raw = {"registro": "mito", "motivo": "Ulises y las sirenas", "escena": "Odysseus tied to the mast...",
               "composicion": "figura centrada", "estado": "grietas", "alt": "Ulises atado al mástil."}
        axes = hv.validate_axes(raw, self.bank, c)
        self.assertIsNotNone(axes)
        self.assertNotEqual(axes.composicion, "figura centrada")  # se corrige, no se repite
        self.assertIsNone(hv.validate_axes({**raw, "motivo": "Cerbero"}, self.bank, c))
        self.assertIsNone(hv.validate_axes({**raw, "registro": "emblema"}, self.bank, c))
        self.assertIsNone(hv.validate_axes({**raw, "estado": "neón"}, self.bank, c))

    def test_focus_from_composition(self):
        c = {"motivos_prohibidos": [], "ultima_composicion": None, "ultimo_registro": None, "escenas_usadas": {}}
        raw = {"registro": "mito", "motivo": "Eco", "escena": "Echo speaks...", "composicion": "sujeto a la izquierda",
               "estado": "laguna", "alt": "Eco."}
        self.assertEqual(hv.validate_axes(raw, self.bank, c).foco, "28% 45%")

    def test_prompt_has_fixed_block_and_three_axes(self):
        blocks = hv.load_prompt_blocks()
        axes = hv.Axes("mito", "Eco", "Echo's voice multiplies as gold waves.", "diagonal", "laguna", "Eco.")
        p = hv.mosaic_prompt(blocks, axes, with_refs=True)
        self.assertTrue(p.startswith("Match the tessera size"))
        self.assertIn(blocks["mosaico"].strip(), p)
        self.assertIn("SUBJECT: Echo", p)
        self.assertIn("COMPOSITION: diagonal composition.", p)
        self.assertIn("MOSAIC STATE: a lacuna", p)
        g = hv.engraving_prompt(blocks, axes)
        self.assertIn("Sepia copperplate engraving", g)
        self.assertNotIn("[SUJETO]", g)

    def test_suggestions_from_bank(self):
        self.assertIn("Eco", hv.suggest_motivos(self.bank, "clonación de voz en un banco"))


class ProduceTest(unittest.TestCase):
    def setUp(self):
        self.axes = hv.Axes("mito", "Eco", "Echo...", "sujeto a la derecha", "grietas", "Eco.", "72% 45%")
        patcher = mock.patch.object(hv, "review_image", side_effect=self._review)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.review_ok = True

    async def _review(self, data, tecnica):
        return self.review_ok, "revisión simulada", 40.0

    def test_first_passing_batch_candidate_wins(self):
        client = FakeClient([jpeg(0.0), jpeg(0.04)], [])
        out = run(hv.produce(client, self.axes, sunday=False))
        self.assertEqual(out.tecnica, "mosaico")
        self.assertEqual([a.passed for a in out.attempts], [False, True])
        self.assertEqual(out.foco, "72% 45%")  # composición lateral: manda la composición
        self.assertTrue(all(a.via == "batch" for a in out.attempts))

    def test_falls_back_to_engraving(self):
        client = FakeClient([jpeg(0.0), jpeg(0.0, blue=True)], [jpeg(0.0), jpeg(0.0)])
        out = run(hv.produce(client, self.axes, sunday=False))
        self.assertEqual(out.tecnica, "grabado")
        self.assertIn("Sepia copperplate engraving", out.prompt)
        self.assertEqual(len(out.attempts), 4)

    def test_nothing_published_when_engraving_fails_review(self):
        self.review_ok = False
        client = FakeClient([jpeg(0.04), jpeg(0.04)], [jpeg(0.04), jpeg(0.0)])
        self.assertIsNone(run(hv.produce(client, self.axes, sunday=False)))

    def test_sunday_goes_straight_to_engraving(self):
        client = FakeClient([], [jpeg(0.0)])
        out = run(hv.produce(client, self.axes, sunday=True))
        self.assertEqual(out.tecnica, "grabado")
        self.assertEqual(len(client.prompts), 1)

    def test_batch_failure_falls_back_to_direct(self):
        client = FakeClient([], [jpeg(0.04), jpeg(0.04)])

        async def boom(*a, **k):
            raise TimeoutError("lento")
        client.generate_batch = boom
        out = run(hv.produce(client, self.axes, sunday=False))
        self.assertEqual(out.attempts[0].via, "directo")


class PublishAndPostprocessTest(unittest.TestCase):
    def test_publish_writes_variants_and_history(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        axes = hv.Axes("mito", "Eco", "Echo...", "diagonal", "grietas", "Eco.")
        outcome = hv.HeroOutcome(jpeg(0.04, size=(2400, 1028)), "mosaico", axes, "50% 45%", "p")
        hero = hv.publish(outcome, tmp, "2026-11-10")
        for name in ("hero-light.jpg", "hero-dark.jpg", "hero-thumb.jpg"):
            self.assertTrue((tmp / "data" / "2026-11-10" / name).exists())
        self.assertEqual(hero["dark_url"], "/data/2026-11-10/hero-dark.jpg")
        hist = tmp / "hist.json"
        hv.remember("2026-11-10", outcome, hist)
        self.assertEqual(json.loads(hist.read_text())["imagenes"][0]["motivo"], "Eco")

    def test_dark_variant_protects_gold(self):
        a = hp.load_rgb(jpeg(0.05))
        dark = hp.dark_mosaic(a)
        gold_px, bg_px = a[181, 10], a[181, 400]
        self.assertLess(abs(dark[181, 10] - gold_px).max(), 0.05)   # el oro conserva su luz
        self.assertLess(dark[181, 400].mean(), 0.35)                 # el fondo se oscurece
        self.assertGreater(bg_px.mean(), 0.7)

    def test_color_check(self):
        self.assertTrue(hp.color_check(hp.load_rgb(jpeg(0.04))).ok)
        self.assertFalse(hp.color_check(hp.load_rgb(jpeg(0.0))).gold_ok)
        self.assertFalse(hp.color_check(hp.load_rgb(jpeg(0.04, blue=True))).foreign_ok)

    def test_tone_gain_is_bounded(self):
        a = np.full((200, 200, 3), 0.4, dtype=np.float32)
        out = hp.match_mosaic_tone(a)
        self.assertLessEqual(out.max(), 0.4 * hp.GAIN_MAX + 1e-6)

    def test_engraving_paper_whitened_and_dark_is_ivory_on_obsidian(self):
        a = np.full((300, 600, 3), [0.93, 0.88, 0.78], dtype=np.float32)
        a[100:200, 300:320] = [0.35, 0.25, 0.15]
        light = hp.whiten_paper(a)
        self.assertGreater(light[20, 20].min(), 0.97)
        dark = hp.dark_engraving(light)
        self.assertLess(dark[20, 20].max(), 0.1)


if __name__ == "__main__":
    unittest.main()


class CostAndArchiveTest(unittest.TestCase):
    """Costo real (todo lo generado) y respaldo de archivo: nunca sin imagen."""

    def setUp(self):
        self.axes = hv.Axes("mito", "Talos", "Talos...", "figura centrada", "grietas", "Talos.")
        patcher = mock.patch.object(hv, "review_image", side_effect=self._review)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.review_ok = True
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    async def _review(self, data, tecnica):
        return self.review_ok, "revisión simulada", 40.0

    def test_both_batch_candidates_are_billed_even_if_first_wins(self):
        client = FakeClient([jpeg(0.04), jpeg(0.04)], [])
        ledger = hv.Ledger()
        out = run(hv.produce(client, self.axes, sunday=False, ledger=ledger))
        self.assertEqual(len(out.attempts), 1)          # solo se evaluó la primera
        self.assertEqual(ledger.generated, 2)           # pero se pagaron las dos
        one = hv._cost(Resp(jpeg(0.04), batch=True))
        self.assertGreater(one, 0)
        self.assertAlmostEqual(out.cost_usd, 2 * one, places=6)

    def test_pick_archive_rules(self):
        archive = [
            {"archivo": "a.jpg", "tecnica": "mosaico", "motivo": "Eco"},
            {"archivo": "b.jpg", "tecnica": "mosaico", "motivo": "El enigma de la Esfinge"},
            {"archivo": "c.jpg", "tecnica": "grabado", "motivo": "Jano"},
        ]
        hist = [{"fecha": "2026-11-09", "motivo": "Eco"}]
        self.assertEqual(hv.pick_archive(hist, "2026-11-13", False, archive)["archivo"], "b.jpg")
        self.assertEqual(hv.pick_archive(hist, "2026-11-15", True, archive)["archivo"], "c.jpg")
        # Todas recientes: se repite la de uso más antiguo antes que quedarse sin imagen.
        hist2 = [{"fecha": "2026-11-02", "motivo": "El enigma de la Esfinge"},
                 {"fecha": "2026-11-09", "motivo": "Eco"}]
        self.assertEqual(hv.pick_archive(hist2, "2026-11-13", False, archive)["archivo"], "b.jpg")
        self.assertIsNone(hv.pick_archive([], "2026-11-13", False, []))

    def test_archive_files_exist_and_mosaics_pass_color_check(self):
        entries = hv.load_archive()
        raw = (hv.yaml.safe_load(hv.ARCHIVE_FILE.read_text(encoding="utf-8")) or {})["imagenes"]
        self.assertEqual(len(entries), len(raw))        # ninguna apunta a un archivo inexistente
        self.assertTrue(any(e["tecnica"] == "mosaico" for e in entries))
        self.assertTrue(any(e["tecnica"] == "grabado" for e in entries))
        hp.configure(hv.load_prompt_blocks().get("control"))
        for e in entries:
            self.assertTrue(e.get("alt") and e.get("motivo"), e["archivo"])
            if e["tecnica"] == "mosaico":
                data = (hv.ARCHIVE_DIR / e["archivo"]).read_bytes()
                self.assertTrue(hp.color_check(hp.load_rgb(data)).ok, e["archivo"])

    def _generate(self, client):
        hist = self.tmp / "hist.json"
        axes = hv.Axes("mito", "Talos", "Talos...", "figura centrada", "grietas", "Talos.")
        load_orig, remember_orig = hv.load_history, hv.remember
        with mock.patch.object(hv, "ROOT", self.tmp), \
             mock.patch.object(hv, "choose_axes", mock.AsyncMock(return_value=(axes, None))), \
             mock.patch.object(hv, "load_history", lambda path=hist: load_orig(hist)), \
             mock.patch.object(hv, "remember", lambda d, o, path=hist: remember_orig(d, o, hist)):
            return run(hv.generate_v32(client, None, {}, [], "2026-11-13", self.tmp / "web"))

    def test_gemini_down_uses_archive_image(self):
        class Down(FakeClient):
            async def generate_batch(self, *a, **k):
                raise RuntimeError("429 spend cap")

            async def generate(self, *a, **k):
                raise RuntimeError("429 spend cap")
        res = self._generate(Down([], []))
        self.assertIsNotNone(res)
        self.assertTrue(res["hero_image"]["archivo"])
        self.assertEqual(res["usage"]["imagenes_generadas"], 0)
        self.assertIn("Gemini no respondió", res["notice"])
        for name in ("hero-light.jpg", "hero-dark.jpg", "hero-thumb.jpg"):
            self.assertTrue((self.tmp / "web" / "data" / "2026-11-13" / name).exists())
        hist = json.loads((self.tmp / "hist.json").read_text())["imagenes"]
        self.assertTrue(hist[-1]["archivo"])

    def test_rejected_candidates_use_archive_and_report_full_cost(self):
        self.review_ok = False
        client = FakeClient([jpeg(0.04), jpeg(0.04)], [jpeg(0.04), jpeg(0.04)])
        res = self._generate(client)
        self.assertTrue(res["hero_image"]["archivo"])
        self.assertEqual(res["usage"]["imagenes_generadas"], 4)
        self.assertGreater(res["usage"]["cost_usd"], 0)
        self.assertIn("ninguna de 4 candidatas", res["notice"])


class EditionImageGateTest(unittest.TestCase):
    def test_gate(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_edition_image", Path(__file__).resolve().parent.parent / "scripts" / "check_edition_image.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        day = tmp / "data" / "2026-11-13"
        day.mkdir(parents=True)
        self.assertTrue(mod.problems("2026-11-13", tmp))               # sin summary
        (day / "summary.json").write_text(json.dumps({"date": "2026-11-13"}))
        self.assertIn("no tiene imagen", mod.problems("2026-11-13", tmp)[0])
        urls = {k: f"/data/2026-11-13/hero-{n}.jpg" for k, n in
                (("light_url", "light"), ("dark_url", "dark"), ("thumb_url", "thumb"))}
        (day / "summary.json").write_text(json.dumps({"hero_image": urls}))
        self.assertEqual(len(mod.problems("2026-11-13", tmp)), 3)     # archivos faltantes
        for n in ("light", "dark", "thumb"):
            (day / f"hero-{n}.jpg").write_bytes(b"x")
        self.assertEqual(mod.problems("2026-11-13", tmp), [])
