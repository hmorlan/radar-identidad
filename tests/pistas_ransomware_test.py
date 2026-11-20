"""Pistas de ransomware: periodo, países y nunca la dirección .onion."""
import json
import unittest
from datetime import date
from types import SimpleNamespace

from scripts.pistas_ransomware import pistas


class PistasTest(unittest.TestCase):
    def test_periodo_sin_onion_y_fallas(self):
        rows = [
            {"discovered": "2026-11-18T22:11:51+00:00", "group_name": "N0n", "post_title": "Empresa X",
             "description": "transporte · México", "website": "x.mx",
             "post_url": "http://abc.onion"},
            {"discovered": "2026-11-10T01:00:00+00:00", "group_name": "Viejo", "post_title": "Y"},
        ]

        def get(url, **kw):
            if url.endswith("/CO"):
                raise RuntimeError("caída")
            data = rows if url.endswith("/MX") else []
            return SimpleNamespace(json=lambda: data, raise_for_status=lambda: None)

        d = pistas(date(2026, 11, 17), date(2026, 11, 19), get=get)
        self.assertEqual([p["victima_segun_el_grupo"] for p in d["pistas"]], ["Empresa X"])
        self.assertNotIn("onion", json.dumps(d))
        self.assertEqual(d["fallas"], ["CO: RuntimeError"])
        self.assertIn("https://ransomware.mx/intel/2026-11-18/", d["resumen_mexico"])
        self.assertIn("sin verificar", d["aviso"])


if __name__ == "__main__":
    unittest.main()
