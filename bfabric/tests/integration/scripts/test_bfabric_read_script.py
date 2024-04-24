import inspect
import pathlib
import subprocess
import unittest
from unittest.mock import patch

import bfabric


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
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )

    def test_read_project_by_id(self):
        res = self.execute_script("project", "id", "3000")
        self.assertEqual(0, res.returncode)
        self.assertIn("query = {'id': '3000'}", res.stdout)
        self.assertIn(
            "Internal project for prototyping and testing. replacement of p1000.",
            res.stdout,
        )

    def test_read_project_without_filter(self):
        res = self.execute_script("project")
        self.assertEqual(0, res.returncode)
        self.assertIn("query = {}", res.stdout)
        self.assertIn("number of query result items = 100", res.stdout)

    def test_read_bad_endpoint(self):
        res = self.execute_script("bad_endpoint")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("endpoint: invalid choice", res.stdout)


if __name__ == "__main__":
    unittest.main()
