"""The auto-updater against throwaway local repos (needs git)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from hearth import config, updater


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class UpdaterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        origin, dev, self.box = self.tmp / "origin.git", self.tmp / "dev", self.tmp / "box"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
        subprocess.run(["git", "clone", "-q", str(origin), str(dev)], check=True, capture_output=True)
        (dev / "a.txt").write_text("v1")
        git(dev, "add", "-A"); git(dev, "commit", "-q", "-m", "v1"); git(dev, "push", "-q", "origin", "HEAD:main")
        subprocess.run(["git", "clone", "-q", str(origin), str(self.box)], check=True, capture_output=True)
        self.dev = dev
        self._root, config.ROOT = config.ROOT, self.box

    def tearDown(self):
        config.ROOT = self._root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def push(self, text):
        (self.dev / "a.txt").write_text(text)
        git(self.dev, "commit", "-q", "-am", text); git(self.dev, "push", "-q", "origin", "HEAD:main")

    def test_pulls_new_commits(self):
        self.assertTrue(updater.is_git_checkout())
        self.assertFalse(updater.check_once())              # nothing new yet
        self.push("v2")
        self.assertTrue(updater.check_once())
        self.assertEqual((self.box / "a.txt").read_text(), "v2")

    def test_keeps_local_edits(self):
        self.push("v2")
        (self.box / "a.txt").write_text("my edit")
        self.assertFalse(updater.check_once())
        self.assertEqual((self.box / "a.txt").read_text(), "my edit")


if __name__ == "__main__":
    unittest.main()
