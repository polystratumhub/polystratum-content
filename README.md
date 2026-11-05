# polystratum-content

The content pipeline for Polystratum Marketer v1. Private.

## How it works

1. **Every night** a Claude scheduled task researches, drafts and checks the next day's posts. It opens **one pull request** with one JSON file per post under `content/<date>/`, the media under `media/`, and an approval manifest under `approved/<date>.json`.
2. **You review the PR** on the GitHub app. **Merging is the approval.** Nothing else publishes.
3. **The `gate` check** runs on every PR: tests, brand and safety rules, and the approval hashes. A red check blocks the merge.
4. **At each slot** the publisher takes only items that are due, still pass the gate, and match the hash you merged. An edit made after your merge is refused.

## The gate rules

| Rule | Blocks |
|---|---|
| `no_price` | ₹, Rs, INR, "free session", discounts |
| `northern_trust_past_tense` | Any Northern Trust mention that is not past employment; any Northern Trust asset |
| `no_cohort_or_scarcity` | Cohort selling, enrolment, "seats left", "filling fast" |
| `stat_needs_source` | A percentage, multiple or study claim without an https source |
| `no_personal_data` | Any email but KV's own; any phone number |
| `ai_label` | Synthetic voice, video or likeness without the AI label |
| `platform_limits` | Over-length posts; more than 3 hashtags |
| `no_retired_name` | "Cognix" |
| `ai_tells` | leverage, elevate, unlock, "Here's how", "It's not X, it's Y" and similar |
| `format_and_slot` | A format the platform cannot take; a slot not in IST; an id that does not match |
| `link_allowlist` | Non-https links and links outside polystratum.com, linkedin.com, github.com |

Every rule has a test that must fail and one that must pass. Disabling any rule turns the suite red.

## Commands

```
pip install -r requirements.txt
python -m pytest -q
python -m gate check
python -m gate manifest content/2026-11-09
python -m gate verify
python -m publisher.due
```

## Item format

See `schema/item.schema.json`. One post per file; the file name is the item id, e.g. `content/2026-11-09/2026-11-09-li-01.json`.
