import hashlib

from publisher import media


def test_object_name_is_content_hash_plus_extension(tmp_path):
    f = tmp_path / "card.PNG"
    f.write_bytes(b"pixels")
    assert media.object_name(f) == hashlib.sha256(b"pixels").hexdigest() + ".png"


def test_same_bytes_same_name_different_bytes_different_name(tmp_path):
    a, b, c = tmp_path / "a.jpg", tmp_path / "b.jpg", tmp_path / "c.jpg"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    c.write_bytes(b"y")
    assert media.object_name(a) == media.object_name(b) != media.object_name(c)


def test_public_url_points_at_the_bucket(tmp_path):
    f = tmp_path / "a.mp4"
    f.write_bytes(b"v")
    assert media.public_url(f) == (
        "https://storage.googleapis.com/polystratum-content-media/" + media.object_name(f))


def test_plan_skips_placeholders_and_unknown_types(tmp_path):
    root = tmp_path / "media"
    (root / "sub").mkdir(parents=True)
    (root / ".gitkeep").write_text("")
    (root / "notes.txt").write_text("not media")
    (root / "sub" / "card.png").write_bytes(b"p")
    (root / "deck.pdf").write_bytes(b"d")
    plan = media.plan(root)
    assert sorted(p.name for p, _ in plan) == ["card.png", "deck.pdf"]
    assert all(dest.startswith("gs://polystratum-content-media/") for _, dest in plan)
