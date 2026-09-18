"""Policy engine (PRD §23, Appendix B). Policy over interruption."""
from dataclasses import dataclass
from enum import Enum


class RiskClass(str, Enum):
    READ = "read"
    REVERSIBLE = "reversible"
    PUBLISH = "publish"
    FINANCIAL = "financial"
    DESTRUCTIVE = "destructive"
    SECURITY = "security"


@dataclass
class Gate:
    needs_confirmation: bool
    reason: str


CONFIRM_ALWAYS = {RiskClass.FINANCIAL, RiskClass.DESTRUCTIVE, RiskClass.SECURITY}
CONFIRM_BY_DEFAULT = {RiskClass.PUBLISH}


def evaluate(risk: RiskClass, workspace: str, dry_run: bool = False) -> Gate:
    if dry_run and risk is not RiskClass.READ:
        # dry-run previews mutations but never blocks observation
        return Gate(True, "dry-run mode: preview required")
    if risk in CONFIRM_ALWAYS:
        return Gate(True, f"{risk.value}: high-impact, confirmation required")
    if risk in CONFIRM_BY_DEFAULT:
        return Gate(True, f"{risk.value}: preview/approval required by default")
    return Gate(False, f"{risk.value}: auto-execute allowed in {workspace}")
