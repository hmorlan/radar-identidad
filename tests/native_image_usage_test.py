"""El modo native debe contar los tokens de pensamiento en el costo de la imagen."""
import unittest
from types import SimpleNamespace as NS

from agents.cost_tracker import price_image_usage
from generators.image_client import native_usage_to_openai_shape


class NativeUsageTest(unittest.TestCase):
    def test_thinking_and_modalities_are_priced_separately(self):
        meta = NS(
            prompt_token_count=600,
            candidates_token_count=1120,
            thoughts_token_count=500,
            total_token_count=2220,
            candidates_tokens_details=[NS(modality="MediaModality.IMAGE", token_count=1120)],
        )
        usage = native_usage_to_openai_shape(meta)
        self.assertEqual(usage["completion_tokens"], 1620)
        self.assertEqual(usage["completion_tokens_details"]["reasoning_tokens"], 500)
        cost = price_image_usage(usage)
        # 1120 imagen a $120/M + 500 pensamiento a $12/M + 600 entrada a $2/M ≈ $0.1416
        self.assertAlmostEqual(cost.total_cost, 0.1344 + 0.006 + 0.0012, places=4)

    def test_without_breakdown_falls_back_to_candidates_as_image(self):
        usage = native_usage_to_openai_shape(NS(prompt_token_count=10, candidates_token_count=1120))
        self.assertEqual(usage["completion_tokens_details"]["image_tokens"], 1120)

    def test_none(self):
        self.assertIsNone(native_usage_to_openai_shape(None))


if __name__ == "__main__":
    unittest.main()
