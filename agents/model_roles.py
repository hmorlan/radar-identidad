"""Enrutamiento de modelos por rol y tope de gasto por corrida.

Radar de Identidad usa dos modelos:

- **Ligero** (``llm.light_model``, p. ej. ``claude-haiku-5-5``): llamadas de perfil
  QUICK y STANDARD — triage, resumen por fuente, detección de temas por categoría,
  enlaces internos. Siempre con ``effort=high``: los niveles más altos no están
  documentados para Haiku 5.5.
- **Principal** (``llm.model``, p. ej. ``claude-opus-5-5``): DEEP y ULTRATHINK —
  selección y resumen por categoría, temas transversales, resumen ejecutivo,
  notas de la edición y su verificación.

Además, antes de cada llamada se compara el costo acumulado de la corrida con
``pipeline.max_cost_usd`` (o la variable ``PIPELINE_MAX_COST_USD``). Al rebasarlo
se lanza :class:`RunBudgetExceeded`, que no se reintenta y detiene la corrida.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from .cost_tracker import get_tracker
from .llm_client import ThinkingLevel

logger = logging.getLogger(__name__)


class RunBudgetExceeded(RuntimeError):
    """The run already spent its configured ceiling; no further LLM calls."""


def resolve_max_cost(configured: Optional[float]) -> Optional[float]:
    """Env var wins over providers.yaml; 0 or empty disables the cap."""
    raw = os.getenv("PIPELINE_MAX_COST_USD")
    value: Optional[float]
    if raw not in (None, ""):
        try:
            value = float(raw)
        except ValueError:
            logger.warning("PIPELINE_MAX_COST_USD=%r no es un número; se ignora", raw)
            value = configured
    else:
        value = configured
    return value if value and value > 0 else None


class RoleRoutedLLMClient:
    """Wraps the async LLM client(s): picks the model by profile and enforces the cap."""

    def __init__(self, heavy: Any, light: Any = None, max_cost_usd: Optional[float] = None):
        self.heavy = heavy
        self.light = light
        self.max_cost_usd = max_cost_usd
        logger.info(
            "Modelos por rol: principal=%s ligero=%s tope=%s",
            getattr(heavy, "model", "router"),
            getattr(light, "model", None) if light else "(mismo que principal)",
            f"US${max_cost_usd:.2f}" if max_cost_usd else "sin tope",
        )

    def _check_budget(self, caller: Optional[str]) -> None:
        if not self.max_cost_usd:
            return
        spent = get_tracker().get_total_cost().total_cost
        if spent >= self.max_cost_usd:
            raise RunBudgetExceeded(
                f"Tope de gasto alcanzado: US${spent:.2f} >= US${self.max_cost_usd:.2f} "
                f"(llamada bloqueada: {caller or 'sin nombre'})"
            )

    def client_for(self, profile: int) -> Any:
        if self.light is not None and profile <= ThinkingLevel.STANDARD:
            return self.light
        return self.heavy

    async def call_with_thinking(self, *args: Any, **kwargs: Any):
        requested = kwargs.get("profile")
        if requested is None:
            requested = kwargs.get("budget_tokens", ThinkingLevel.STANDARD)
        self._check_budget(kwargs.get("caller"))
        client = self.client_for(int(requested))
        if client is self.light:
            # Haiku 5.5: keep effort at "high" (QUICK maps to high).
            kwargs["profile"] = ThinkingLevel.QUICK
            kwargs.pop("budget_tokens", None)
        return await client.call_with_thinking(*args, **kwargs)

    async def close(self) -> None:
        for client in (self.heavy, self.light):
            closer = getattr(client, "close", None)
            if closer is not None:
                result = closer()
                if hasattr(result, "__await__"):
                    await result

    def __getattr__(self, name: str) -> Any:
        # Anything else (model, provider_id, max_output_tokens...) is the main model's.
        return getattr(self.heavy, name)
