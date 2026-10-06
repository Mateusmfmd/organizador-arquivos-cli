import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from organizador_arquivos.cli import main


class CliTests(unittest.TestCase):
    def test_json_dry_run_output_and_log_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "arquivos"
            root.mkdir()
            (root / "foto.jpg").write_bytes(b"x")
            log = Path(directory) / "organizador.log"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main([str(root), "--dry-run", "--json", "--log-file", str(log)])
            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["planned"], 1)
            self.assertEqual(payload["moved"], 0)
            self.assertTrue(log.exists())
            self.assertTrue((root / "foto.jpg").exists())

    def test_missing_path_returns_error_code(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["/tmp/nao-existe-organizador-cli"])
        self.assertEqual(exit_code, 2)
        self.assertIn("não existe", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
