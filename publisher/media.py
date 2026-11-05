"""Media goes to a public bucket under a content-hash name.

The name is the file's sha256, so the same bytes always land at the same URL,
a changed file gets a new URL, and nothing is ever overwritten. That is why the
uploader needs only create rights (roles/storage.objectCreator).

python -m publisher.media plan   ->  one "<local path> <gs:// destination>" line per file
"""
import hashlib
import sys
from pathlib import Path

BUCKET = "polystratum-content-media"
PUBLIC_BASE = f"https://storage.googleapis.com/{BUCKET}/"
MEDIA_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".pdf", ".mp3", ".wav"}


def object_name(path: Path) -> str:
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return digest + Path(path).suffix.lower()


def public_url(path: Path) -> str:
    return PUBLIC_BASE + object_name(path)


def plan(media_root: Path) -> list[tuple[Path, str]]:
    files = [p for p in sorted(Path(media_root).rglob("*"))
             if p.is_file() and p.suffix.lower() in MEDIA_TYPES]
    return [(p, f"gs://{BUCKET}/{object_name(p)}") for p in files]


def main(argv: list[str]) -> int:
    if argv != ["plan"]:
        print(__doc__)
        return 2
    for src, dest in plan(Path.cwd() / "media"):
        print(f"{src.relative_to(Path.cwd())} {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
