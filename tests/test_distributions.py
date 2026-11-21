"""Release artifacts must keep the source, version and bytes qualified by CI."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/distributions.py"
spec = importlib.util.spec_from_file_location("distributions", SCRIPT)
distributions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distributions)


class Distributions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        version = distributions.package_version()
        self.names = [f"vscode_hpc-{version}-py3-none-any.whl",
                      f"vscode_hpc-{version}.tar.gz", f"vscode-hpc-{version}-py_0.conda"]
        for name in self.names:
            (self.directory / name).write_bytes(name.encode())
        self.source = "a" * 40

    def run_script(self, command, source=None, extra=()):
        return subprocess.run(
            [sys.executable, str(SCRIPT), command, "--directory", str(self.directory),
             "--source", source or self.source, *extra], capture_output=True, text=True,
        )

    def test_record_and_verify_exact_bundle(self):
        self.assertEqual(self.run_script("record").returncode, 0)
        self.assertEqual(self.run_script("verify").returncode, 0)
        data = json.loads((self.directory / "manifest.json").read_text())
        self.assertEqual(data["source"], self.source)
        self.assertEqual(set(data["sha256"]), set(self.names))

    def test_changed_bytes_rejected(self):
        self.run_script("record")
        (self.directory / self.names[0]).write_bytes(b"replacement")
        self.assertNotEqual(self.run_script("verify").returncode, 0)

    def test_changed_source_rejected(self):
        self.run_script("record")
        self.assertNotEqual(self.run_script("verify", source="b" * 40).returncode, 0)

    def test_mismatched_tag_rejected(self):
        self.run_script("record")
        self.assertNotEqual(self.run_script("verify", extra=("--tag", "v99.0.0")).returncode, 0)

    def test_extra_artifact_rejected(self):
        (self.directory / "unexpected.whl").write_bytes(b"extra")
        self.assertNotEqual(self.run_script("record").returncode, 0)

    def test_missing_artifact_rejected(self):
        (self.directory / self.names[0]).unlink()
        self.assertNotEqual(self.run_script("record").returncode, 0)

    def test_existing_manifest_not_overwritten(self):
        self.run_script("record")
        self.assertNotEqual(self.run_script("record").returncode, 0)

    def test_invalid_source_rejected(self):
        self.assertNotEqual(self.run_script("record", source="master").returncode, 0)
