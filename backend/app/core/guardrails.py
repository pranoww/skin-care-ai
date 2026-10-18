"""AI Guardrails for input validation, safety enforcement, and output sanitization."""

import logging
import re
from typing import Optional, List

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

PROMPT_INJECTION_PATTERNS = [
    # Forget / Ignore / Disregard instructions (with common typos like foegt, foget, ignre, everyhting)
    r"\b(fo?rge?t|foegt|foget)\b.*?\b(everything|everyhting|all|rules|instructions|prompts?|context)\b",
    r"\b(ignore|ignre|disregard|override|bypass|cancel|drop|clear)\b.*?\b(all|previous|prior|system|earlier)?\s*(instructions|prompts?|rules|constraints|context|guidelines)\b",
    r"\b(reset (your |the )?(instructions|system|rules|memory))\b",
    r"\b(you are now (an? )?(unrestricted|jailbroken|DAN|developer mode|medical doctor who prescribes))\b",
    r"\b(system prompt|reveal your prompt|print system instructions|show (me )?your prompt)\b",
    r"\b(pretend to be|roleplay as|act as) (an unrestricted|a doctor who prescribes|a hacker)\b",
]

DATA_EXTRACTION_PATTERNS = [
    # Attempts to extract env, api keys, tokens, credentials, secrets
    r"\b(give|show|print|tell|reveal|send|display|share|leak|dump|provide|output)\b.*?\b(your |the |all )?(env|\.env|environment|api[_\s-]?keys?|gemini[_\s-]?key|secrets?|tokens?|credentials?|passwords?)\b",
    r"\bwhat is (your |the )?(env|\.env|api[_\s-]?key|secret|token|gemini[_\s-]?api[_\s-]?key|password)\b",
    r"\b(read|cat|echo|printenv|env)\b.*?\b(\.env|config\.py|credentials|environment)\b",
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

DEFINITIVE_DIAGNOSIS_PATTERNS = [
    (r"\byou have ([a-z\s]+)(?:disease|condition|infection)?\b", r"your symptoms may be consistent with \1"),
    (r"\byour diagnosis is\b", r"possible considerations include"),
    (r"\byou are suffering from\b", r"you may be experiencing"),
    (r"\byou definitely have\b", r"you might have"),
]

SEVERE_SYMPTOMS_TRIGGERS = [
    r"\b(fever|chills)\b",
    r"\b(yellow pus|green pus|oozing pus)\b",
    r"\b(bleeding|blood oozing)\b",
    r"\b(intense pain|severe pain|excruciating pain|unbearable pain)\b",
    r"\b(spreading rapidly|worsening rapidly|rapidly spreading)\b",
]


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
        for pattern, replacement in DEFINITIVE_DIAGNOSIS_PATTERNS:
            summary = re.sub(pattern, replacement, summary, flags=re.IGNORECASE)

        # 2. Check for prescription drug mentions in recommendations
        sanitized_recs: List[str] = []
        for rec in recommendations:
            rec_modified = rec
            for rx_pattern in PRESCRIPTION_DRUGS:
                if re.search(rx_pattern, rec, flags=re.IGNORECASE):
                    # Ensure it clarifies prescription requirement
                    if "prescription" not in rec.lower() and "dermatologist" not in rec.lower() and "doctor" not in rec.lower():
                        rec_modified = f"{rec} (Requires professional consultation and prescription from a qualified healthcare provider)"
            sanitized_recs.append(rec_modified)

        # 3. Enforce triage escalation for severe or alarming symptoms
        has_severe_symptom = any(
            re.search(trigger, lower_input, flags=re.IGNORECASE) for trigger in SEVERE_SYMPTOMS_TRIGGERS
        )
        if has_severe_symptom:
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
