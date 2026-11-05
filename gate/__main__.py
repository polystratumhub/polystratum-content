"""python -m gate check | manifest <day-dir> | verify

check     schema + brand rules on every item under content/
manifest  write approved/<date>.json for one day (run by the drafting agent in its PR)
verify    every content day has a manifest, and every hash matches
"""
import json
import sys
from pathlib import Path

from gate import manifest, rules, schema

ROOT = Path.cwd()
CONTENT = ROOT / "content"
APPROVED = ROOT / "approved"


def _day_dirs():
    return sorted(p for p in CONTENT.glob("????-??-??") if p.is_dir())


def cmd_check() -> int:
    failures = 0
    for path in sorted(CONTENT.glob("????-??-??/*.json")):
        item = json.loads(path.read_text())
        problems = [f"schema: {m}" for m in schema.validate(item)]
        problems += [f"{v.rule}: {v.message}" for v in rules.check(item)]
        if path.stem != item.get("id"):
            problems.append("file name must equal the item id")
        for m in item.get("media", []):
            if not (ROOT / m["path"]).exists():
                problems.append(f"media file missing: {m['path']}")
        for p in problems:
            print(f"FAIL {path.relative_to(ROOT)} | {p}")
        failures += bool(problems)
    print(f"gate check: {failures} item(s) failed")
    return 1 if failures else 0


def cmd_manifest(day: str) -> int:
    day_dir = Path(day)
    APPROVED.mkdir(exist_ok=True)
    out = APPROVED / f"{day_dir.name}.json"
    out.write_text(json.dumps(manifest.build(day_dir), indent=2, sort_keys=True) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


def cmd_verify() -> int:
    problems = []
    for day_dir in _day_dirs():
        m_path = APPROVED / f"{day_dir.name}.json"
        if not m_path.exists():
            problems.append(f"{day_dir.name}: no approved manifest")
            continue
        problems += [f"{day_dir.name}: {p}" for p in manifest.verify(day_dir, json.loads(m_path.read_text()))]
    for p in problems:
        print(f"FAIL {p}")
    print(f"gate verify: {len(problems)} problem(s)")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "check":
        return cmd_check()
    if argv[0] == "manifest" and len(argv) == 2:
        return cmd_manifest(argv[1])
    if argv[0] == "verify":
        return cmd_verify()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
