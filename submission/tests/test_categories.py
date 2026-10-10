import unittest

from submission.anonymizer.categories import load_categories


class TestCategories(unittest.TestCase):
    def test_loads_five_categories_in_order(self):
        ids = [c.id for c in load_categories()]
        self.assertEqual(ids, [
            "identity",
            "contact_location",
            "gov_financial_ids",
            "health",
            "sensitive_social",
        ])

    def test_ids_unique_and_fields_present(self):
        categories = load_categories()
        ids = [c.id for c in categories]
        self.assertEqual(len(ids), len(set(ids)))

        for category in categories:
            self.assertTrue(category.name)
            self.assertTrue(category.description)
            self.assertGreaterEqual(len(category.examples), 1)


if __name__ == "__main__":
    unittest.main()
