"""23 nov: sin prefiltro de palabras de IA y tope de 1200 s para resumen y temas."""
import asyncio
import inspect
import os
import unittest
from datetime import datetime
from unittest.mock import patch

from agents.analyzers.news_analyzer import NewsAnalyzer
from agents.base import CollectedItem
from agents import orchestrator


def _item(i, title, content):
    return CollectedItem(id=f"{i:032d}", title=title, content=content, url=f"https://example.com/{i}",
                         author="", published="2026-11-21T10:00:00", source="The Hacker News",
                         source_type="rss")


class SinPrefiltroTest(unittest.TestCase):
    def _run(self, env):
        analyzer = NewsAnalyzer()
        seen = []

        async def fake_filter(items):
            seen.extend(items)
            return []
        analyzer._filter_with_llm = fake_filter
        items = [_item(1, "Meta Muse hijacked through a malicious web page", "The assistant exposed connected accounts."),
                 _item(2, "Renfe pide a sus clientes cambiar la contraseña", "Acceso no autorizado a cuentas.")]
        with patch.dict(os.environ, env, clear=False):
            asyncio.run(analyzer.analyze(items))
        return seen

    def test_todo_llega_al_filtro_de_haiku(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEWS_AI_KEYWORD_PREFILTER", None)
            self.assertEqual(len(self._run({})), 2)

    def test_modo_heredado_se_puede_reactivar(self):
        # "mail" no aparece; ninguna de las dos tiene una palabra de la lista heredada.
        self.assertEqual(len(self._run({"NEWS_AI_KEYWORD_PREFILTER": "1"})), 0)


class TopeResumenYTemasTest(unittest.TestCase):
    def test_resumen_y_temas_usan_el_tope_de_la_edicion(self):
        src = inspect.getsource(orchestrator)
        for caller in ("orchestrator.summary", "orchestrator.topics"):
            antes = src[:src.index(f'caller="{caller}"')]
            self.assertIn("with attempt_timeout(_edition_timeout()):", antes[-700:], caller)


if __name__ == "__main__":
    unittest.main()
