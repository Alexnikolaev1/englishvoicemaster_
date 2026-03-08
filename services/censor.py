"""Content moderation service."""
import re
from dataclasses import dataclass

FORBIDDEN_PATTERNS = [
    # English profanity
    r'\b(fuck(?:ing|er|ed)?|shit|bitch|ass(?:hole)?|cunt|cock|dick|pussy|bastard)\b',
    r'\b(porn(?:o)?|xxx|nude|naked|erotic|sex(?:ual)?)\b',
    r'\b(how\s+to\s+(make|build|create)\s+(bomb|weapon|gun|explosive|drug))\b',
    r'\b(kill\s+(me|you|him|her|them|yourself|myself))\b',
    r'\b(suicide|self[\s-]harm|cut\s+myself)\b',
    # Russian mat (transliterated)
    r'\b((?:blyat|bliad|khuy|pizd|yebat|suka|muda[ck]|pidar|pizdec))\b',
]

SOFT_REDIRECT_PATTERNS = [
    r'\b(politic(?:s|al)?|president|government|election|party|democrat|republican)\b',
    r'\b(war|violence|terrorist|attack|weapon|gun|murder)\b',
]

COMPILED_HARD = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]
COMPILED_SOFT = [re.compile(p, re.IGNORECASE) for p in SOFT_REDIRECT_PATTERNS]


@dataclass
class CensorResult:
    blocked: bool
    soft_redirect: bool
    reason: str = ""


def check_content(text: str) -> CensorResult:
    if not text:
        return CensorResult(blocked=False, soft_redirect=False)
    for pattern in COMPILED_HARD:
        if pattern.search(text):
            return CensorResult(blocked=True, soft_redirect=False, reason="forbidden_content")
    for pattern in COMPILED_SOFT:
        if pattern.search(text):
            return CensorResult(blocked=False, soft_redirect=True, reason="sensitive_topic")
    return CensorResult(blocked=False, soft_redirect=False)
