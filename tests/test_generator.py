import tempfile
import unittest
from pathlib import Path

from ad_disclaimer_generator import load_rules, render_disclaimer


class GeneratorTests(unittest.TestCase):
    def test_render_includes_required_and_triggered_rules(self):
        csv_data = """id,law_scope,text,required,trigger_field,trigger_value,priority,additional_notes
base-1,law,Base,true,,,10,
fin-1,law,Finance text,false,industry,finance,20,
med-1,law,Medicine text,false,industry,medicine,20,
"""
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry.csv"
            registry.write_text(csv_data, encoding="utf-8")
            rules = load_rules(registry)
            campaign = {
                "industry": "finance",
                "advertiser_name": "ООО Тест",
                "advertiser_inn": "123",
                "advertiser_ogrn": "456",
            }

            output = render_disclaimer(campaign, rules)
            self.assertIn("Base", output)
            self.assertIn("Finance text", output)
            self.assertNotIn("Medicine text", output)
            self.assertIn("ООО Тест", output)


if __name__ == "__main__":
    unittest.main()
