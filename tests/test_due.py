import json
from datetime import datetime

from gate import manifest
from publisher.due import due_items
from tests.test_rules import item

NOW = datetime.fromisoformat("2026-11-09T09:20:00+05:30")


def _setup(tmp_path, it, approve=True, approved_item=None):
    day = tmp_path / "content" / "2026-11-09"
    day.mkdir(parents=True)
    (day / f"{it['id']}.json").write_text(json.dumps(it))
    (tmp_path / "approved").mkdir()
    if approve:
        h = manifest.item_hash(approved_item or it)
        (tmp_path / "approved" / "2026-11-09.json").write_text(
            json.dumps({"date": "2026-11-09", "items": {it["id"]: h}}))


def test_approved_due_item_is_ready(tmp_path):
    _setup(tmp_path, item())
    ready, refused = due_items(tmp_path, NOW)
    assert [i["id"] for i in ready] == ["2026-11-09-li-01"] and refused == []


def test_unapproved_item_is_refused(tmp_path):
    _setup(tmp_path, item(), approve=False)
    ready, refused = due_items(tmp_path, NOW)
    assert ready == [] and refused


def test_item_edited_after_merge_is_refused(tmp_path):
    _setup(tmp_path, item(body="Edited on main after review."), approved_item=item())
    ready, refused = due_items(tmp_path, NOW)
    assert ready == [] and "hash" in refused[0]


def test_item_failing_gate_is_refused_even_if_approved(tmp_path):
    _setup(tmp_path, item(body="Only ₹999 today."))
    ready, refused = due_items(tmp_path, NOW)
    assert ready == [] and "gate" in refused[0]


def test_future_item_is_not_due(tmp_path):
    _setup(tmp_path, item(slot_ist="2026-11-09T18:00:00+05:30"))
    assert due_items(tmp_path, NOW) == ([], [])


def test_stale_item_is_not_due(tmp_path):
    _setup(tmp_path, item(slot_ist="2026-11-09T08:00:00+05:30"))
    assert due_items(tmp_path, NOW) == ([], [])
