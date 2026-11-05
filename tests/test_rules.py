"""Every gate rule gets a case that must FAIL and a case that must PASS.

A rule with no failing case has never been shown to bite (Agentic Build R20).
"""
import copy

import pytest

from gate import rules


def item(**overrides):
    base = {
        "id": "2026-11-09-li-01",
        "platform": "linkedin",
        "slot_ist": "2026-11-09T09:15:00+05:30",
        "format": "text",
        "kind": "subject",
        "body": "Most month-end closes still run on email and a spreadsheet. "
                "This week I mapped one and wrote down every hand-off.",
        "hashtags": [],
        "media": [],
        "sources": [],
        "ai_generated": False,
        "ai_label": False,
    }
    out = copy.deepcopy(base)
    out.update(overrides)
    return out


def names(violations):
    return {v.rule for v in violations}


def test_clean_item_passes():
    assert rules.check(item()) == []


# R1 price -----------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Join for ₹5,200 this weekend.",
    "Only Rs. 999 for the session.",
    "Fee is INR 9.",
    "Come to the free session on Friday.",
    "Get a 20% discount today.",
])
def test_price_fails(text):
    assert "no_price" in names(rules.check(item(body=text)))


def test_price_word_free_in_ordinary_use_passes():
    assert "no_price" not in names(rules.check(item(body="Feel free to reply with your process.")))


# R2 Northern Trust, past tense only -----------------------------------------

@pytest.mark.parametrize("text", [
    "I work at Northern Trust and build agents at night.",
    "In partnership with Northern Trust, we teach AI.",
    "Northern Trust trusts this method.",
])
def test_northern_trust_present_fails(text):
    assert "northern_trust_past_tense" in names(rules.check(item(body=text)))


@pytest.mark.parametrize("text", [
    "Former VP at Northern Trust.",
    "Ex-Northern Trust. Now I build agents.",
    "I spent nearly 17 years at Northern Trust before this.",
])
def test_northern_trust_past_passes(text):
    assert "northern_trust_past_tense" not in names(rules.check(item(body=text)))


def test_northern_trust_logo_fails():
    media = [{"path": "media/northern-trust-logo.png", "alt": "logo", "synthetic": False}]
    assert "northern_trust_past_tense" in names(rules.check(item(media=media)))


# R3 no cohort selling, no fake scarcity ------------------------------------

@pytest.mark.parametrize("text", [
    "Enrolment closes Friday.",
    "Enroll now for the next batch.",
    "Only 3 seats left!",
    "Seats are filling fast.",
    "Last chance to join.",
    "The next cohort starts in December.",
])
def test_cohort_and_scarcity_fail(text):
    assert "no_cohort_or_scarcity" in names(rules.check(item(body=text)))


def test_cohort_in_founder_story_passes():
    it = item(kind="founder_story", body="I cancelled the cohort. Here is what it cost me.")
    assert "no_cohort_or_scarcity" not in names(rules.check(it))


def test_real_capacity_line_passes():
    assert "no_cohort_or_scarcity" not in names(rules.check(item(body="7 people maximum.")))


# R4 statistics need a live source ------------------------------------------

@pytest.mark.parametrize("text", [
    "73% of hiring managers want AI skills.",
    "Agents cut processing time 4x.",
    "Research shows most pilots fail.",
    "A 2 crore market by next year.",
])
def test_unsourced_stat_fails(text):
    assert "stat_needs_source" in names(rules.check(item(body=text)))


def test_sourced_stat_passes():
    it = item(body="73% of hiring managers want AI skills.",
              sources=[{"claim": "73% of hiring managers", "url": "https://example.org/report"}])
    assert "stat_needs_source" not in names(rules.check(it))


def test_source_must_be_https():
    it = item(body="73% of hiring managers want AI skills.",
              sources=[{"claim": "73%", "url": "http://example.org/report"}])
    assert "stat_needs_source" in names(rules.check(it))


def test_allowed_own_figures_pass():
    text = "250+ students coached. Nearly 17 years in operations."
    assert "stat_needs_source" not in names(rules.check(item(body=text)))


# R5 no personal data -------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Thanks to someone@gmail.com for the idea.",
    "Call me on +91 98765 43210.",
    "WhatsApp 9876543210 for details.",
])
def test_pii_fails(text):
    assert "no_personal_data" in names(rules.check(item(body=text)))


def test_own_business_email_passes():
    assert "no_personal_data" not in names(rules.check(item(body="Write to karthik@polystratum.com.")))


# R6 AI label ---------------------------------------------------------------

def test_ai_generated_without_label_fails():
    assert "ai_label" in names(rules.check(item(ai_generated=True, ai_label=False)))


def test_synthetic_media_without_label_fails():
    media = [{"path": "media/reel.mp4", "alt": "reel", "synthetic": True}]
    assert "ai_label" in names(rules.check(item(media=media, ai_label=False)))


def test_ai_generated_with_label_passes():
    assert "ai_label" not in names(rules.check(item(ai_generated=True, ai_label=True)))


# R7 platform limits --------------------------------------------------------

def test_linkedin_too_long_fails():
    assert "platform_limits" in names(rules.check(item(body="a " * 1600)))


def test_instagram_too_long_fails():
    it = item(platform="instagram", id="2026-11-09-ig-01", format="image", body="a " * 1200)
    assert "platform_limits" in names(rules.check(it))


def test_too_many_hashtags_fails():
    it = item(hashtags=["#ai", "#agents", "#ops", "#sme"])
    assert "platform_limits" in names(rules.check(it))


def test_hashtags_in_body_count():
    it = item(body="Closing the books. #ai #agents #ops #sme")
    assert "platform_limits" in names(rules.check(it))


# R8 retired name -----------------------------------------------------------

def test_cognix_fails():
    assert "no_retired_name" in names(rules.check(item(body="Built at Cognix.")))


# R9 AI tells ---------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Leverage AI to elevate your career.",
    "The result? Faster closes.",
    "Here's how we did it.",
    "It's not about tools, it's about judgement.",
    "This is a game-changer.",
])
def test_ai_tells_fail(text):
    assert "ai_tells" in names(rules.check(item(body=text)))


# R10 format fits platform, slot is IST --------------------------------------

def test_pdf_on_instagram_fails():
    it = item(platform="instagram", id="2026-11-09-ig-01", format="document_pdf")
    assert "format_and_slot" in names(rules.check(it))


def test_reel_on_linkedin_fails():
    assert "format_and_slot" in names(rules.check(item(format="reel")))


def test_slot_must_be_ist():
    assert "format_and_slot" in names(rules.check(item(slot_ist="2026-11-09T09:15:00Z")))


def test_id_platform_mismatch_fails():
    assert "format_and_slot" in names(rules.check(item(id="2026-11-09-ig-01")))


def test_id_date_must_match_slot():
    assert "format_and_slot" in names(rules.check(item(id="2026-11-10-li-01")))


# R11 links -----------------------------------------------------------------

def test_unknown_link_domain_fails():
    assert "link_allowlist" in names(rules.check(item(body="Read more at https://bit.ly/x1")))


def test_http_link_fails():
    assert "link_allowlist" in names(rules.check(item(body="See http://polystratum.com/forms/x")))


def test_own_link_passes():
    it = item(body="Check yourself: https://polystratum.com/forms/career-takeoff-readiness")
    assert "link_allowlist" not in names(rules.check(it))
