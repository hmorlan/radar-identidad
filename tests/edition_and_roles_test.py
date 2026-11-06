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


class BuildEditionTest(unittest.TestCase):
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
