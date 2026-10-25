"""Conservative, deterministic rules. Unknown identifiers require human review."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from apps.api.schemas import Stage


@dataclass(frozen=True)
class Classification:
    company: str | None
    role: str | None
    status: Stage | None
    confidence: float
    reason: str
    action_required: bool = False
    deadline: datetime | None = None
    review_required: bool = True


RULES = [
    (
        Stage.REJECTED,
        r"not (?:be )?moving forward|will not be proceeding|unfortunately.{0,100}(?:application|position|candidate)|decided to pursue other candidates",
    ),
    (Stage.OFFER, r"(?:pleased|delighted|excited) to offer you|offer of employment|job offer for"),
    (
        Stage.INTERVIEW,
        r"(?:schedule|scheduled|invite you to|invitation to).{0,50}interview|interview (?:invitation|scheduled|with)",
    ),
    (
        Stage.ASSESSMENT,
        r"(?:complete|invited|invitation|take).{0,60}(?:assessment|coding challenge|hackerrank)|assessment invitation",
    ),
    (Stage.REVIEW, r"application.{0,40}(?:under review|being reviewed)|reviewing your application"),
    (
        Stage.RECEIVED,
        r"thank you for applying|(?:received|receiving) your application|application (?:received|confirmation)",
    ),
]


def classify(
    subject: str, sender: str, snippet: str, *, company: str | None = None, role: str | None = None
) -> Classification:
    # Length cap avoids pathological work on malformed/provider-controlled input.
    text = f"{subject[:1000]} {snippet[:4000]}"
    lower = text.lower()
    if re.search(r"unsubscribe|weekly digest|job alerts?|newsletter|promotional offer", lower):
        return Classification(None, None, None, 0.0, "Bulk mail is not an application event")
    identity = re.search(
        r"(?:application|applied)\s+for\s+(?:the\s+)?(.{2,100}?)\s+(?:position\s+)?at\s+([\w][\w &.'-]{1,80}?)(?=\s+(?:is (?:underway|under review|being reviewed|being processed)|has been (?:received|submitted)|was (?:received|submitted))\b|[.!?\n]|$)",
        subject,
        re.I,
    )
    if identity:
        role = identity.group(1).strip()
        company = identity.group(2).strip()
    action = bool(re.search(r"action required|complete by|deadline|respond by", lower))
    deadline = None
    date = re.search(r"(?:complete by|deadline[: ]*|respond by)\s*(\d{4}-\d{2}-\d{2})\b", lower)
    if date:
        try:
            deadline = datetime.strptime(date.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    matches = [stage for stage, pattern in RULES if re.search(pattern, lower)]
    if len(matches) > 1:
        # Acknowledgment prose is common in later updates. Conflicting terminal
        # outcomes or multiple active stages require review rather than priority.
        substantive = [stage for stage in matches if stage != Stage.RECEIVED]
        if len(substantive) > 1:
            return Classification(
                company, role, None, 0.4, "Conflicting recruiting signals", action, deadline
            )
        matches = substantive or matches
    status = matches[0] if matches else None
    if not status and not action:
        return Classification(company, role, None, 0.0, "No supported recruiting event")
    known = bool(company and role)
    confidence = 0.95 if known and status else 0.55
    return Classification(
        company,
        role,
        status,
        confidence,
        "Explicit recruiting phrase and application identity"
        if known
        else "Application identity is incomplete",
        action,
        deadline,
        not (known and status and confidence >= 0.9),
    )
