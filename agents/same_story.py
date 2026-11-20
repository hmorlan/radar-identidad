"""Un hecho, una entrada: agrupa las notas que cuentan el mismo hecho.

El 20 nov la lista de Noticias mostró el ataque al proveedor de Visa/JPMorgan cuatro
veces, Optimizely tres y el paquete PyPI de Microsoft tres. El ranking (reduce_rank)
ya leía todas esas notas; ahora además devuelve ``mismo_hecho``: grupos de IDs que
cuentan lo mismo, con la de mejor fuente primero. Aquí se pliegan: queda una
entrada (la principal, con el puntaje más alto del grupo) y las demás pasan a
``metadata['tambien_en']`` para que el sitio diga "También lo cubren".
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Sequence, Tuple

logger = logging.getLogger(__name__)

MAX_GROUPS = 20
MAX_PER_GROUP = 8


def sanitize_groups(value: Any) -> List[List[str]]:
    """Grupos de 2+ IDs (texto), sin repetir un ID en dos grupos."""
    if not isinstance(value, list):
        return []
    seen: set = set()
    groups: List[List[str]] = []
    for raw in value[:MAX_GROUPS * 2]:
        if not isinstance(raw, list):
            continue
        ids: List[str] = []
        for entry in raw[:MAX_PER_GROUP]:
            if isinstance(entry, str):
                entry = entry.strip()[:64]
                if entry and entry not in seen and entry not in ids:
                    ids.append(entry)
        if len(ids) >= 2:
            seen.update(ids)
            groups.append(ids)
        if len(groups) >= MAX_GROUPS:
            break
    return groups


def fold_same_story(groups: Sequence[Sequence[str]], items: List[Any],
                    top_ids: Iterable[str] = ()) -> Tuple[List[Any], Dict[str, str]]:
    """Pliega cada grupo en su nota principal.

    Devuelve la lista sin duplicados (mismo orden) y ``{id_plegado: id_principal}``.
    La principal es la primera del grupo que esté en el top 10, si alguna está;
    si no, la primera del grupo (el ranking la pone primero por mejor fuente).
    """
    by_id = {a.item.id: a for a in items}
    top = set(top_ids)
    folded: Dict[str, str] = {}
    for group in groups:
        members = [by_id[i] for i in group if i in by_id and i not in folded]
        if len(members) < 2:
            continue
        primary = next((m for m in members if m.item.id in top), members[0])
        others = [m for m in members if m is not primary]
        meta = primary.item.metadata if isinstance(primary.item.metadata, dict) else {}
        primary.item.metadata = meta
        also = list(meta.get("tambien_en") or [])
        known = {a.get("url") for a in also}
        for m in others:
            if m.item.url not in known:
                also.append({"source": m.item.source or "", "url": m.item.url or "",
                             "title": m.item.title or ""})
            folded[m.item.id] = primary.item.id
            primary.importance_score = max(primary.importance_score or 0, m.importance_score or 0)
        meta["tambien_en"] = also[:MAX_PER_GROUP]
    if folded:
        logger.info("Un hecho, una entrada: %d notas plegadas en %d", len(folded),
                    len(set(folded.values())))
    return [a for a in items if a.item.id not in folded], folded
