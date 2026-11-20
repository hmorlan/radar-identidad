"""Un hecho, una entrada (corrida del 20 nov: Visa/JPM 4 veces en Noticias)."""
import unittest
from types import SimpleNamespace

from agents.analysis_schema import sanitize_ranking_result
from agents.same_story import fold_same_story, sanitize_groups


def _a(i, source, score, url=None):
    item = SimpleNamespace(id=i, source=source, url=url or f"https://{source}.test/{i}",
                           title=f"t-{i}", metadata={})
    return SimpleNamespace(item=item, importance_score=score)


class SameStoryTest(unittest.TestCase):
    def test_sanitiza_grupos(self):
        self.assertEqual(sanitize_groups([["a", "b"], ["c"], ["b", "d"], "x", [1, "e", "f"]]),
                         [["a", "b"], ["e", "f"]])
        self.assertEqual(sanitize_groups(None), [])

    def test_el_ranking_conserva_mismo_hecho(self):
        r = sanitize_ranking_result({"top_10": ["a"], "category_summary": "x",
                                     "mismo_hecho": [["a", "b"]]})
        self.assertEqual(r["mismo_hecho"], [["a", "b"]])

    def test_pliega_en_la_principal(self):
        items = [_a("reg", "The Register", 70), _a("ab", "American Banker", 74),
                 _a("ab2", "American Banker", 72), _a("otra", "CSO", 60)]
        out, folded = fold_same_story([["reg", "ab", "ab2"]], items, top_ids=["otra"])
        self.assertEqual([a.item.id for a in out], ["reg", "otra"])
        self.assertEqual(folded, {"ab": "reg", "ab2": "reg"})
        reg = out[0]
        self.assertEqual(reg.importance_score, 74)
        self.assertEqual([x["source"] for x in reg.item.metadata["tambien_en"]],
                         ["American Banker", "American Banker"])

    def test_prefiere_la_que_esta_en_el_top(self):
        items = [_a("a", "A", 70), _a("b", "B", 80)]
        out, folded = fold_same_story([["a", "b"]], items, top_ids=["b"])
        self.assertEqual([x.item.id for x in out], ["b"])
        self.assertEqual(folded, {"a": "b"})

    def test_ids_desconocidos_no_rompen(self):
        items = [_a("a", "A", 70)]
        out, folded = fold_same_story([["a", "zz"]], items)
        self.assertEqual(len(out), 1)
        self.assertEqual(folded, {})


if __name__ == "__main__":
    unittest.main()
