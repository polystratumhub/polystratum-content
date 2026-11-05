import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "item.schema.json"
_validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))


def validate(item: dict) -> list[str]:
    """Return one message per schema error; empty means valid."""
    return [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}"
            for e in sorted(_validator.iter_errors(item), key=lambda e: list(e.path))]
