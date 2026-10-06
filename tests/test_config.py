import json
import tempfile
import unittest
from pathlib import Path

from organizador_arquivos.config import ConfigError, OrganizerConfig, load_config


class ConfigTests(unittest.TestCase):
    def test_defaults_are_usable_and_independent(self):
        first = OrganizerConfig()
        second = OrganizerConfig()
        first.categories["Imagens"].append(".custom")
        self.assertNotIn(".custom", second.categories["Imagens"])
        self.assertEqual(first.conflict_strategy, "rename")

    def test_json_is_loaded_and_extensions_are_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "categories": {"Fotos": ["JPG", ".PNG"]},
                        "unknown_category": "Sem categoria",
                        "recursive": True,
                        "include_hidden": True,
                        "conflict_strategy": "skip",
                        "ignore": ["tmp", "tmp"],
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(path)
        self.assertEqual(config.categories, {"Fotos": [".jpg", ".png"]})
        self.assertEqual(config.unknown_category, "Sem categoria")
        self.assertTrue(config.recursive)
        self.assertTrue(config.include_hidden)
        self.assertEqual(config.ignore, ["tmp"])

    def test_rejects_invalid_json_and_unknown_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.json"
            invalid.write_text("{", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(invalid)
        with self.assertRaises(ConfigError):
            OrganizerConfig.from_mapping({"categories": {"A": [".txt"]}, "extra": True})

    def test_rejects_duplicate_extensions_and_unsafe_category(self):
        with self.assertRaises(ConfigError):
            OrganizerConfig.from_mapping({"categories": {"A": [".txt"], "B": ["TXT"]}})
        with self.assertRaises(ConfigError):
            OrganizerConfig.from_mapping({"categories": {"../fora": [".txt"]}})

    def test_missing_config_has_clear_error(self):
        with self.assertRaisesRegex(ConfigError, "não encontrado"):
            load_config("/tmp/arquivo-que-nao-existe-organizador.json")


if __name__ == "__main__":
    unittest.main()
