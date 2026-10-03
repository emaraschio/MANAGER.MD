#!/usr/bin/env python3
"""Checks for MANAGER.md: rule format, live IDs, eval cases, plus a leak scan.

Usage:
  python3 scripts/check.py                      # format, dashes, ids, cases, shapes
  python3 scripts/check.py --denylist PATH      # also scan for private terms
  python3 scripts/check.py --require-denylist   # fail if no deny-list is given

The deny-list (one term per line, `#` comments) is the adopter's private list of
names that must never be published: people, handles, company, internal repos.
Keep it OUTSIDE this repo. Terms match whole-word and case-sensitively, so a
false positive fails safe. Hits print the term's index, never the term, so CI
logs cannot leak it.

Exit codes: 0 ok, 1 finding, 2 usage error or missing input.
"""
import argparse
import json
import os
import re
import sys

MAX_LINES = 300
MAX_WORDS = 4000
REQUIRED_SECTIONS = ["Stance", "Guardrails", "Operating rules", "Your context", "Output"]
SKIP_DIRS = {".git", "__pycache__"}

RULE_RE = re.compile(r"^- \*\*([GR])-(\d+)\. ([^*]+?)\*\*(.*)$")
RULE_LIKE_RE = re.compile(r"\*\*[GR]-\d+")
ID_RE = re.compile(r"\b([GR]-\d+)\b")
CASE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CASE_KEYS = {"id", "rules", "given", "must", "must_not", "why"}
REVISION_HEADING = "## ID changes in this revision"
DASHES = {"\u2014": "em dash", "\u2013": "en dash"}

# Shapes ported from a private redactor. Dates are deliberately absent: they
# would flag every dated line.
SHAPES = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "phone": r"(?<![0-9A-Za-z])(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?![0-9A-Za-z])",
    "secret": "|".join([
        r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{10,}",
        r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}",
        r"\bAKIA[0-9A-Z]{16}\b",
        r"\bAIza[0-9A-Za-z_\-]{35}\b",
        r"\bxox[baprs]-[A-Za-z0-9-]{10,}",
        r"https://[0-9a-f]{16,}@[\w.-]+/\d+",
    ]),
}
SHAPES = {k: re.compile(v) for k, v in SHAPES.items()}


def check_format(path):
    """Return (errors, summary) for the MANAGER.md at path."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    errors = []

    headings = [l[3:].strip() for l in lines if l.startswith("## ")]
    for section in REQUIRED_SECTIONS:
        if not any(h.startswith(section) for h in headings):
            errors.append(f"missing section '## {section}'")

    seen = {"G": [], "R": []}
    for n, line in enumerate(lines, 1):
        m = RULE_RE.match(line)
        if m:
            prefix, num, _title, rest = m.group(1), int(m.group(2)), m.group(3), m.group(4)
            if num in seen[prefix]:
                errors.append(f"line {n}: duplicate {prefix}-{num}")
            seen[prefix].append(num)
            if "*Why:*" not in rest:
                errors.append(f"line {n}: {prefix}-{num} has no *Why:*")
        elif RULE_LIKE_RE.search(line):
            errors.append(f"line {n}: malformed rule line")

    for prefix, nums in seen.items():
        if not nums:
            errors.append(f"no {prefix}- rules found")
        elif nums != list(range(1, len(nums) + 1)):
            errors.append(f"{prefix}- rules are not numbered 1..{len(nums)} in order")

    words = len(text.split())
    if len(lines) > MAX_LINES:
        errors.append(f"{len(lines)} lines, cap is {MAX_LINES}")
    if words > MAX_WORDS:
        errors.append(f"{words} words, cap is {MAX_WORDS}")
    summary = f"G={len(seen['G'])} R={len(seen['R'])} lines={len(lines)} words={words}"
    return errors, summary


def defined_ids(text):
    found = set()
    for line in text.splitlines():
        m = RULE_RE.match(line)
        if m:
            found.add(f"{m.group(1)}-{int(m.group(2))}")
    return found


def find_dashes(rel, lines):
    hits = []
    for n, line in enumerate(lines, 1):
        for char, name in DASHES.items():
            if char in line:
                hits.append(f"{rel}:{n}: {name}")
    return hits


def find_bad_ids(rel, lines, defined, skip_revision=False):
    hits = []
    skipping = False
    for n, line in enumerate(lines, 1):
        if skip_revision and line.startswith("## "):
            skipping = line.strip() == REVISION_HEADING
        if skipping:
            continue
        for token in ID_RE.findall(line):
            if token not in defined:
                hits.append(f"{rel}:{n}: {token} is not a rule")
    return hits


def _string_list(value):
    return isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value)


def check_cases(root, defined):
    """Return (errors, count) for evals/cases/*.json. Missing dir is zero cases, not a failure."""
    case_dir = os.path.join(root, "evals", "cases")
    if not os.path.isdir(case_dir):
        return [], 0
    errors = []
    count = 0
    for name in sorted(os.listdir(case_dir)):
        rel = f"evals/cases/{name}"
        path = os.path.join(case_dir, name)
        if not name.endswith(".json") or not os.path.isfile(path):
            errors.append(f"{rel}: expected a json file")
            continue
        count += 1
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        errors.extend(find_dashes(rel, raw.splitlines()))
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            errors.append(f"{rel}: invalid json ({e.msg})")
            continue
        if not isinstance(data, dict):
            errors.append(f"{rel}: expected an object")
            continue
        for key in sorted(CASE_KEYS - set(data)):
            errors.append(f"{rel}: missing {key}")
        for key in sorted(set(data) - CASE_KEYS):
            errors.append(f"{rel}: unexpected key {key}")
        case_id = data.get("id")
        if not isinstance(case_id, str) or not CASE_ID_RE.match(case_id or ""):
            errors.append(f"{rel}: id must be lowercase hyphenated words")
        elif name != case_id + ".json":
            errors.append(f"{rel}: filename does not match id")
        rules = data.get("rules")
        if not isinstance(rules, list) or not rules:
            errors.append(f"{rel}: rules must be a non-empty list")
        else:
            for rule in rules:
                if not isinstance(rule, str) or not ID_RE.fullmatch(rule):
                    errors.append(f"{rel}: bad rule token")
                elif rule not in defined:
                    errors.append(f"{rel}: {rule} is not a rule")
        if not isinstance(data.get("given"), str) or not str(data.get("given", "")).strip():
            errors.append(f"{rel}: given must be a non-empty string")
        if not isinstance(data.get("why"), str) or not str(data.get("why", "")).strip():
            errors.append(f"{rel}: why must be a non-empty string")
        for key in ("must", "must_not"):
            if key in data and not _string_list(data.get(key)):
                errors.append(f"{rel}: {key} must be a non-empty list of strings")
    return errors, count


def text_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8") as f:
                    yield os.path.relpath(path, root), f.read().splitlines()
            except (UnicodeDecodeError, OSError):
                continue


def load_denylist(path):
    with open(path, encoding="utf-8") as f:
        terms = [t.strip() for t in f if t.strip() and not t.strip().startswith("#")]
    return [re.compile(r"(?<![A-Za-z0-9_])" + re.escape(t) + r"(?![A-Za-z0-9_])") for t in terms]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p.add_argument("--manager", default=None, help="path to MANAGER.md (default: ROOT/MANAGER.md)")
    p.add_argument("--denylist", default=os.environ.get("MANAGER_MD_DENYLIST"))
    p.add_argument("--require-denylist", action="store_true")
    args = p.parse_args(argv)

    manager = args.manager or os.path.join(args.root, "MANAGER.md")
    if not os.path.isfile(manager):
        print(f"error: {manager} not found")
        return 2

    terms = None
    if args.denylist:
        try:
            terms = load_denylist(args.denylist)
        except OSError as e:
            print(f"error: cannot read deny-list: {e.strerror}")
            return 2
        if not terms:
            print("error: deny-list is empty, refusing to report it as passed")
            return 2
    elif args.require_denylist:
        print("error: --require-denylist set but no deny-list given (--denylist or MANAGER_MD_DENYLIST)")
        return 2

    findings = 0
    errors, summary = check_format(manager)
    for e in errors:
        print(f"format: {e}")
    findings += len(errors)
    print(f"format: {'FAIL' if errors else 'ok'} ({summary})")

    with open(manager, encoding="utf-8") as f:
        manager_text = f.read()
    defined = defined_ids(manager_text)
    manager_lines = manager_text.splitlines()

    dash_hits = find_dashes("MANAGER.md", manager_lines)
    id_hits = find_bad_ids("MANAGER.md", manager_lines, defined)
    readme = os.path.join(args.root, "README.md")
    if os.path.isfile(readme):
        with open(readme, encoding="utf-8") as f:
            readme_lines = f.read().splitlines()
        dash_hits.extend(find_dashes("README.md", readme_lines))
        id_hits.extend(find_bad_ids("README.md", readme_lines, defined, skip_revision=True))
    for hit in dash_hits:
        print(f"dash: {hit}")
    findings += len(dash_hits)
    print(f"dashes: {'FAIL' if dash_hits else 'ok'}")
    for hit in id_hits:
        print(f"id: {hit}")
    findings += len(id_hits)
    print(f"ids: {'FAIL' if id_hits else 'ok'}")

    case_hits, case_count = check_cases(args.root, defined)
    for hit in case_hits:
        print(f"case: {hit}")
    findings += len(case_hits)
    print(f"cases: {'FAIL' if case_hits else 'ok'} ({case_count} files)")

    shape_hits = term_hits = scanned = 0
    for rel, lines in text_files(args.root):
        scanned += 1
        for n, line in enumerate(lines, 1):
            for kind, rx in SHAPES.items():
                if rx.search(line):
                    print(f"shape: {rel}:{n}: looks like a {kind}")
                    shape_hits += 1
            for i, rx in enumerate(terms or [], 1):
                if rx.search(line):
                    print(f"deny-list: {rel}:{n}: term #{i}")
                    term_hits += 1
    findings += shape_hits + term_hits
    print(f"shapes: {'FAIL' if shape_hits else 'ok'} ({scanned} files)")
    if terms is None:
        print("deny-list: NOT PROVIDED (unverified)")
    else:
        print(f"deny-list: {'FAIL' if term_hits else 'ok'} ({len(terms)} terms, {scanned} files)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
