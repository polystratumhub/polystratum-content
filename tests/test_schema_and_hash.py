import copy
import json

import pytest

from gate import manifest, schema
from tests.test_rules import item


def test_valid_item_matches_schema():
    assert schema.validate(item()) == []


@pytest.mark.parametrize("field", ["id", "platform", "slot_ist", "format", "kind", "body",
                                   "ai_generated", "ai_label", "sources", "media"])
def test_missing_required_field_fails(field):
    it = item()
    del it[field]
    assert schema.validate(it) != []


def test_unknown_platform_fails():
    assert schema.validate(item(platform="x")) != []


def test_unknown_field_fails():
    assert schema.validate(item(extra="nope")) != []


def test_hash_is_stable_under_key_order():
    a = item()
    b = dict(reversed(list(copy.deepcopy(a).items())))
    assert manifest.item_hash(a) == manifest.item_hash(b)


def test_hash_changes_when_body_changes():
    assert manifest.item_hash(item()) != manifest.item_hash(item(body="Different."))


def _write(tmp_path, it):
    day = tmp_path / "content" / it["slot_ist"][:10]
    day.mkdir(parents=True, exist_ok=True)
    (day / f"{it['id']}.json").write_text(json.dumps(it))
    return day


def test_manifest_round_trip(tmp_path):
    day = _write(tmp_path, item())
    m = manifest.build(day)
    assert manifest.verify(day, m) == []


def test_edit_after_approval_is_caught(tmp_path):
    day = _write(tmp_path, item())
    m = manifest.build(day)
    _write(tmp_path, item(body="Changed after review."))
    problems = manifest.verify(day, m)
    assert problems and "hash" in problems[0]


def test_item_added_after_approval_is_caught(tmp_path):
    day = _write(tmp_path, item())
    m = manifest.build(day)
    _write(tmp_path, item(id="2026-11-09-li-02"))
    assert any("not in manifest" in p for p in manifest.verify(day, m))


def test_item_removed_after_approval_is_caught(tmp_path):
    day = _write(tmp_path, item())
    _write(tmp_path, item(id="2026-11-09-li-02"))
    m = manifest.build(day)
    (day / "2026-11-09-li-02.json").unlink()
    assert any("missing" in p for p in manifest.verify(day, m))
