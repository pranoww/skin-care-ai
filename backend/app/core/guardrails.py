"""AI Guardrails for input validation, safety enforcement, and output sanitization."""

import logging
import re
from typing import List, Optional

from app.schemas.chat import ChatResponse, SeverityLevel

logger = logging.getLogger(__name__)


# ==============================================================================
# Input Safety Patterns
# ==============================================================================

EMERGENCY_PATTERNS = [
    r"\b(difficulty breathing|trouble breathing|throat closing|throat swelling)\b",
    r"\b(anaphylaxis|anaphylactic)\b",
    r"\b(chemical burn|acid burn|battery acid)\b",
    r"\b(unconscious|passed out|fainting)\b",
    r"\b(severe blood loss|bleeding uncontrollably|gushing blood)\b",
]

HAZARDOUS_PRACTICE_PATTERNS = [
    r"\b(put bleach|apply bleach|drink bleach|use bleach)\b",
    r"\b(cut off (my |a )?(mole|growth|wart|cyst)|remove (my |a )?mole myself)\b",
    r"\b(sewing needle|safety pin|knife|razor blade) to (pop|drain|cut|pierce)\b",
    r"\b(burn off (my |a )?(wart|mole|skin))\b",
]

# Patterns are deliberately narrow: each one needs an AI-directed target
# ("your instructions", "system prompt", "API key") close to the verb, so normal
# skincare phrasing ("clear acne", "my environment", "the rules for vitamin C")
# passes. Gaps are bounded to the same sentence with [^.?!\n]{0,N}.
_SAME_SENTENCE = r"[^.?!\n]{0,40}?"
_FORGET_VERBS = r"(?:forget|forgt|frget|foget|foegt|fogret)"
_OVERRIDE_VERBS = r"(?:ignore|ignre|disregard|override|bypass)"
_AI_RULE_NOUNS = r"(?:instructions|prompts?|rules|guidelines|directives|constraints|programming)"

PROMPT_INJECTION_PATTERNS = [
    # "ignore all previous instructions", "disregard your system prompt"
    rf"\b{_OVERRIDE_VERBS}\b{_SAME_SENTENCE}\b(?:all|any|your|the|these|those|previous|prior|above|earlier|system|initial|original)\s+(?:\w+\s+)?{_AI_RULE_NOUNS}\b",
    # "forget everything", "foegt about everyhting", "forget your rules"
    rf"\b{_FORGET_VERBS}\b\s+(?:about\s+)?(?:everything|everyhting|evrything|all\s+(?:previous|prior|your|the)|your\s+{_AI_RULE_NOUNS}|previous\s+{_AI_RULE_NOUNS})\b",
    r"\breset\s+(?:your|the)\s+(?:instructions|system|rules|memory)\b",
    r"\byou are now\s+(?:an?\s+)?(?:unrestricted|jailbroken|DAN|in developer mode|developer mode|medical doctor who prescribes)\b",
    r"\b(?:system prompt|reveal your prompt|print (?:your |the )?system instructions|show (?:me )?your (?:prompt|instructions))\b",
    r"\b(?:pretend to be|roleplay as|act as)\s+(?:an unrestricted|a doctor who prescribes|a hacker|a licensed doctor who prescribes)\b",
]

# Secrets the assistant must never reveal. Generic words like "environment" or
# "tokens" only count when they clearly point at the system ("your env",
# "environment variables"), never at the user's surroundings.
_SECRET_NOUNS = (
    r"(?:api[_\s-]?keys?|gemini[_\s-]?(?:api[_\s-]?)?keys?|secret[_\s-]?keys?|secrets"
    r"|credentials|passwords?|access[_\s-]?tokens?|auth[_\s-]?tokens?|bearer tokens?"
    r"|\.env(?:\s+file)?|env\s+file|environment\s+variables?|env\s+vars?)"
)
_SYSTEM_OWNED_GENERIC = r"(?:your|the\s+server'?s?|the\s+system'?s?|system)\s+(?:env|environment|config|configuration|tokens?)\b"

DATA_EXTRACTION_PATTERNS = [
    rf"\b(?:give|show|print|tell|reveal|send|display|share|leak|dump|provide|output|list|read)\b{_SAME_SENTENCE}(?:{_SECRET_NOUNS}|{_SYSTEM_OWNED_GENERIC})",
    rf"\bwhat(?:'s| is| are)\s+(?:your|the)\s+(?:{_SECRET_NOUNS}|env)\b",
    r"\b(?:cat|echo|printenv)\b[^.?!\n]{0,20}(?:\.env|config\.py|credentials)",
]

SECRET_LEAKAGE_PATTERNS = [
    r"AIza[0-9A-Za-z-_]{35}",
    r"AQ\.[0-9A-Za-z-_]{40,}",
    r"sk-[0-9A-Za-z-_]{20,}",
    r"gsk_[0-9A-Za-z-_]{20,}",
    r"Bearer\s+[A-Za-z0-9\-_\.]{20,}",
]

PRESCRIPTION_DRUGS = [
    # Isotretinoin
    r"\b(accutane|isotretinoin|isotroin|accufine|tretiva|zerotin)\b",

    # Tretinoin
    r"\b(tretinoin|retin-a|retino-a|supatret)\b",

    # Spironolactone
    r"\b(spironolactone|aldactone)\b",

    # Oral antibiotics
    r"\b(doxycycline|minocycline|tetracycline|doxy|doxicip|moxy|minoz)\b",

    # Clindamycin
    r"\b(clindamycin|oral clindamycin|clindac|clindac-a)\b",

    # Oral steroids / systemic corticosteroids
    r"\b(prednisone|prednisolone|oral steroid|systemic corticosteroid|deflazacort)\b",

    # Topical steroids
    r"\b(clobetasol|clobetasol propionate|triamcinolone|betamethasone)\b",
]

# "you have <condition>" is softened, but only when "have" is not an auxiliary
# or modal verb ("you have been using", "you have to", "you have tried").
_NON_DIAGNOSTIC_AFTER_HAVE = (
    r"been|had|to|got|gotten|tried|used|applied|mentioned|described|noticed|reported|"
    r"said|shared|already|not|no|never|experienced|developed|done|started|stopped|"
    r"seen|felt|taken|any|some|questions?|options|time"
)
DEFINITIVE_DIAGNOSIS_PATTERNS = [
    (rf"\byou (?:definitely |certainly |clearly )?have (?!(?:{_NON_DIAGNOSTIC_AFTER_HAVE})\b)", "your symptoms may be consistent with "),
    (r"\byour diagnosis is\b", "possible considerations include"),
    (r"\byou are suffering from\b", "you may be experiencing"),
]

SEVERE_SYMPTOMS_TRIGGERS = [
    r"\b(?:fever|chills)\b",
    r"\b(?:yellow pus|green pus|oozing pus)\b",
    r"\b(?:bleeding|blood oozing)\b",
    r"\b(?:intense pain|severe pain|excruciating pain|unbearable pain)\b",
    r"\b(?:spreading rapidly|worsening rapidly|rapidly spreading)\b",
]

# A red flag is ignored when the user explicitly negates it in the same clause
# ("no fever", "it is not bleeding", "without fever or chills").
_NEGATION = re.compile(
    r"\b(?:no|not|without|never|denies|deny|free of|absence of|"
    r"(?:do|does|did|is|are|was|were|has|have|had)n'?t|(?:do|does|did) not)\b",
    flags=re.IGNORECASE,
)
_CLAUSE_BREAK = re.compile(r"[.,;:!?\n]|\b(?:but|however|although|though|yet|except)\b", flags=re.IGNORECASE)
_NEGATION_WINDOW_CHARS = 40

# A recommendation that tells the user to avoid a drug does not need the
# "requires prescription" notice.
_AVOIDANCE_PREFIX = re.compile(r"^\s*(?:avoid|don'?t|do not|stop|never|skip)\b", flags=re.IGNORECASE)
_PROFESSIONAL_WORDS = ("prescription", "dermatologist", "doctor", "physician", "healthcare provider")


def _is_negated(text: str, match_start: int) -> bool:
    """True when a negation word precedes the match within the same clause."""
    window = text[max(0, match_start - _NEGATION_WINDOW_CHARS):match_start]
    breaks = list(_CLAUSE_BREAK.finditer(window))
    if breaks:
        window = window[breaks[-1].end():]
    return bool(_NEGATION.search(window))


def _has_unnegated_red_flag(text: str) -> bool:
    for trigger in SEVERE_SYMPTOMS_TRIGGERS:
        for match in re.finditer(trigger, text, flags=re.IGNORECASE):
            if not _is_negated(text, match.start()):
                return True
    return False


def _soften_diagnosis(text: str) -> str:
    """Replace definitive diagnostic phrasing, keeping sentence-start capitals."""
    def _replace_keep_case(replacement: str):
        def _sub(match: re.Match) -> str:
            if match.group(0)[:1].isupper():
                return replacement[:1].upper() + replacement[1:]
            return replacement
        return _sub

    for pattern, replacement in DEFINITIVE_DIAGNOSIS_PATTERNS:
        text = re.sub(pattern, _replace_keep_case(replacement), text, flags=re.IGNORECASE)
    return text


class AIGuardrail:
    """Multi-stage AI guardrail system for pre-execution and post-execution safety."""

    @classmethod
    def check_input_guardrail(cls, message: str) -> Optional[ChatResponse]:
        """Inspect user input before sending to LLM.
        
        Returns a preemptive safe ChatResponse if an emergency, hazardous practice,
        or injection attempt is detected, bypassing LLM execution.
        """
        lower_msg = message.lower()

        # 1. Emergency Detection
        for pattern in EMERGENCY_PATTERNS:
            if re.search(pattern, lower_msg, flags=re.IGNORECASE):
                logger.warning("Guardrail triggered: Emergency detected in input.")
                return ChatResponse(
                    skin_concern="Potential Medical Emergency / Acute Reaction",
                    summary=(
                        "The symptoms described suggest a potentially acute or life-threatening emergency. "
                        "This AI chatbot is strictly for general, non-urgent skin care education and cannot handle medical emergencies."
                    ),
                    possible_factors=[
                        "Acute systemic allergic reaction or anaphylaxis",
                        "Severe chemical or thermal injury",
                        "Acute medical crisis"
                    ],
                    recommendations=[
                        "Call emergency services (e.g. 911 / 112) or go to the nearest emergency room immediately",
                        "Do not wait or rely on topical skincare products",
                        "Avoid taking unverified medications without emergency personnel guidance"
                    ],
                    severity=SeverityLevel.HIGH,
                    confidence=1.0,
                    professional_advice=True,
                )

        # 2. Hazardous Practice Detection
        for pattern in HAZARDOUS_PRACTICE_PATTERNS:
            if re.search(pattern, lower_msg, flags=re.IGNORECASE):
                logger.warning("Guardrail triggered: Hazardous self-treatment practice detected.")
                return ChatResponse(
                    skin_concern="Hazardous Self-Treatment Risk",
                    summary=(
                        "Attempting invasive self-treatment, cutting skin lesions, using non-medical corrosive substances (like bleach), "
                        "or using unsterilized tools can lead to severe tissue damage, disfigurement, and life-threatening infections."
                    ),
                    possible_factors=[
                        "Attempted self-removal of skin lesions",
                        "Use of caustic or non-skincare chemical agents",
                        "Risk of secondary bacterial infection and scarring"
                    ],
                    recommendations=[
                        "Immediately stop using household chemicals, sharp tools, or invasive self-removal techniques",
                        "Keep the affected skin clean with gentle soap and water",
                        "Schedule an appointment with a board-certified dermatologist or healthcare provider for safe evaluation and treatment"
                    ],
                    severity=SeverityLevel.HIGH,
                    confidence=1.0,
                    professional_advice=True,
                )

        # 3. Prompt Injection & Confidential Data Extraction Defense
        is_injection = any(re.search(p, lower_msg, flags=re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS)
        is_extraction = any(re.search(p, lower_msg, flags=re.IGNORECASE) for p in DATA_EXTRACTION_PATTERNS)

        if is_injection or is_extraction:
            logger.warning("Guardrail triggered: Prompt injection or data extraction attempt detected.")
            if is_extraction:
                summary_text = (
                    "Security Notice: System environment configurations, private credentials, and API keys are strictly confidential. "
                    "Requests attempting to extract system parameters, override safety instructions, or reveal secrets are blocked."
                )
            else:
                summary_text = (
                    "This assistant is designed strictly to offer safe, non-diagnostic skin care guidance. "
                    "System instructions and medical safety boundaries cannot be bypassed or modified."
                )

            return ChatResponse(
                skin_concern="Security & Safety Policy Notice",
                summary=summary_text,
                possible_factors=["Security policy enforcement and prompt injection / data extraction protection"],
                recommendations=[
                    "Please describe only your legitimate skincare concerns (e.g., dryness, acne, or irritation) in natural language."
                ],
                severity=SeverityLevel.LOW,
                confidence=1.0,
                professional_advice=False,
            )

        # Input is safe to pass to LLM
        return None

    @classmethod
    def apply_output_guardrail(cls, response: ChatResponse, user_input: str) -> ChatResponse:
        """Inspect and sanitize AI-generated response before delivering to the client.
        
        Ensures:
        - No definitive diagnoses slip through.
        - Prescription medications are not recommended without doctor consultation notice.
        - Red-flag symptoms strictly enforce professional_advice=True and high/medium severity.
        - Confidential tokens, API keys, and environment variables are redacted.
        """
        lower_input = user_input.lower()
        summary = response.summary
        recommendations = list(response.recommendations)
        severity = response.severity
        professional_advice = response.professional_advice

        # 1. Soften any definitive diagnostic phrasing
        summary = _soften_diagnosis(summary)

        # 2. Check for prescription drug mentions in recommendations
        sanitized_recs: List[str] = []
        for rec in recommendations:
            rec_modified = rec
            mentions_rx = any(re.search(p, rec, flags=re.IGNORECASE) for p in PRESCRIPTION_DRUGS)
            already_qualified = any(word in rec.lower() for word in _PROFESSIONAL_WORDS)
            if mentions_rx and not already_qualified and not _AVOIDANCE_PREFIX.search(rec):
                rec_modified = f"{rec} (Requires professional consultation and prescription from a qualified healthcare provider)"
            sanitized_recs.append(rec_modified)

        # 3. Enforce triage escalation for severe or alarming symptoms
        if _has_unnegated_red_flag(lower_input):
            professional_advice = True
            if severity in [SeverityLevel.LOW, SeverityLevel.UNKNOWN]:
                severity = SeverityLevel.HIGH

            # Ensure seeing a healthcare professional is included in recommendations
            already_mentions_doctor = any(
                ("dermatologist" in r.lower() or "physician" in r.lower() or "medical" in r.lower() or "doctor" in r.lower())
                for r in sanitized_recs
            )
            if not already_mentions_doctor:
                sanitized_recs.insert(0, "Consult a board-certified dermatologist or healthcare provider promptly for an in-person clinical evaluation.")

        # 4. Confidential Data Leakage Sanitizer
        for secret_pattern in SECRET_LEAKAGE_PATTERNS:
            summary = re.sub(secret_pattern, "[CONFIDENTIAL_DATA_REDACTED]", summary)
            sanitized_recs = [
                re.sub(secret_pattern, "[CONFIDENTIAL_DATA_REDACTED]", r) for r in sanitized_recs
            ]

        return ChatResponse(
            skin_concern=response.skin_concern,
            summary=summary,
            possible_factors=response.possible_factors,
            recommendations=sanitized_recs,
            severity=severity,
            confidence=response.confidence,
            professional_advice=professional_advice,
        )
