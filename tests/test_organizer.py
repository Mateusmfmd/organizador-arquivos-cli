import tempfile
import unittest
from pathlib import Path

from organizador_arquivos.config import OrganizerConfig
from organizador_arquivos.organizer import FileOrganizer, OrganizationError


class OrganizerTests(unittest.TestCase):
    def make_config(self, **overrides):
        values = {
            "categories": {"Imagens": [".jpg", ".png"], "Texto": [".txt"]},
            "unknown_category": "Outros",
            "ignore": [".git"],
        }
        values.update(overrides)
        return OrganizerConfig.from_mapping(values)

    def test_dry_run_does_not_write_and_reports_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "foto.JPG").write_text("foto", encoding="utf-8")
            (root / "leia-me.txt").write_text("texto", encoding="utf-8")
            (root / "sem-extensao").write_text("outro", encoding="utf-8")
            summary = FileOrganizer(root, self.make_config(), dry_run=True).organize()
            self.assertEqual(summary.planned, 3)
            self.assertEqual(summary.moved, 0)
            self.assertEqual(summary.errors, 0)
            self.assertTrue((root / "foto.JPG").exists())
            self.assertFalse((root / "Imagens").exists())

    def test_moves_by_case_insensitive_extension_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "foto.JPG").write_bytes(b"x")
            (root / "notas.txt").write_bytes(b"x")
            (root / "dados.bin").write_bytes(b"x")
            first = FileOrganizer(root, self.make_config()).organize()
            second = FileOrganizer(root, self.make_config()).organize()
            self.assertEqual(first.moved, 3)
            self.assertEqual(second.planned, 0)
            self.assertEqual(second.moved, 0)
            self.assertTrue((root / "Imagens" / "foto.JPG").exists())
            self.assertTrue((root / "Texto" / "notas.txt").exists())
            self.assertTrue((root / "Outros" / "dados.bin").exists())

    def test_conflict_rename_preserves_both_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image_dir = root / "Imagens"
            image_dir.mkdir()
            (image_dir / "foto.jpg").write_text("old", encoding="utf-8")
            (root / "foto.jpg").write_text("new", encoding="utf-8")
            summary = FileOrganizer(root, self.make_config()).organize()
            self.assertEqual(summary.moved, 1)
            self.assertEqual((image_dir / "foto.jpg").read_text(encoding="utf-8"), "old")
            self.assertEqual((image_dir / "foto (1).jpg").read_text(encoding="utf-8"), "new")

    def test_skip_conflict_and_recursive_hidden_ignore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Texto").mkdir()
            (root / "Texto" / "a.txt").write_text("old", encoding="utf-8")
            (root / "a.txt").write_text("new", encoding="utf-8")
            (root / "sub").mkdir()
            (root / "sub" / "b.txt").write_text("b", encoding="utf-8")
            (root / ".hidden.txt").write_text("hidden", encoding="utf-8")
            config = self.make_config(recursive=True, conflict_strategy="skip")
            summary = FileOrganizer(root, config).organize()
            self.assertEqual(summary.moved, 1)
            self.assertEqual(summary.skipped, 1)
            self.assertTrue((root / "sub" / "Texto" / "b.txt").exists())
            self.assertTrue((root / ".hidden.txt").exists())

    def test_does_not_follow_symlink_file_or_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "origem"
            root.mkdir()
            external = Path(directory) / "external.txt"
            external.write_text("outside", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest("links simbólicos indisponíveis neste sistema")
            summary = FileOrganizer(root, self.make_config()).organize()
            self.assertEqual(summary.moved, 0)
            self.assertGreaterEqual(summary.skipped, 1)
            self.assertTrue(link.is_symlink())
            self.assertTrue(external.exists())

    def test_invalid_source_is_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with self.assertRaises(OrganizationError):
                FileOrganizer(missing, self.make_config()).organize()


if __name__ == "__main__":
    unittest.main()
