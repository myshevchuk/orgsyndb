"""Reaction-type vocabulary file (procedure-schema)."""

import re
import tempfile
import tomllib
import unittest
from pathlib import Path

from support import REPO, ValidatorTestCase, run_validator

SHIPPED = REPO / "site" / "data" / "reaction_types.toml"
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REQUIRED = ["acylation", "aldol-condensation", "cross-coupling",
            "esterification", "olefination", "protection", "reduction",
            "reductive-amination"]


class ShippedVocabularyTests(ValidatorTestCase):
    def test_shipped_vocabulary_is_well_formed_and_complete(self) -> None:
        """Scenario: Shipped vocabulary is well formed and complete."""
        self.assertTrue(SHIPPED.is_file(),
                        "site/data/reaction_types.toml does not exist")
        data = tomllib.loads(SHIPPED.read_text(encoding="utf-8"))
        for key, entry in data.items():
            self.assertRegex(key, SLUG)
            self.assertIsInstance(entry, dict, key)
            label = entry.get("label")
            self.assertIsInstance(label, str, key)
            self.assertNotEqual(label.strip(), "", key)
        self.assertLessEqual(set(REQUIRED), set(data))

    def test_validator_accepts_the_shipped_vocabulary(self) -> None:
        """Scenario: Validator accepts the shipped vocabulary."""
        self.assertTrue(SHIPPED.is_file(),
                        "site/data/reaction_types.toml does not exist")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "content"
            root.mkdir()
            result = run_validator([root], cwd=Path(tmp))
        self.assert_clean(result)


if __name__ == "__main__":
    unittest.main()
