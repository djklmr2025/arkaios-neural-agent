"""
ARKAIOS Safety Guard
────────────────────
Evaluates agent actions before execution and classifies them by risk level.
Blocks absolutely dangerous operations and flags sensitive ones for user confirmation.
"""

import re
from typing import List, Dict, Tuple
from utils.action_logger import log_action

# ─────────────────────────────────────────────────────────────────────────────
# BLOCKLIST — these actions are NEVER allowed, no matter what
# ─────────────────────────────────────────────────────────────────────────────
BLOCKED_PATTERNS = [
    # Destructive file system commands
    r"\brm\s+-rf\b",
    r"\bformat\s+[a-zA-Z]:",
    r"\bdel\s+/[sS]\b",
    r"\brmdir\s+/[sS]\b",
    r"\bdiskpart\b",
    r"\bfdisk\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",

    # Privilege escalation
    r"\bsudo\s+rm\b",
    r"\bsudo\s+mkfs\b",
    r"\bchmod\s+777\b",
    r"\bchmod\s+-R\s+777\b",

    # Credential / financial keywords
    r"\bprivate[_\s]?key\b",
    r"\bseed[_\s]?phrase\b",
    r"\bwallet[_\s]?password\b",
    r"\bsend[_\s]?(eth|btc|usdt|money|funds)\b",
    r"\btransfer[_\s]?funds\b",
    r"\bwire[_\s]?transfer\b",

    # Shell escape / arbitrary code
    r"\beval\s+\(",
    r"\bexec\s+\(",
    r"\bos\.system\s*\(",
    r"\bsubprocess\.call\s*\(",
    r"\bpowershell\s+-enc\b",
    r"\bcmd\s+/c\s+del\b",
]

# ─────────────────────────────────────────────────────────────────────────────
# SENSITIVE PATTERNS — require user confirmation before proceeding (MEDIUM/HIGH)
# ─────────────────────────────────────────────────────────────────────────────
HIGH_RISK_PATTERNS = [
    # File deletion
    r"\bdelete\b.*\bfile\b",
    r"\bremove\b.*\bfile\b",
    r"\btrash\b.*\bfile\b",
    r"\.exe\b",
    r"\.bat\b",
    r"\.ps1\b",
    r"\.sh\b",
    r"regedit\b",
    r"reg\s+(add|delete|import)\b",
]

MEDIUM_RISK_PATTERNS = [
    # Sending messages / posts
    r"\bsend\b.*\b(email|mail|message|dm|tweet|post)\b",
    r"\bpublish\b",
    r"\bsubmit\b.*\bform\b",
    r"\bpurchase\b",
    r"\bbuy\b.*\bwith\b",
    r"\bcheckout\b",
    # System-wide changes
    r"\binstall\b.*\bsoftware\b",
    r"\buninstall\b",
    r"\bsystem\s+settings\b",
    r"\bcontrol\s+panel\b",
]


def _text_from_action(action: Dict) -> str:
    """Extracts all text content from an action dict for pattern matching."""
    parts = [action.get("action", "")]
    params = action.get("params", {})
    if isinstance(params, dict):
        for v in params.values():
            if isinstance(v, str):
                parts.append(v)
    return " ".join(parts).lower()


def is_blocked(action: Dict) -> Tuple[bool, str]:
    """
    Returns (True, reason) if the action matches a hard-blocked pattern.
    These are NEVER executed regardless of user confirmation.
    """
    text = _text_from_action(action)
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Blocked pattern matched: `{pattern}`"
    return False, ""


def risk_level(action: Dict) -> str:
    """
    Returns 'LOW', 'MEDIUM', or 'HIGH' based on the action content.
    HIGH → requires explicit user confirmation
    MEDIUM → soft warning, confirmation recommended
    LOW → safe to execute without confirmation
    """
    text = _text_from_action(action)

    for pattern in HIGH_RISK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "HIGH"

    for pattern in MEDIUM_RISK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "MEDIUM"

    return "LOW"


def evaluate_actions(actions: List[Dict]) -> Dict:
    """
    Evaluates a list of actions from the agent before execution.

    Returns:
    {
        "safe_to_execute": bool,
        "requires_confirmation": bool,
        "blocked": bool,
        "blocked_reason": str | None,
        "risk_level": "LOW" | "MEDIUM" | "HIGH",
        "flagged_actions": list[dict]  # actions that were HIGH/MEDIUM risk
    }
    """
    flagged = []
    overall_risk = "LOW"
    blocked = False
    blocked_reason = None

    for action in actions:
        # Check hard block first
        is_block, reason = is_blocked(action)
        if is_block:
            blocked = True
            blocked_reason = reason
            log_action("safety.blocked", {"action": action, "reason": reason}, status="blocked")
            break

        level = risk_level(action)
        if level == "HIGH":
            overall_risk = "HIGH"
            flagged.append({"action": action, "risk": "HIGH"})
            log_action("safety.requires_confirmation", {"action": action, "risk": "HIGH"}, status="warning")
        elif level == "MEDIUM" and overall_risk != "HIGH":
            overall_risk = "MEDIUM"
            flagged.append({"action": action, "risk": "MEDIUM"})
            log_action("safety.requires_confirmation", {"action": action, "risk": "MEDIUM"}, status="warning")

    if blocked:
        return {
            "safe_to_execute": False,
            "requires_confirmation": False,
            "blocked": True,
            "blocked_reason": blocked_reason,
            "risk_level": "BLOCKED",
            "flagged_actions": [],
        }

    requires_confirmation = overall_risk in ("HIGH", "MEDIUM")

    return {
        "safe_to_execute": not requires_confirmation,
        "requires_confirmation": requires_confirmation,
        "blocked": False,
        "blocked_reason": None,
        "risk_level": overall_risk,
        "flagged_actions": flagged,
    }
