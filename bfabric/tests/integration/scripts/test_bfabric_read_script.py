import inspect
import pathlib
import subprocess
import unittest
from unittest.mock import patch
import bfabric
import json


@patch.dict("os.environ", {"BFABRICPY_CONFIG_ENV": "TEST"})
class TestBfabricReadScript(unittest.TestCase):
    def setUp(self):
        root_dir = pathlib.Path(inspect.getfile(bfabric)).parent
        script_path = root_dir.joinpath("scripts", "bfabric_read.py")
        self.base_command = ["python", script_path]

    def execute_script(self, *args):
        command = self.base_command + list(args)
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )

    def test_read_project_by_id_to_json(self):
        for format in [("--format", "json"), ("--format", "auto"), ()]:
            with self.subTest(format=format):
                res = self.execute_script(*format, "project", "id", "3000")
                self.assertEqual(0, res.returncode)
                results = json.loads(res.stdout)
                self.assertEqual(1, len(results))
                self.assertIn("query = {'id': '3000'}", res.stderr)
                self.assertEqual(
                    "Internal project for prototyping and testing. replacement of p1000.",
                    results[0]["summary"],
                )

    def test_read_project_by_id_to_table(self):
        res = self.execute_script("--format", "table_tsv", "project", "id", "3000")
        self.assertEqual(0, res.returncode)
        lines = res.stdout.splitlines()
        self.assertEqual(1, len(lines))
        self.assertEqual(3, len(lines[0].split("\t")))

    def test_read_project_without_filter_to_json(self):
        res = self.execute_script("--format", "json", "project")
        self.assertEqual(0, res.returncode)
        results = json.loads(res.stdout)
        self.assertEqual(100, len(results))

    def test_read_project_without_filter_to_table(self):
        res = self.execute_script("--format", "table_tsv", "project")
        self.assertEqual(0, res.returncode)
        lines = res.stdout.splitlines()
        self.assertEqual(100, len(lines))
        self.assertEqual(3, len(lines[0].split("\t")))

    def test_read_bad_endpoint(self):
        res = self.execute_script("bad_endpoint")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("endpoint: invalid choice", res.stderr)


if __name__ == "__main__":
    unittest.main()
