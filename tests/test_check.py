"""Drive scripts/check.py through its CLI, the boundary CI and the hooks use."""
import os
import subprocess
import sys
import tempfile
import unittest

CHECK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "check.py")

GOOD = """# MANAGER.md

## Stance
Text.

## Guardrails
- **G-1. First guardrail.** Do it. *Why:* reasons.

## Operating rules
- **R-1. First rule.** Do it. *Why:* reasons.
- **R-2. Second rule.** Do it. *Why:* reasons.

## Your context
Fill in.

## Output
Summary first.
"""


def run(manager_text, *args, extra_files=None):
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "MANAGER.md"), "w") as f:
            f.write(manager_text)
        for name, body in (extra_files or {}).items():
            with open(os.path.join(root, name), "w") as f:
                f.write(body)
        resolved = [a.replace("{root}", root) for a in args]
        env = {k: v for k, v in os.environ.items() if k != "MANAGER_MD_DENYLIST"}
        p = subprocess.run([sys.executable, CHECK, "--root", root, *resolved],
                           capture_output=True, text=True, env=env)
        return p.returncode, p.stdout


class FormatTests(unittest.TestCase):
    def test_good_file_passes(self):
        code, out = run(GOOD)
        self.assertEqual(code, 0, out)
        self.assertIn("deny-list: NOT PROVIDED (unverified)", out)

    def test_missing_why_fails(self):
        code, out = run(GOOD.replace("- **R-2. Second rule.** Do it. *Why:* reasons.",
                                     "- **R-2. Second rule.** Do it."))
        self.assertEqual(code, 1)
        self.assertIn("R-2 has no *Why:*", out)

    def test_duplicate_id_fails(self):
        code, out = run(GOOD.replace("R-2. Second", "R-1. Second"))
        self.assertEqual(code, 1)
        self.assertIn("duplicate R-1", out)

    def test_missing_section_fails(self):
        code, out = run(GOOD.replace("## Stance", "## Attitude"))
        self.assertEqual(code, 1)
        self.assertIn("missing section '## Stance'", out)


class LeakTests(unittest.TestCase):
    def test_denylist_term_fails_without_printing_it(self):
        code, out = run(GOOD + "\nZorbex owns this.\n", "--denylist", "{root}/deny.txt",
                        extra_files={"deny.txt": "# private\nZorbex\n"})
        # deny.txt sits inside the temp root here, so it also matches itself; the
        # MANAGER.md hit is what this test is about.
        self.assertEqual(code, 1)
        self.assertIn("MANAGER.md", out)
        self.assertIn("term #1", out)
        self.assertNotIn("Zorbex", out)

    def test_near_miss_inside_longer_word_passes(self):
        with tempfile.TemporaryDirectory() as d:
            deny = os.path.join(d, "deny.txt")
            with open(deny, "w") as f:
                f.write("Orin\n")
            code, out = run(GOOD + "\nThe Orinoco and Corinth.\n", "--denylist", deny)
            self.assertEqual(code, 0, out)
            code, out = run(GOOD + "\nAsk Orin.\n", "--denylist", deny)
            self.assertEqual(code, 1, out)

    def test_require_denylist_without_one_fails(self):
        code, out = run(GOOD, "--require-denylist")
        self.assertEqual(code, 2)

    def test_empty_denylist_is_an_error_not_a_pass(self):
        with tempfile.TemporaryDirectory() as d:
            deny = os.path.join(d, "deny.txt")
            open(deny, "w").close()
            code, _ = run(GOOD, "--denylist", deny)
            self.assertEqual(code, 2)

    def test_secret_shape_fails(self):
        token = "ghp" + "_" + "a" * 30
        code, out = run(GOOD + f"\ntoken {token}\n")
        self.assertEqual(code, 1)
        self.assertIn("looks like a secret", out)


if __name__ == "__main__":
    unittest.main()
