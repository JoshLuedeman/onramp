"""Content safety service — prompt injection defense & output filtering.

Provides input sanitization, output validation, per-user rate limiting,
and security-event logging for all AI-facing endpoints.
"""

import base64
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timezone

from app.schemas.content_safety import (
    ContentSafetyConfig,
    InputCheckResult,
    OutputCheckResult,
    RateLimitStatus,
    SafetyStrictness,
)

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("onramp.security")

# ── Prompt injection patterns ───────────────────────────────────────
# Each entry: (compiled regex, human-readable label, minimum strictness)

_INJECTION_PATTERNS: list[tuple[re.Pattern, str, SafetyStrictness]] = [
    # Direct instruction override
    (
        re.compile(
            r"ignore\s+(all\s+)?(previous|prior|above|earlier)"
            r"\s+(instructions|prompts|rules|context)", re.I,
        ),
        "instruction_override", SafetyStrictness.MINIMAL,
    ),
    (
        re.compile(
            r"disregard\s+(all\s+)?(previous|prior|above|earlier|your)"
            r"\s+(instructions|prompts|rules|directives)", re.I,
        ),
        "instruction_override", SafetyStrictness.MINIMAL,
    ),
    (
        re.compile(
            r"forget\s+(all\s+)?(your\s+)?(previous|prior|above|earlier)"
            r"\s+(instructions|prompts|rules|context)", re.I,
        ),
        "instruction_override", SafetyStrictness.MINIMAL,
    ),
    # System prompt takeover
    (re.compile(r"(?:^|\n)\s*system\s*:", re.I),
     "system_prompt_injection", SafetyStrictness.MINIMAL),
    (re.compile(r"new\s+instructions?\s*:", re.I),
     "system_prompt_injection", SafetyStrictness.MINIMAL),
    (re.compile(r"you\s+are\s+now\s+(?:a|an|the)\b", re.I),
     "identity_manipulation", SafetyStrictness.MODERATE),
    (re.compile(r"(?:^|\n)\s*\[INST\]", re.I),
     "system_prompt_injection", SafetyStrictness.MINIMAL),
    # Role / privilege escalation
    (re.compile(r"as\s+an?\s+administrator", re.I),
     "role_escalation", SafetyStrictness.MODERATE),
    (re.compile(r"override\s+safety", re.I),
     "role_escalation", SafetyStrictness.MINIMAL),
    (
        re.compile(
            r"bypass\s+(all\s+)?"
            r"(security|safety|filter|restriction|guardrail)", re.I,
        ),
        "role_escalation", SafetyStrictness.MINIMAL,
    ),
    (re.compile(r"(?:sudo|admin)\s+mode", re.I),
     "role_escalation", SafetyStrictness.MODERATE),
    # Encoding / obfuscation tricks
    (re.compile(r"base64[:\s]+[A-Za-z0-9+/]{20,}={0,2}", re.I),
     "encoding_trick", SafetyStrictness.MODERATE),
    (re.compile(r"eval\s*\(", re.I),
     "code_injection", SafetyStrictness.MODERATE),
    (re.compile(r"exec\s*\(", re.I),
     "code_injection", SafetyStrictness.MODERATE),
    # Prompt leaking attempts
    (
        re.compile(
            r"(reveal|show|display|output|print|repeat)\s+(the\s+)?"
            r"(system\s+prompt|initial\s+prompt"
            r"|hidden\s+instructions|your\s+instructions)", re.I,
        ),
        "prompt_leak", SafetyStrictness.MINIMAL,
    ),
    # Jailbreak / DAN patterns
    (re.compile(r"(?:DAN|do\s+anything\s+now)\s+mode", re.I),
     "jailbreak", SafetyStrictness.MINIMAL),
    (
        re.compile(
            r"pretend\s+(?:you\s+(?:are|have)|there\s+(?:are|is))"
            r"\s+no\s+(rules|restrictions|limitations"
            r"|filters|safety)", re.I,
        ),
        "jailbreak", SafetyStrictness.MINIMAL,
    ),
    (
        re.compile(
            r"act\s+as\s+(?:if|though)\s+you"
            r"\s+(?:have\s+no|don'?t\s+have)"
            r"\s+(restrictions|rules|safety|filters)", re.I,
        ),
        "jailbreak", SafetyStrictness.MINIMAL,
    ),
    # Delimiter injection
    (re.compile(r"```\s*system\b", re.I),
     "delimiter_injection", SafetyStrictness.MODERATE),
    (re.compile(r"<\|(?:im_start|system|endoftext)\|>", re.I),
     "delimiter_injection", SafetyStrictness.MINIMAL),
    # Instruction in markdown / HTML
    (re.compile(r"<!--\s*(?:ignore|override|system)", re.I),
     "hidden_instruction", SafetyStrictness.MODERATE),
]

# ── Output safety patterns ──────────────────────────────────────────

_OUTPUT_HARMFUL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"disable\s+all\s+security", re.I),
     "harmful_security_advice"),
    (re.compile(
        r"turn\s+off\s+(?:all\s+)?"
        r"(?:firewall|antivirus|logging|monitoring|encryption)", re.I,
    ), "harmful_security_advice"),
    (re.compile(
        r"remove\s+all\s+(?:NSG|network\s+security\s+group"
        r"|firewall)\s+rules", re.I,
    ), "harmful_security_advice"),
    (re.compile(
        r"(?:make|set)\s+(?:everything|all\s+resources?)"
        r"\s+(?:public|publicly\s+accessible)", re.I,
    ), "harmful_security_advice"),
    (re.compile(
        r"disable\s+(?:Azure\s+)?"
        r"(?:Defender|Security\s+Center|Sentinel)", re.I,
    ), "harmful_security_advice"),
    (re.compile(
        r"store\s+(?:passwords?|secrets?|credentials?)"
        r"\s+in\s+(?:plain\s*text|source\s*code|environment)", re.I,
    ), "harmful_security_advice"),
]

_AZURE_CLOUD_KEYWORDS = re.compile(
    r"\b(?:azure|cloud|infrastructure|deployment|architecture|policy|compliance"
    r"|governance|security|network|storage|compute|database|vm|vnet"
    r"|subscription|resource\s*group|tenant|landing\s*zone|bicep|arm"
    r"|terraform|kubernetes|aks|container|app\s*service|function"
    r"|key\s*vault|monitor|defender|sentinel|identity|rbac|nsg"
    r"|firewall|load\s*balancer|dns|cdn|blob|queue|cosmos"
    r"|sql|redis|service\s*bus|event\s*hub|devops|ci/?cd|pipeline)\b",
    re.I,
)


def _strictness_level(s: SafetyStrictness) -> int:
    """Return an integer severity ordering for strictness."""
    return {"strict": 0, "moderate": 1, "minimal": 2}[s.value]


class ContentSafetyService:
    """Singleton service for content safety checks."""

    def __init__(self) -> None:
        self._config = ContentSafetyConfig()
        # Rate-limit state: {user_id: [(timestamp, ...),]}
        self._user_calls: dict[str, list[float]] = defaultdict(list)
        self._tenant_calls: dict[str, list[float]] = defaultdict(list)
        self._rate_window = 3600  # 1 hour in seconds

    # ── Configuration ───────────────────────────────────────────────

    @property
    def config(self) -> ContentSafetyConfig:
        return self._config

    def update_config(self, new_config: ContentSafetyConfig) -> None:
        self._config = new_config
        logger.info("Content safety config updated: strictness=%s", new_config.strictness)

    # ── Input checking ──────────────────────────────────────────────

    def check_input(
        self,
        text: str,
        strictness: str | SafetyStrictness = "moderate",
    ) -> InputCheckResult:
        """Scan user input for prompt injection patterns.

        Returns an InputCheckResult indicating whether the text is safe,
        any flagged patterns, the sanitized text, and a risk level.
        """
        if isinstance(strictness, str):
            strictness = SafetyStrictness(strictness)

        level = _strictness_level(strictness)
        flagged: list[str] = []

        for pattern, label, min_strictness in _INJECTION_PATTERNS:
            if _strictness_level(min_strictness) >= level and pattern.search(text):
                flagged.append(label)

        # Check for base64-encoded instruction payloads
        flagged.extend(self._check_base64_payloads(text, level))

        # Check for unicode homoglyph tricks
        if self._has_suspicious_unicode(text) and level <= 1:  # moderate+
            flagged.append("unicode_homoglyph")

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_flags: list[str] = []
        for f in flagged:
            if f not in seen:
                seen.add(f)
                unique_flags.append(f)

        risk = self._assess_risk(unique_flags)
        sanitized = self._sanitize_text(text, unique_flags)

        safe = len(unique_flags) == 0

        if not safe:
            self.log_security_event(
                "input_flagged",
                user_id="unknown",  # caller should log with real user_id
                details={
                    "patterns": unique_flags,
                    "risk_level": risk,
                    "text_length": len(text),
                },
            )

        return InputCheckResult(
            safe=safe,
            flagged_patterns=unique_flags,
            sanitized_text=sanitized,
            risk_level=risk,
        )

    # ── Output checking ─────────────────────────────────────────────

    def check_output(self, text: str, feature: str = "general") -> OutputCheckResult:
        """Validate AI output for harmful content and relevance."""
        flags: list[str] = []

        # Check for harmful recommendations
        for pattern, label in _OUTPUT_HARMFUL_PATTERNS:
            if pattern.search(text):
                flags.append(label)

        # Off-topic detection: for policy/architecture features the output
        # should reference Azure / cloud concepts
        if feature in ("policy", "architecture", "chat"):
            if len(text) > 100 and not _AZURE_CLOUD_KEYWORDS.search(text):
                flags.append("off_topic")

        safe = len(flags) == 0
        filtered = text if safe else None

        if not safe:
            self.log_security_event(
                "output_flagged",
                user_id="system",
                details={"flags": flags, "feature": feature, "text_length": len(text)},
            )

        return OutputCheckResult(safe=safe, flags=flags, filtered_text=filtered)

    # ── Rate limiting ───────────────────────────────────────────────

    def check_rate_limit(self, user_id: str, tenant_id: str | None = None) -> bool:
        """Return True if the user/tenant is within rate limits."""
        now = time.monotonic()
        cutoff = now - self._rate_window

        # Prune old entries and check user limit
        self._user_calls[user_id] = [
            t for t in self._user_calls[user_id] if t > cutoff
        ]
        if len(self._user_calls[user_id]) >= self._config.user_rate_limit:
            self.log_security_event(
                "rate_limit_exceeded",
                user_id=user_id,
                details={"scope": "user", "limit": self._config.user_rate_limit},
            )
            return False

        # Tenant limit
        if tenant_id is not None:
            self._tenant_calls[tenant_id] = [
                t for t in self._tenant_calls[tenant_id] if t > cutoff
            ]
            if len(self._tenant_calls[tenant_id]) >= self._config.tenant_rate_limit:
                self.log_security_event(
                    "rate_limit_exceeded",
                    user_id=user_id,
                    details={"scope": "tenant", "tenant_id": tenant_id, "limit": self._config.tenant_rate_limit},
                )
                return False

        # Record call
        self._user_calls[user_id].append(now)
        if tenant_id is not None:
            self._tenant_calls[tenant_id].append(now)

        return True

    def get_rate_limit_status(
        self, user_id: str, tenant_id: str | None = None
    ) -> RateLimitStatus:
        """Return current rate limit counters for a user/tenant."""
        now = time.monotonic()
        cutoff = now - self._rate_window

        # Prune
        self._user_calls[user_id] = [
            t for t in self._user_calls[user_id] if t > cutoff
        ]
        user_used = len(self._user_calls[user_id])
        user_remaining = max(0, self._config.user_rate_limit - user_used)

        tenant_remaining: int | None = None
        if tenant_id is not None:
            self._tenant_calls[tenant_id] = [
                t for t in self._tenant_calls[tenant_id] if t > cutoff
            ]
            tenant_used = len(self._tenant_calls[tenant_id])
            tenant_remaining = max(0, self._config.tenant_rate_limit - tenant_used)

        # Approximate reset time: now + window
        reset_at = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        # Next full hour
        from datetime import timedelta

        reset_at += timedelta(hours=1)

        return RateLimitStatus(
            user_calls_remaining=user_remaining,
            tenant_calls_remaining=tenant_remaining,
            reset_at=reset_at,
        )

    # ── Security event logging ──────────────────────────────────────

    def log_security_event(
        self, event_type: str, user_id: str, details: dict
    ) -> None:
        """Log a security event via Python logging (privacy-friendly)."""
        security_logger.warning(
            "SECURITY_EVENT type=%s user=%s details=%s",
            event_type,
            user_id,
            details,
        )

    # ── Private helpers ─────────────────────────────────────────────

    def _check_base64_payloads(self, text: str, level: int) -> list[str]:
        """Look for base64-encoded strings that decode to suspicious content."""
        flags: list[str] = []
        b64_pattern = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")
        for match in b64_pattern.finditer(text):
            try:
                decoded = base64.b64decode(match.group()).decode("utf-8", errors="ignore").lower()
                if any(
                    kw in decoded
                    for kw in ("ignore previous", "system:", "new instructions", "override")
                ):
                    flags.append("base64_encoded_injection")
                    break
            except Exception:
                continue
        return flags

    def _has_suspicious_unicode(self, text: str) -> bool:
        """Detect common unicode homoglyph abuse.

        Checks for Cyrillic / Greek letters that visually resemble Latin
        characters — a common technique to evade keyword filters.
        """
        # Cyrillic homoglyphs of Latin letters (а е о р с у)
        suspicious_ranges = [
            ("\u0400", "\u04ff"),  # Cyrillic
            ("\u0370", "\u03ff"),  # Greek
            ("\uff00", "\uffef"),  # Fullwidth forms
        ]
        for ch in text:
            for lo, hi in suspicious_ranges:
                if lo <= ch <= hi:
                    return True
        return False

    def _assess_risk(self, flags: list[str]) -> str:
        """Map flag count and severity to a risk level string."""
        if not flags:
            return "none"

        high_severity = {"instruction_override", "system_prompt_injection", "jailbreak", "base64_encoded_injection"}
        medium_severity = {"role_escalation", "identity_manipulation", "delimiter_injection", "prompt_leak"}

        high_count = sum(1 for f in flags if f in high_severity)
        med_count = sum(1 for f in flags if f in medium_severity)

        if high_count >= 2:
            return "critical"
        if high_count >= 1:
            return "high"
        if med_count >= 1:
            return "medium"
        return "low"

    def _sanitize_text(self, text: str, flags: list[str]) -> str:
        """Strip or neutralize detected injection patterns from text.

        For low-risk flags we simply return the original text.
        For higher-risk we strip the offending sequences.
        """
        if not flags:
            return text

        sanitized = text
        for pattern, _label, _min in _INJECTION_PATTERNS:
            sanitized = pattern.sub("[FILTERED]", sanitized)
        return sanitized


# Module-level singleton
content_safety_service = ContentSafetyService()
