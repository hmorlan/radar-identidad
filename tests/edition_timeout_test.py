"""Arreglos tras la corrida del 20 nov: las notas de la edición agotaron sus intentos.

- El redactor y el verificador tienen su propio tope por intento (attempt_timeout),
  sin cambiar el de las demás llamadas.
- El texto completo de la fuente se recorta a FULLTEXT_CLIP (2000).
- El control de publicación rechaza una edición sin notas.
"""
import asyncio
import os
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from agents import edition_notes
from agents.llm_client import AsyncAnthropicClient, LLMAttemptTimeout, attempt_timeout
from scripts.validate_report import validate


def _client(timeout):
    client = AsyncAnthropicClient.__new__(AsyncAnthropicClient)
    client.provider_id = "anthropic"
    client.model = "claude-opus-5-5"
    client.mode = "anthropic"
    client.timeout = timeout
    client.stream_stall_seconds = 5.0
    client._provider_alive_at = 0.0
    return client


def _slow(seconds):
    async def run(progress, **kwargs):
        end = time.time() + seconds
        while time.time() < end:
            progress["last_chunk_at"] = time.time()
            await asyncio.sleep(0.01)
        return "ok"
    return run


def _stream(client):
    return asyncio.run(client._stream_message(
        progress={}, model=client.model, messages=[{"role": "user", "content": "x"}], max_tokens=10))


class AttemptTimeoutOverrideTest(unittest.TestCase):
    def test_sin_override_se_corta_en_el_tope_general(self):
        client = _client(0.2)
        client._stream_message_anthropic = _slow(0.6)
        with self.assertRaises(LLMAttemptTimeout):
            _stream(client)

    def test_el_override_da_mas_tiempo_dentro_del_bloque(self):
        client = _client(0.2)
        client._stream_message_anthropic = _slow(0.6)
        with attempt_timeout(2.0):
            self.assertEqual(_stream(client), "ok")

    def test_el_override_no_se_queda_puesto_al_salir(self):
        client = _client(0.2)
        client._stream_message_anthropic = _slow(0.6)
        with attempt_timeout(2.0):
            pass
        with self.assertRaises(LLMAttemptTimeout):
            _stream(client)

    def test_tope_de_la_edicion_configurable(self):
        with mock.patch.dict(os.environ, {"EDITION_LLM_TIMEOUT_SECONDS": "900"}):
            self.assertEqual(edition_notes._edition_timeout(), 900.0)
        with mock.patch.dict(os.environ, {"EDITION_LLM_TIMEOUT_SECONDS": ""}):
            self.assertEqual(edition_notes._edition_timeout(), 1200.0)
        with mock.patch.dict(os.environ, {"EDITION_LLM_TIMEOUT_SECONDS": "nada"}):
            self.assertEqual(edition_notes._edition_timeout(), 1200.0)


class TextoCompletoRecortadoTest(unittest.TestCase):
    def test_texto_completo_se_recorta_a_2000(self):
        it = SimpleNamespace(content="corto", metadata={"texto_completo": "palabra " * 2000})
        self.assertLessEqual(len(edition_notes.source_text(it, 600)), 2000)
        self.assertEqual(edition_notes.FULLTEXT_CLIP, 2000)


class EdicionSinNotasNoSePublicaTest(unittest.TestCase):
    def _summary(self, edition):
        s = {
            "date": "2026-11-20",
            "executive_summary": "x" * 800,
            "top_topics": [{"name": "t"}],
            "total_items_analyzed": 150,
            "total_items_collected": 300,
            "categories": {},
        }
        if edition is not None:
            s["edition"] = edition
        return s

    def test_sin_notas_falla(self):
        r = validate(self._summary({"titular": "", "notas": []}), "2026-11-20")
        self.assertFalse(r["valid"])
        self.assertTrue(any("edition.notas" in f for f in r["failures"]))

    def test_con_notas_pasa(self):
        r = validate(self._summary({"titular": "Algo pasó", "notas": [{"id": "a"}]}), "2026-11-20")
        self.assertTrue(r["valid"], r["failures"])

    def test_reporte_anterior_sin_edicion_pasa(self):
        self.assertTrue(validate(self._summary(None), "2026-11-20")["valid"])


if __name__ == "__main__":
    unittest.main()
