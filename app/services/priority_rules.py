import re
from dataclasses import dataclass

RULES_VERSION = "1.0.0"

# Common negation terms and historical/resolved context patterns
NEGATION_PATTERNS = [
    r"\b(?:no|not|neither|nor|without|never|don't|doesn't|didn't|isn't|aren't|wasn't|weren't)\b",
    r"\b(?:false\s+alarm|no\s+sign\s+of|prevent(?:ed|ing)?)\b",
]

HISTORICAL_OR_RESOLVED_PATTERNS = [
    r"\b(?:already|previously|earlier|yesterday|last\s+week|last\s+month|in\s+the\s+past)\b",
    r"\b(?:fixed|repaired|resolved|addressed|cleared\s+up|stopped)\b",
    r"\b(?:used\s+to\s+be|was\s+already|is\s+now\s+fine)\b",
]

# Versioned priority definitions with explainable trigger phrases
# Ordered from highest to lowest severity
URGENT_PHRASES = [
    ("sparking socket", "Immediate electrical hazard with fire risk"),
    ("sparking wire", "Immediate electrical hazard with fire risk"),
    ("sparking outlet", "Immediate electrical hazard with fire risk"),
    ("live wire", "Immediate electrocution hazard"),
    ("exposed live wire", "Immediate electrocution hazard"),
    ("exposed wire", "Potential electrocution hazard"),
    ("electrical fire", "Active fire or combustion event"),
    ("gas leak", "Potential hazardous gas concentration or explosion risk"),
    ("smoke coming from", "Active sign of combustion or overheating"),
    ("ceiling collapse", "Severe structural failure and physical injury risk"),
    ("falling debris", "Falling structural hazard"),
    ("sewage overflow", "Severe biological hazard and contamination"),
    ("chemical spill", "Hazardous substance spill"),
    ("broken glass window", "Immediate physical laceration hazard in active passage"),
    ("locked fire exit", "Emergency egress obstruction"),
    ("blocked emergency exit", "Emergency egress obstruction"),
]

HIGH_PHRASES = [
    ("water pipe burst", "Active water flooding causing property damage"),
    ("flooding", "Active water accumulation impeding use"),
    ("water leakage", "Continuous water leak requiring timely maintenance"),
    ("no running water", "Critical utility outage for sanitation/hygiene"),
    ("power outage", "Complete electrical blackout in building/wing"),
    ("blackout", "Complete electrical blackout"),
    ("elevator stuck", "Mechanical trap or vertical mobility disruption"),
    ("lift stuck", "Mechanical trap or vertical mobility disruption"),
    ("pest infestation", "Sanitary pest issue affecting health"),
    ("bedbugs", "Severe pest infestation in dormitory"),
    ("food poisoning", "Health concern from cafeteria food"),
    ("mold growth", "Respiratory health concern"),
    ("door lock broken", "Room security vulnerability"),
]

NORMAL_PHRASES = [
    ("ac not cooling", "HVAC comfort issue"),
    ("fan not working", "Air circulation malfunction"),
    ("wifi slow", "Network performance degradation"),
    ("wifi down", "Internet connectivity disruption"),
    ("projector not working", "Classroom presentation equipment failure"),
    ("light bulb fused", "Lighting replacement needed"),
    ("desk broken", "Classroom/study furniture maintenance"),
    ("chair broken", "Furniture maintenance"),
    ("tap dripping", "Minor plumbing water waste"),
    ("flush not working", "Restroom plumbing issue"),
]

LOW_PHRASES = [
    ("suggestion", "General user improvement suggestion"),
    ("feedback", "User input regarding campus life"),
    ("aesthetic", "Cosmetic improvement request"),
    ("paint peeling", "Non-structural cosmetic surface maintenance"),
    ("library book", "Book requisition or catalog query"),
    ("vending machine", "Convenience service request"),
]


@dataclass
class PriorityEvaluation:
    suggested_priority: str
    matched_phrase: str | None
    explanation: str
    is_ambiguous: bool
    rules_version: str


def evaluate_priority(text: str, submission_type: str = "complaint") -> PriorityEvaluation:
    """
    Evaluates complaint priority using versioned, explainable deterministic rules.
    Detects negation and historical context to prevent false urgency.
    """
    if not text:
        return PriorityEvaluation(
            suggested_priority="Normal",
            matched_phrase=None,
            explanation="Empty description; defaulted to Normal priority.",
            is_ambiguous=True,
            rules_version=RULES_VERSION,
        )

    # If it is explicitly a suggestion and has no safety keywords, start at Low
    if submission_type == "suggestion":
        # Check if user submitted a safety hazard inside a suggestion
        for phrase, reason in URGENT_PHRASES:
            if re.search(r"\b" + re.escape(phrase) + r"\b", text, re.IGNORECASE):
                # Urgent overrides suggestion type
                break
        else:
            return PriorityEvaluation(
                suggested_priority="Low",
                matched_phrase="submission_type: suggestion",
                explanation="Submitted as a general campus suggestion or improvement.",
                is_ambiguous=False,
                rules_version=RULES_VERSION,
            )

    text_lower = text.lower()
    sentences = re.split(r"[.!?;\n]+", text_lower)

    def contains_negation_or_history(sentence: str, match_start: int, match_end: int) -> tuple[bool, str]:
        # Check window around match (up to 40 chars before or after)
        window_start = max(0, match_start - 40)
        window_end = min(len(sentence), match_end + 40)
        window = sentence[window_start:window_end]

        for pat in NEGATION_PATTERNS:
            if re.search(pat, window):
                return True, "Negation detected near keyword"

        for pat in HISTORICAL_OR_RESOLVED_PATTERNS:
            if re.search(pat, window):
                return True, "Historical or resolved context detected"

        return False, ""

    # 1. Check Urgent phrases
    for phrase, reason in URGENT_PHRASES:
        for s in sentences:
            m = re.search(r"\b" + re.escape(phrase) + r"\b", s)
            if m:
                has_qualifier, qualifier_reason = contains_negation_or_history(s, m.start(), m.end())
                if has_qualifier:
                    return PriorityEvaluation(
                        suggested_priority="Normal",
                        matched_phrase=phrase,
                        explanation=(
                            f"Matched hazard phrase '{phrase}' but detected '{qualifier_reason}'. "
                            f"Flagged as ambiguous for handler review."
                        ),
                        is_ambiguous=True,
                        rules_version=RULES_VERSION,
                    )
                return PriorityEvaluation(
                    suggested_priority="Urgent review",
                    matched_phrase=phrase,
                    explanation=f"Matched '{phrase}': {reason}.",
                    is_ambiguous=False,
                    rules_version=RULES_VERSION,
                )

    # 2. Check High phrases
    for phrase, reason in HIGH_PHRASES:
        for s in sentences:
            m = re.search(r"\b" + re.escape(phrase) + r"\b", s)
            if m:
                has_qualifier, qualifier_reason = contains_negation_or_history(s, m.start(), m.end())
                if has_qualifier:
                    return PriorityEvaluation(
                        suggested_priority="Normal",
                        matched_phrase=phrase,
                        explanation=f"Matched '{phrase}' with '{qualifier_reason}'. Requiring handler review.",
                        is_ambiguous=True,
                        rules_version=RULES_VERSION,
                    )
                return PriorityEvaluation(
                    suggested_priority="High",
                    matched_phrase=phrase,
                    explanation=f"Matched '{phrase}': {reason}.",
                    is_ambiguous=False,
                    rules_version=RULES_VERSION,
                )

    # 3. Check Normal phrases
    for phrase, reason in NORMAL_PHRASES:
        if re.search(r"\b" + re.escape(phrase) + r"\b", text_lower):
            return PriorityEvaluation(
                suggested_priority="Normal",
                matched_phrase=phrase,
                explanation=f"Matched '{phrase}': {reason}.",
                is_ambiguous=False,
                rules_version=RULES_VERSION,
            )

    # 4. Check Low phrases
    for phrase, reason in LOW_PHRASES:
        if re.search(r"\b" + re.escape(phrase) + r"\b", text_lower):
            return PriorityEvaluation(
                suggested_priority="Low",
                matched_phrase=phrase,
                explanation=f"Matched '{phrase}': {reason}.",
                is_ambiguous=False,
                rules_version=RULES_VERSION,
            )

    # Default fallback
    return PriorityEvaluation(
        suggested_priority="Normal",
        matched_phrase=None,
        explanation="Standard maintenance report; no high-severity hazard phrases detected.",
        is_ambiguous=False,
        rules_version=RULES_VERSION,
    )
