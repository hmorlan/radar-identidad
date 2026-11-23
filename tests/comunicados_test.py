"""23 nov (revisión de Instinct, P5): sin comunicados de proveedores vía Google News."""
import unittest

from agents.gatherers.regulator_sources import is_press_release_url


class ComunicadosTest(unittest.TestCase):
    def test_comunicados_y_agregadores(self):
        for url in (
            "https://www.metrowestdailynews.com/press-release/story/12345/meinstein-launches-agent/",
            "https://tradersunion.com/news/market-voices/show/123-agentic-ai-foundation/",
            "https://www.openpr.com/news/4123456/ai-agents-identity.html",
            "https://www.prnewswire.com/news-releases/acme-301234567.html",
            "https://markets.businesswire.com/news/home/2026/acme",
            "https://www.example.com/news-release/acme-anuncia",
        ):
            self.assertTrue(is_press_release_url(url), url)

    def test_prensa_independiente_pasa(self):
        for url in (
            "https://www.reuters.com/technology/meta-muse-2026-11-18/",
            "https://www.eleconomista.com.mx/sectorfinanciero/coppel-biometria-20261120-1234.html",
            "https://techcrunch.com/2026/11/18/more-banks-says-customers/",
            "https://www.pymnts.com/news/artificial-intelligence/2026/citi-cautions/",
            "",
        ):
            self.assertFalse(is_press_release_url(url), url)


if __name__ == "__main__":
    unittest.main()
