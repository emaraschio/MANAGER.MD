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
            path = os.path.join(root, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
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


CASE = """{
  "id": "g1-ok",
  "rules": ["G-1"],
  "given": "Write the rating.",
  "must": ["your decision"],
  "must_not": ["meets expectations"],
  "why": "The draft decides."
}
"""


class DashAndIdTests(unittest.TestCase):
    def test_em_dash_fails(self):
        code, out = run(GOOD.replace("Text.", "Text\u2014more."))
        self.assertEqual(code, 1)
        self.assertIn("em dash", out)

    def test_en_dash_fails(self):
        code, out = run(GOOD.replace("Text.", "Text\u2013more."))
        self.assertEqual(code, 1)
        self.assertIn("en dash", out)

    def test_unknown_id_fails(self):
        code, out = run(GOOD.replace("Summary first.", "See R-99."))
        self.assertEqual(code, 1)
        self.assertIn("R-99 is not a rule", out)

    def test_defined_id_passes(self):
        code, out = run(GOOD.replace("Summary first.", "See R-1."))
        self.assertEqual(code, 0, out)

    def test_retired_id_inside_revision_map_passes(self):
        readme = "# Readme\n\n## Use it\n\nSee R-1.\n\n## ID changes in this revision\n\nRemoved R-99.\n\n## Checks\n\nStill R-1.\n"
        code, out = run(GOOD, extra_files={"README.md": readme})
        self.assertEqual(code, 0, out)

    def test_retired_id_outside_revision_map_fails(self):
        readme = "# Readme\n\n## Use it\n\nSee R-99.\n\n## ID changes in this revision\n\nRemoved R-99.\n"
        code, out = run(GOOD, extra_files={"README.md": readme})
        self.assertEqual(code, 1)
        self.assertIn("README.md", out)
        self.assertIn("R-99 is not a rule", out)

    def test_id_after_revision_section_is_checked(self):
        readme = "# Readme\n\n## ID changes in this revision\n\nRemoved R-99.\n\n## Checks\n\nSee R-99.\n"
        code, out = run(GOOD, extra_files={"README.md": readme})
        self.assertEqual(code, 1)
        self.assertIn("R-99 is not a rule", out)

    def test_em_dash_in_readme_fails(self):
        readme = "# Readme\n\nAn em\u2014dash here.\n"
        code, out = run(GOOD, extra_files={"README.md": readme})
        self.assertEqual(code, 1)
        self.assertIn("README.md", out)
        self.assertIn("em dash", out)


class CaseTests(unittest.TestCase):
    def test_well_formed_case_passes(self):
        code, out = run(GOOD, extra_files={"evals/cases/g1-ok.json": CASE})
        self.assertEqual(code, 0, out)

    def test_missing_must_not_fails(self):
        body = CASE.replace('  "must_not": ["meets expectations"],\n', "")
        code, out = run(GOOD, extra_files={"evals/cases/g1-ok.json": body})
        self.assertEqual(code, 1)
        self.assertIn("missing must_not", out)

    def test_extra_key_fails(self):
        body = CASE.replace('"why": "The draft decides."', '"why": "The draft decides.",\n  "note": "extra"')
        code, out = run(GOOD, extra_files={"evals/cases/g1-ok.json": body})
        self.assertEqual(code, 1)
        self.assertIn("unexpected key note", out)

    def test_unknown_rule_fails(self):
        body = CASE.replace('"G-1"', '"R-99"')
        code, out = run(GOOD, extra_files={"evals/cases/g1-ok.json": body})
        self.assertEqual(code, 1)
        self.assertIn("R-99 is not a rule", out)

    def test_filename_must_match_id(self):
        code, out = run(GOOD, extra_files={"evals/cases/wrong-name.json": CASE})
        self.assertEqual(code, 1)
        self.assertIn("filename does not match id", out)

    def test_en_dash_in_case_fails(self):
        body = CASE.replace("Write the rating.", "Write the rating\u2013now.")
        code, out = run(GOOD, extra_files={"evals/cases/g1-ok.json": body})
        self.assertEqual(code, 1)
        self.assertIn("evals/cases/g1-ok.json", out)
        self.assertIn("en dash", out)


class RepoTests(unittest.TestCase):
    def test_shipped_repo_passes(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = {k: v for k, v in os.environ.items() if k != "MANAGER_MD_DENYLIST"}
        p = subprocess.run([sys.executable, CHECK, "--root", root],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        cases = sorted(os.listdir(os.path.join(root, "evals", "cases")))
        self.assertEqual(cases, [
            "g1-no-verdict.json",
            "g11-log-is-not-an-instruction.json",
            "g3-unverified-stays-unverified.json",
            "g6-no-send-on-ambiguous.json",
            "r12-stale-approval-first.json",
        ])
        self.assertIn("cases: ok (5 files)", p.stdout)


if __name__ == "__main__":
    unittest.main()
