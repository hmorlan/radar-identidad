"""Notas de la edición, verificación, modelos por rol, tope de gasto y costo por modelo."""
import asyncio
import json
import os
import unittest
from types import SimpleNamespace as NS
from unittest import mock

from agents import edition_notes as en
from agents.base import AnalyzedItem, CategoryReport, CollectedItem
from agents.cost_tracker import APICallRecord, CostTracker
from agents.llm_client import ThinkingLevel
from agents.model_roles import RoleRoutedLLMClient, RunBudgetExceeded, resolve_max_cost


def _item(i, category="news", score=80.0):
    it = CollectedItem(
        id=f"id{i}", title=f"Título {i}", content=f"Contenido de la fuente {i}.",
        url=f"https://example.org/{i}", author="", published="2026-11-05T10:00:00",
        source="The Record", source_type="rss", tags=[], metadata={}, keywords=[],
    )
    return AnalyzedItem(item=it, summary=f"Resumen {i}", importance_score=score,
                        reasoning="r", themes=["Tema"])


def _reports():
    news = [_item(i) for i in range(3)]
    research = [_item(10, "research")]
    return {
        "news": CategoryReport(category="news", top_items=news, all_items=news,
                               category_summary="", themes=[], cross_signals=[], total_collected=3),
        "research": CategoryReport(category="research", top_items=research, all_items=research,
                                   category_summary="", themes=[], cross_signals=[], total_collected=1),
    }


NOTES_JSON = json.dumps({
    "titular": "Robo de sesiones sin contraseña",
    "notas": [
        {"id": "id0", "titulo": "nota cero", "que_paso": "Pasó algo.", "por_que_importa": "Importa.",
         "pregunta_de_fondo": "¿Quién responde?", "senal": "alta"},
        {"id": "id1", "titulo": "nota uno", "que_paso": "Pasó otra cosa.", "por_que_importa": "Importa.",
         "pregunta_de_fondo": None, "senal": "media"},
        {"id": "id2", "titulo": "nota dos", "que_paso": "Hecho dudoso.", "por_que_importa": "Importa.",
         "senal": "baja"},
        {"id": "inventado", "titulo": "x", "que_paso": "x", "por_que_importa": "x", "senal": "alta"},
        {"id": "id10", "titulo": "sin señal", "que_paso": "x", "por_que_importa": "x", "senal": "urgente"},
    ],
})

CHECK_JSON = json.dumps({"revisiones": [
    {"id": "id0", "veredicto": "verificada", "motivo": "Respaldada."},
    {"id": "id1", "veredicto": "corregida", "motivo": "Cifra sin respaldo.",
     "que_paso": "Pasó otra cosa, sin cifra.", "senal": "baja"},
    {"id": "id2", "veredicto": "descartar", "motivo": "La fuente no lo dice."},
]})


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.by_id = {a.item.id: (c, a) for c, a in en.collect_candidates(_reports())}

    def test_parse_drops_unknown_ids_and_bad_signals(self):
        edition = en.parse_notes(NOTES_JSON, self.by_id, max_notes=8)
        self.assertEqual([n.item_id for n in edition.notas], ["id0", "id1", "id2"])
        self.assertEqual(edition.titular, "Robo de sesiones sin contraseña")
        self.assertEqual(edition.notas[0].url, "https://example.org/0")
        self.assertIsNone(edition.notas[1].pregunta_de_fondo)

    def test_fact_check_verifies_corrects_and_drops(self):
        edition = en.apply_fact_check(en.parse_notes(NOTES_JSON, self.by_id, 8), CHECK_JSON)
        self.assertEqual([n.item_id for n in edition.notas], ["id0", "id1"])
        self.assertEqual(edition.notas[0].verificacion, "verificada")
        self.assertEqual(edition.notas[1].verificacion, "corregida")
        self.assertEqual(edition.notas[1].que_paso, "Pasó otra cosa, sin cifra.")
        self.assertEqual(edition.notas[1].senal, "baja")

    def test_roundtrip(self):
        edition = en.parse_notes(NOTES_JSON, self.by_id, 8)
        again = en.Edition.from_dict(edition.to_dict())
        self.assertEqual(again.to_dict(), edition.to_dict())


class NoNetwork(unittest.TestCase):
    """build_edition baja páginas de fuentes con RSS corto: en tests, nunca a la red."""

    def setUp(self):
        patcher = mock.patch.object(en, "_fetch_page", side_effect=RuntimeError("sin red en tests"))
        patcher.start()
        self.addCleanup(patcher.stop)


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def call_with_thinking(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return NS(content=reply)


class FakePrompts:
    def get_orchestration_prompt(self, name, context):
        return f"Instrucciones {name} para {context['date']}"


class BuildEditionTest(NoNetwork):
    def test_writes_then_verifies_with_main_model_profile(self):
        client = FakeClient([NOTES_JSON, CHECK_JSON])
        edition = asyncio.run(en.build_edition(client, FakePrompts(), _reports(), "2026-11-06"))
        self.assertEqual(len(edition.notas), 2)
        self.assertEqual(edition.degradations, [])
        self.assertEqual([c["caller"] for c in client.calls],
                         ["orchestrator.edition_notes", "orchestrator.edition_fact_check"])
        self.assertTrue(all(c["profile"] == ThinkingLevel.DEEP for c in client.calls))

    def test_failed_check_keeps_notes_unverified_and_degrades(self):
        client = FakeClient([NOTES_JSON, RuntimeError("caído")])
        edition = asyncio.run(en.build_edition(client, FakePrompts(), _reports(), "2026-11-06"))
        self.assertEqual(len(edition.notas), 3)
        self.assertTrue(all(n.verificacion == "sin_verificar" for n in edition.notas))
        self.assertTrue(edition.degradations)


class CoherenceTest(NoNetwork):
    DERIVED = {
        "executive_summary": "El FBI [alerta de fraude](/?date=x#item-1) y deepfakes que superan la verificación.",
        "tema:0": "Deepfakes que superan verificaciones de identidad en dos exchanges.",
    }

    def _edition(self):
        by_id = {a.item.id: (c, a) for c, a in en.collect_candidates(_reports())}
        return en.apply_fact_check(en.parse_notes(NOTES_JSON, by_id, 8), CHECK_JSON), by_id

    def test_check_records_discarded_notes(self):
        edition, _ = self._edition()
        self.assertEqual([d["id"] for d in edition.descartadas], ["id2"])
        self.assertTrue(en.needs_coherence(edition))

    def test_parse_keeps_only_exact_link_safe_edits(self):
        texts = {"titular": "Deepfakes burlan el KYC", **self.DERIVED}
        reply = json.dumps({"ajustes": [
            {"campo": "executive_summary", "antes": "y deepfakes que superan la verificación",
             "despues": "y deepfakes que el servidor rechazó en todos los intentos", "motivo": "fuente"},
            {"campo": "executive_summary", "antes": "[alerta de fraude](/?date=x#item-1)",
             "despues": "alerta de fraude", "motivo": "pierde el enlace"},
            {"campo": "tema:0", "antes": "no está en el texto", "despues": "x", "motivo": ""},
            {"campo": "titular", "antes": "burlan el KYC", "despues": "intentan burlar el KYC", "motivo": ""},
        ]})
        edits = en.parse_coherence(reply, texts)
        self.assertEqual([(e["campo"], e["antes"]) for e in edits],
                         [("executive_summary", "y deepfakes que superan la verificación"),
                          ("titular", "burlan el KYC")])
        out = en.apply_edits(texts, edits)
        self.assertIn("[alerta de fraude](/?date=x#item-1)", out["executive_summary"])
        self.assertIn("rechazó en todos los intentos", out["executive_summary"])
        self.assertEqual(out["titular"], "Deepfakes intentan burlar el KYC")

    def test_build_reconciles_derived_texts_after_corrections(self):
        reply = json.dumps({"ajustes": [
            {"campo": "tema:0", "antes": "Deepfakes que superan verificaciones",
             "despues": "Deepfakes que intentaron superar verificaciones", "motivo": "fuente"}]})
        client = FakeClient([NOTES_JSON, CHECK_JSON, reply])
        edition = asyncio.run(en.build_edition(client, FakePrompts(), _reports(), "2026-11-06",
                                               derived=dict(self.DERIVED)))
        self.assertEqual(client.calls[-1]["caller"], "orchestrator.edition_coherence")
        self.assertEqual(client.calls[-1]["profile"], ThinkingLevel.QUICK)
        self.assertEqual(len(edition.ajustes), 1)
        self.assertEqual(edition.degradations, [])
        again = en.Edition.from_dict(edition.to_dict())
        self.assertEqual(again.ajustes, edition.ajustes)

    def test_sin_correcciones_igual_revisa_el_nivel_de_certeza(self):
        # 23 nov (Instinct, P2): el resumen de Noticias quitó el "aparente" de una
        # nota verificada. La coherencia corre aunque no haya correcciones y recibe
        # las notas verificadas como referencia.
        all_ok = json.dumps({"revisiones": [{"id": i, "veredicto": "verificada"} for i in ("id0", "id1", "id2")]})
        reply = json.dumps({"ajustes": [
            {"campo": "executive_summary", "antes": "y deepfakes que superan la verificación",
             "despues": "y deepfakes que, según la fuente, intentan superar la verificación", "motivo": "certeza"}]})
        client = FakeClient([NOTES_JSON, all_ok, reply])
        edition = asyncio.run(en.build_edition(client, FakePrompts(), _reports(), "2026-11-06",
                                               derived=dict(self.DERIVED)))
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(client.calls[-1]["caller"], "orchestrator.edition_coherence")
        self.assertIn("notas_verificadas", json.dumps(client.calls[-1]["messages"], ensure_ascii=False))
        self.assertEqual(len(edition.ajustes), 1)

    def test_failed_coherence_degrades_without_losing_notes(self):
        client = FakeClient([NOTES_JSON, CHECK_JSON, RuntimeError("caído")])
        edition = asyncio.run(en.build_edition(client, FakePrompts(), _reports(), "2026-11-06",
                                               derived=dict(self.DERIVED)))
        self.assertEqual(len(edition.notas), 2)
        self.assertTrue(any(d.startswith("coherencia") for d in edition.degradations))


class FullTextTest(unittest.TestCase):
    def _cands(self):
        return en.collect_candidates(_reports())

    def test_short_rss_gets_full_page_and_feeds_editor_and_checker(self):
        cands = self._cands()
        long_text = "Controles por compra y tokenización. " * 80
        with mock.patch.object(en, "_fetch_page", return_value=(long_text, "")) as fetch:
            got = asyncio.run(en.enrich_full_text(cands))
        self.assertGreater(got, 0)
        self.assertTrue(fetch.called)
        ctx = json.loads(en.candidates_context(cands))
        enriched = [r for r in ctx if "tokenización" in r["contenido"]]
        self.assertTrue(enriched)
        self.assertGreater(len(enriched[0]["contenido"]), en.CONTENT_CLIP)

    def test_failures_and_soft_404_keep_rss_text(self):
        cands = self._cands()
        with mock.patch.object(en, "_fetch_page", side_effect=RuntimeError("403")):
            self.assertEqual(asyncio.run(en.enrich_full_text(cands)), 0)
        with mock.patch.object(en, "_fetch_page", return_value=("Página no encontrada " + "x" * 3000, "")):
            self.assertEqual(asyncio.run(en.enrich_full_text(cands)), 0)
        self.assertFalse(any("texto_completo" in (a.item.metadata or {}) for _, a in cands))

    def test_can_be_disabled(self):
        with mock.patch.dict(os.environ, {"EDITION_FULLTEXT": "0"}), \
                mock.patch.object(en, "_fetch_page") as fetch:
            self.assertEqual(asyncio.run(en.enrich_full_text(self._cands())), 0)
        fetch.assert_not_called()


class RoleRoutingTest(unittest.TestCase):
    def test_light_for_quick_and_standard_heavy_for_deep(self):
        heavy, light = FakeClient(["h", "h"]), FakeClient(["l", "l"])
        router = RoleRoutedLLMClient(heavy, light)
        asyncio.run(router.call_with_thinking(messages=[], profile=ThinkingLevel.STANDARD, caller="map"))
        asyncio.run(router.call_with_thinking(messages=[], budget_tokens=ThinkingLevel.QUICK, caller="filter"))
        asyncio.run(router.call_with_thinking(messages=[], profile=ThinkingLevel.DEEP, caller="rank"))
        asyncio.run(router.call_with_thinking(messages=[], profile=ThinkingLevel.ULTRATHINK, caller="topics"))
        self.assertEqual([c["caller"] for c in light.calls], ["map", "filter"])
        self.assertTrue(all(c["profile"] == ThinkingLevel.QUICK for c in light.calls))
        self.assertEqual([c["caller"] for c in heavy.calls], ["rank", "topics"])

    def test_without_light_everything_goes_to_main(self):
        heavy = FakeClient(["h"])
        asyncio.run(RoleRoutedLLMClient(heavy).call_with_thinking(messages=[], profile=ThinkingLevel.QUICK))
        self.assertEqual(len(heavy.calls), 1)

    def test_budget_blocks_calls_once_reached(self):
        tracker = CostTracker("claude-opus-5-5")
        tracker.record_call("x", {"input_tokens": 1_000_000, "output_tokens": 0}, model="claude-opus-5-5")
        heavy = FakeClient(["h"])
        router = RoleRoutedLLMClient(heavy, max_cost_usd=3.0)
        with mock.patch("agents.model_roles.get_tracker", return_value=tracker):
            with self.assertRaises(RunBudgetExceeded):
                asyncio.run(router.call_with_thinking(messages=[], profile=ThinkingLevel.DEEP, caller="rank"))
        self.assertEqual(heavy.calls, [])

    def test_resolve_max_cost(self):
        with mock.patch.dict(os.environ, {"PIPELINE_MAX_COST_USD": "7.5"}):
            self.assertEqual(resolve_max_cost(3.0), 7.5)
        with mock.patch.dict(os.environ, {"PIPELINE_MAX_COST_USD": ""}):
            self.assertEqual(resolve_max_cost(3.0), 3.0)
            self.assertIsNone(resolve_max_cost(0))


class PerModelCostTest(unittest.TestCase):
    def test_mixed_models_priced_at_their_own_rates(self):
        tracker = CostTracker("claude-opus-5-5")
        tracker.record_call("rank", {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
                            model="claude-opus-5-5")
        tracker.record_call("map", {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
                            model="claude-haiku-5-5")
        costs = [tracker.calculate_cost(c).total_cost for c in tracker.calls]
        self.assertAlmostEqual(costs[0], 4.0 + 20.0)
        # 1M de entrada en una sola petición rebasa 100K: tarifa de contexto largo.
        self.assertAlmostEqual(costs[1], 0.50 + 2.50)
        self.assertFalse(tracker.pricing_is_estimate)

    def test_haiku_short_prompt_rate(self):
        tracker = CostTracker("claude-opus-5-5")
        rec = APICallRecord(timestamp="", caller="map", thinking_level=None, input_tokens=50_000, output_tokens=10_000,
                            model="claude-haiku-5-5-20261015")
        self.assertAlmostEqual(tracker.calculate_cost(rec).total_cost, 0.005 + 0.005)


if __name__ == "__main__":
    unittest.main()


class ReduceLimitTest(unittest.TestCase):
    def test_research_capped_and_env_override(self):
        from unittest import mock
        from agents.base import reduce_candidate_limit
        self.assertEqual(reduce_candidate_limit("research"), 25)
        self.assertEqual(reduce_candidate_limit("news"), 50)
        with mock.patch.dict("os.environ", {"REDUCE_MAX_CANDIDATES_RESEARCH": "10"}):
            self.assertEqual(reduce_candidate_limit("research"), 10)
