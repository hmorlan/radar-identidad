"""Tests del archivo de ediciones en R2 (wrangler simulado, sin red)."""
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import archive_r2  # noqa: E402


class FakeBucket:
    """Stands in for `wrangler r2 object get/put` with a local folder."""

    def __init__(self, root: Path):
        self.root = root
        self.puts = []

    def __call__(self, *args):
        action, path = args[2], args[3]
        key = path.split("/", 1)[1]
        target = self.root / key
        file_arg = Path(args[args.index("--file") + 1])
        if action == "get":
            if not target.exists():
                return subprocess.CompletedProcess(args, 1, "", "The specified key does not exist.")
            shutil.copy(target, file_arg)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(file_arg, target)
            self.puts.append(key)
        return subprocess.CompletedProcess(args, 0, "", "")


def write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bucket = FakeBucket(self.tmp / "bucket")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_retired_edition_stays_in_r2_but_is_not_restored(self):
        # config/ediciones_retiradas.txt lista 2026-11-10 (20 nov).
        run1 = self.tmp / "run1"
        write(run1 / "index.json", "{}")
        for day in ("2026-11-10", "2026-11-13"):
            write(run1 / day / "summary.json", "{}")
        archive_r2.push(run1, self.bucket)
        run2 = self.tmp / "run2"
        archive_r2.pull(run2, self.bucket)
        self.assertFalse((run2 / "2026-11-10").exists())
        self.assertTrue((run2 / "2026-11-13" / "summary.json").exists())

    def test_empty_bucket_pull_returns_empty_code(self):
        self.assertEqual(archive_r2.pull(self.tmp / "data", self.bucket), archive_r2.EMPTY)

    def test_roundtrip_and_incremental_push(self):
        run1 = self.tmp / "run1"
        write(run1 / "index.json", '{"dates":["2026-11-11"]}')
        write(run1 / "2026-11-11" / "summary.json", "{}")
        write(run1 / "feeds" / "main.xml", "<feed/>")
        archive_r2.push(run1, self.bucket)
        self.assertIn("archivo/dias/2026-11-11.tar.gz", self.bucket.puts)

        # Next run: fresh checkout, pull, add a day, push only that day.
        run2 = self.tmp / "run2"
        write(run2 / "index.json", "{}")
        self.assertEqual(archive_r2.pull(run2, self.bucket), 0)
        self.assertTrue((run2 / "2026-11-11" / "summary.json").exists())
        self.assertTrue((run2 / "feeds" / "main.xml").exists())
        time.sleep(0.05)
        write(run2 / "2026-11-12" / "summary.json", "{}")
        self.bucket.puts.clear()
        archive_r2.push(run2, self.bucket)
        self.assertEqual(sorted(self.bucket.puts), ["archivo/dias/2026-11-12.tar.gz", "archivo/raiz.tar.gz"])

        run3 = self.tmp / "run3"
        archive_r2.pull(run3, self.bucket)
        self.assertEqual(archive_r2.day_dirs(run3), ["2026-11-11", "2026-11-12"])
        self.assertFalse((run3 / archive_r2.MARKER).read_text() == "")


if __name__ == "__main__":
    unittest.main()


class RetirarEdicionesTest(unittest.TestCase):
    def test_quita_carpeta_indice_y_manifiesto(self):
        from scripts.retirar_ediciones import retirar
        tmp = Path(tempfile.mkdtemp())
        try:
            write(tmp / "2026-11-10" / "summary.json", "{}")
            write(tmp / "2026-11-13" / "summary.json", "{}")
            write(tmp / "index.json", '{"dates":[{"date":"2026-11-13"},{"date":"2026-11-10"}],'
                                      '"latestDate":"2026-11-13","totalDates":2}')
            write(tmp / ".archivo.json", '{"dias":["2026-11-10","2026-11-13"]}')
            self.assertEqual(len(retirar(tmp, ["2026-11-10"])), 3)
            self.assertFalse((tmp / "2026-11-10").exists())
            idx = json.loads((tmp / "index.json").read_text())
            self.assertEqual((idx["totalDates"], idx["latestDate"]), (1, "2026-11-13"))
            self.assertEqual(json.loads((tmp / ".archivo.json").read_text())["dias"], ["2026-11-13"])
            self.assertEqual(retirar(tmp, ["2026-11-10"]), [])
        finally:
            shutil.rmtree(tmp)
