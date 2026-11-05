"""The approval hash.

At review time the PR carries approved/<date>.json: one sha256 per item.
CI checks the manifest matches the files, so what KV merged is what ships.
At slot time the publisher re-hashes the item and refuses a mismatch.
"""
import hashlib
import json
from pathlib import Path


def item_hash(item: dict) -> str:
    canonical = json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _items(day_dir: Path) -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in sorted(Path(day_dir).glob("*.json"))}


def build(day_dir: Path) -> dict:
    day_dir = Path(day_dir)
    return {"date": day_dir.name,
            "items": {i: item_hash(it) for i, it in _items(day_dir).items()}}


def verify(day_dir: Path, manifest: dict) -> list[str]:
    problems = []
    current = _items(day_dir)
    approved = manifest.get("items", {})
    for item_id, it in current.items():
        if item_id not in approved:
            problems.append(f"{item_id}: not in manifest")
        elif item_hash(it) != approved[item_id]:
            problems.append(f"{item_id}: hash differs from the approved manifest")
    for item_id in approved:
        if item_id not in current:
            problems.append(f"{item_id}: in manifest but file missing")
    return problems
