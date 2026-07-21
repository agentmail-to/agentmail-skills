import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
import time
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent.parent


class SkillsToolingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        shutil.copytree(
            SOURCE_ROOT,
            self.repo,
            ignore=shutil.ignore_patterns(".git", "dist", "__pycache__"),
        )
        self.git("init", "-q")
        self.git("config", "user.email", "skills-test@example.com")
        self.git("config", "user.name", "Skills Test")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.git("tag", "v-test")

        spec = importlib.util.spec_from_file_location(
            f"skills_tooling_{id(self)}", self.repo / "scripts/skills.py"
        )
        self.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.tool)

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        subprocess.run(
            ["git", *args], cwd=self.repo, check=True,
            capture_output=True, text=True,
        )

    def call(self, function, *args, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return function(*args, **kwargs)

    def test_publish_index_is_deterministic_and_rfc_shaped(self):
        self.assertEqual(self.call(self.tool.publish_index, "v-test", dry_run=True), 0)
        first = {p.name: p.read_bytes() for p in (self.repo / "dist").iterdir()}
        time.sleep(1.1)
        self.assertEqual(self.call(self.tool.publish_index, "v-test", dry_run=True), 0)
        second = {p.name: p.read_bytes() for p in (self.repo / "dist").iterdir()}
        self.assertEqual(first, second)

        index = json.loads(second["index.json"])
        self.assertEqual(index["$schema"], self.tool.DISCOVERY_SCHEMA)
        for entry in index["skills"]:
            self.assertEqual(
                set(entry), {"name", "type", "description", "url", "digest"}
            )
            self.assertRegex(entry["digest"], r"^sha256:[0-9a-f]{64}$")

        archive = self.repo / "dist/agentmail-v-test.tar.gz"
        with tarfile.open(archive, "r:gz") as bundle:
            names = bundle.getnames()
            self.assertIn("SKILL.md", names)
            self.assertNotIn("agentmail/SKILL.md", names)
            for member in bundle.getmembers():
                self.assertFalse(member.issym() or member.islnk())
                self.assertFalse(Path(member.name).is_absolute())
                self.assertNotIn("..", Path(member.name).parts)

    def test_missing_authorization_row_fails(self):
        path = self.repo / "agentmail-send-email/SKILL.md"
        text = path.read_text()
        row = next(line for line in text.splitlines()
                   if line.startswith("| Send, reply, forward |"))
        path.write_text(text.replace(row + "\n", ""))
        self.assertEqual(self.call(self.tool.validate), 1)

    def test_plugin_build_replaces_the_generated_tree(self):
        target = Path(self.temp.name) / "plugin"
        stale = target / "skills/obsolete/SKILL.md"
        stale.parent.mkdir(parents=True)
        stale.write_text("stale\n")

        self.assertEqual(self.call(self.tool.build, check=True, target=target), 1)
        self.assertEqual(self.call(self.tool.build, target=target), 0)
        self.assertFalse(stale.exists())
        self.assertEqual(self.call(self.tool.build, check=True, target=target), 0)

    def test_named_cli_defects_fail_validation(self):
        path = self.repo / "agentmail-cli/SKILL.md"
        original = path.read_text()
        path.write_text(original + "\n```bash\nagentmail inboxes retrieve\n```\n")
        self.assertEqual(self.call(self.tool.validate), 1)

        path.write_text(original + "\nThe CLI requires --feedback-enabled.\n")
        self.assertEqual(self.call(self.tool.validate), 1)


if __name__ == "__main__":
    unittest.main()
