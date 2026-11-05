"""Pick the items that are due now and still match their approved hash.

Phase 0 ships selection only; posting to LinkedIn and Meta lands in Phase 0 step 6.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gate import manifest, rules, schema

WINDOW = timedelta(minutes=20)


def due_items(root: Path, now: datetime) -> tuple[list[dict], list[str]]:
    """Return (ready items, refusals). An item is ready only if it is due,
    approved by hash, and still passes the gate."""
    ready, refused = [], []
    for day_dir in sorted((root / "content").glob("????-??-??")):
        m_path = root / "approved" / f"{day_dir.name}.json"
        approved = json.loads(m_path.read_text())["items"] if m_path.exists() else {}
        for path in sorted(day_dir.glob("*.json")):
            item = json.loads(path.read_text())
            slot = datetime.fromisoformat(item["slot_ist"])
            if not (now - WINDOW <= slot <= now):
                continue
            if approved.get(item["id"]) != manifest.item_hash(item):
                refused.append(f"{item['id']}: not approved at this hash")
            elif schema.validate(item) or rules.check(item):
                refused.append(f"{item['id']}: fails the gate")
            else:
                ready.append(item)
    return ready, refused


def main() -> int:
    ready, refused = due_items(Path.cwd(), datetime.now(timezone.utc))
    for r in refused:
        print(f"REFUSED {r}")
    for it in ready:
        print(f"DUE {it['id']} {it['platform']} {it['format']} (dry run: not posted)")
    print(f"{len(ready)} due, {len(refused)} refused")
    return 1 if refused else 0


if __name__ == "__main__":
    raise SystemExit(main())
