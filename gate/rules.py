"""Brand and safety rules for one content item.

Each rule returns a list of Violation. `check` runs them all.
A failing item never reaches a publish slot. Rules are deliberately strict:
a false alarm costs one redraft; a miss costs a public post.
"""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlparse


@dataclass(frozen=True)
class Violation:
    rule: str
    message: str


IST = timedelta(hours=5, minutes=30)
OWN_EMAILS = {"karthik@polystratum.com"}
LINK_HOSTS = {"polystratum.com", "www.polystratum.com", "github.com",
              "linkedin.com", "www.linkedin.com"}
MAX_CHARS = {"linkedin": 3000, "instagram": 2200, "facebook": 63206}
MAX_HASHTAGS = 3
FORMATS = {
    "linkedin": {"text", "image", "document_pdf"},
    "instagram": {"image", "carousel", "reel", "story"},
    "facebook": {"text", "image", "carousel", "reel", "story"},
}
PLATFORM_CODE = {"linkedin": "li", "instagram": "ig", "facebook": "fb"}


def _text(item: dict) -> str:
    raw = "\n".join([item.get("body", ""), item.get("first_comment", "")])
    return raw.replace("’", "'").replace("‘", "'")


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _any(patterns, text):
    return [p for p in patterns if re.search(p, text, re.IGNORECASE)]


# R1 ------------------------------------------------------------------------
PRICE = [
    r"₹\s?\d", r"\bRs\.?\s?\d", r"\bINR\b", r"\brupees?\b",
    r"\bfree\s+(session|webinar|class|workshop|demo|seats?|trial|masterclass|event|course)\b",
    r"\bfor free\b", r"\bdiscount", r"\d+\s?%\s?off\b",
]


def no_price(item):
    hits = _any(PRICE, _text(item))
    return [Violation("no_price", f"price or offer language: /{hits[0]}/")] if hits else []


# R2 ------------------------------------------------------------------------
NT = r"northern\s+trust"
NT_PAST = [
    r"\b(former|ex-?)\s*(vp\b|vice president\b)?[^.]{0,20}" + NT,
    r"\b(spent|left|leaving|after|was|were|worked|led|ran|retired)\b[^.]*" + NT,
    NT + r"[^.]*\b(taught|was|were|gave|showed)\b",
]
NT_NEVER = [r"\b(partner\w*|endors\w*|certified|association|sponsor\w*|backed)\b[^.]*" + NT,
            NT + r"[^.]*\b(partner\w*|endors\w*|certif\w*|sponsor\w*|backs)\b"]


def northern_trust_past_tense(item):
    out = []
    for s in _sentences(_text(item)):
        if not re.search(NT, s, re.IGNORECASE):
            continue
        if _any(NT_NEVER, s) or not _any(NT_PAST, s):
            out.append(Violation("northern_trust_past_tense",
                                 "Northern Trust must read as past employment only"))
    for m in item.get("media", []):
        if re.search(r"northern", m.get("path", "") + " " + m.get("alt", ""), re.IGNORECASE):
            out.append(Violation("northern_trust_past_tense", "no Northern Trust logo or asset"))
    return out


# R3 ------------------------------------------------------------------------
SCARCITY = [r"\bseats?\s+(left|remaining)\b", r"\bspots?\s+(left|remaining)\b",
            r"\bonly\s+\d+\s+(seats|spots|places)\b", r"\bfilling\s+(up\s+)?fast\b",
            r"\blast chance\b", r"\bhurry\b", r"\bdon't miss out\b"]
SELLING = [r"\benrol+(ment|ling|led|s)?\b", r"\bcohort\b",
           r"\b\d-day\s+(course|programme|program)\b"]


def no_cohort_or_scarcity(item):
    text = _text(item)
    hits = _any(SCARCITY, text)
    if item.get("kind") != "founder_story":
        hits += _any(SELLING, text)
    return [Violation("no_cohort_or_scarcity", f"cohort selling or invented scarcity: /{hits[0]}/")] if hits else []


# R4 ------------------------------------------------------------------------
STAT = [r"\d+(\.\d+)?\s?%", r"\b\d+(\.\d+)?\s?x\b",
        r"\b\d+(\.\d+)?\s?(times|million|billion|crore|lakhs?|percent)\b",
        r"\b(research|studies|study|data|surveys?|reports?)\s+(shows?|finds?|found|says?|suggests?)\b",
        r"\baccording to\b"]


def stat_needs_source(item):
    if not _any(STAT, _text(item)):
        return []
    sources = item.get("sources", [])
    if not sources:
        return [Violation("stat_needs_source", "a statistic or study claim with no source")]
    if any(not s.get("url", "").startswith("https://") for s in sources):
        return [Violation("stat_needs_source", "every source must be a live https link")]
    return []


# R5 ------------------------------------------------------------------------
EMAIL = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
PHONE = r"(?<!\d)\+?\d[\d\s-]{8,}\d(?!\d)"


def no_personal_data(item):
    text = _text(item)
    out = []
    for e in re.findall(EMAIL, text):
        if e.lower() not in OWN_EMAILS:
            out.append(Violation("no_personal_data", "an email address other than KV's own"))
    for p in re.findall(PHONE, text):
        if len(re.sub(r"\D", "", p)) >= 10:
            out.append(Violation("no_personal_data", "a phone number"))
    return out


# R6 ------------------------------------------------------------------------
def ai_label(item):
    synthetic = item.get("ai_generated") or any(m.get("synthetic") for m in item.get("media", []))
    if synthetic and not item.get("ai_label"):
        return [Violation("ai_label", "synthetic content must carry the AI label")]
    return []


# R7 ------------------------------------------------------------------------
def platform_limits(item):
    out = []
    platform = item.get("platform")
    body = item.get("body", "")
    if platform in MAX_CHARS and len(body) > MAX_CHARS[platform]:
        out.append(Violation("platform_limits", f"{len(body)} chars; {platform} allows {MAX_CHARS[platform]}"))
    tags = {t.lower() for t in item.get("hashtags", [])}
    tags |= {t.lower() for t in re.findall(r"(?<![\w#])#\w+", body)}
    if len(tags) > MAX_HASHTAGS:
        out.append(Violation("platform_limits", f"{len(tags)} hashtags; brand limit is {MAX_HASHTAGS}"))
    return out


# R8 ------------------------------------------------------------------------
def no_retired_name(item):
    if re.search(r"\bcognix\b", _text(item), re.IGNORECASE):
        return [Violation("no_retired_name", "the business is Polystratum, never Cognix")]
    return []


# R9 ------------------------------------------------------------------------
AI_TELLS = [
    r"\bleverag\w*", r"\belevat\w*", r"\bempower\w*", r"\bunlock\w*", r"\bgame[- ]changer\b",
    r"\bdelve\w*", r"\bsynerg\w*", r"\bin today's fast-paced\b", r"\blet that sink in\b",
    r"\bthe result\?", r"\bhere's (how|what|the thing|why)\b",
    r"\bit's not (just )?[^.,;]{1,40}[,;—-]\s*it's\b",
    r"\bnot (just )?\w+(\s\w+)?,\s+but\b",
]


def ai_tells(item):
    hits = _any(AI_TELLS, _text(item))
    return [Violation("ai_tells", f"AI-tell phrasing: /{hits[0]}/")] if hits else []


# R10 -----------------------------------------------------------------------
def format_and_slot(item):
    out = []
    platform, fmt = item.get("platform"), item.get("format")
    if platform in FORMATS and fmt not in FORMATS[platform]:
        out.append(Violation("format_and_slot", f"{fmt} is not a {platform} format"))
    slot = None
    try:
        slot = datetime.fromisoformat(item.get("slot_ist", ""))
    except ValueError:
        out.append(Violation("format_and_slot", "slot_ist is not an ISO date-time"))
    if slot is not None and slot.utcoffset() != IST:
        out.append(Violation("format_and_slot", "slot_ist must carry the +05:30 offset"))
    m = re.match(r"^(\d{4}-\d{2}-\d{2})-(li|ig|fb)-\d{2}$", item.get("id", ""))
    if not m:
        out.append(Violation("format_and_slot", "id must be <date>-<li|ig|fb>-<nn>"))
    else:
        if PLATFORM_CODE.get(platform) != m.group(2):
            out.append(Violation("format_and_slot", "id platform code does not match platform"))
        if slot is not None and slot.date().isoformat() != m.group(1):
            out.append(Violation("format_and_slot", "id date does not match the slot date"))
    return out


# R11 -----------------------------------------------------------------------
URL = r"\b(?:https?://|www\.)[^\s)>\]]+"


def link_allowlist(item):
    out = []
    for url in re.findall(URL, _text(item), re.IGNORECASE):
        full = url if "://" in url else "https://" + url
        parsed = urlparse(full)
        if parsed.scheme != "https":
            out.append(Violation("link_allowlist", "links must be https"))
        elif parsed.hostname not in LINK_HOSTS:
            out.append(Violation("link_allowlist", f"link host not allowed: {parsed.hostname}"))
    return out


RULES = [no_price, northern_trust_past_tense, no_cohort_or_scarcity, stat_needs_source,
         no_personal_data, ai_label, platform_limits, no_retired_name, ai_tells,
         format_and_slot, link_allowlist]


def check(item: dict) -> list[Violation]:
    out = []
    for rule in RULES:
        out.extend(rule(item))
    return out
