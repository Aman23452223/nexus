"""Typed tool registry (PRD §27). Each tool declares risk + verification."""
from dataclasses import dataclass
from ..policy import RiskClass

@dataclass
class ToolSpec:
    name: str
    domain: str
    risk: RiskClass
    verification: str
    reversible: bool = True


REGISTRY = {
    "desktop.list_dir": ToolSpec("desktop.list_dir", "computer", RiskClass.READ, "dir listing returned"),
    "desktop.run_cmd": ToolSpec("desktop.run_cmd", "computer", RiskClass.REVERSIBLE, "exit code 0 + output"),
    "files.scan": ToolSpec("files.scan", "computer", RiskClass.READ, "scan counts + dup groups returned"),
    "files.organize": ToolSpec("files.organize", "computer", RiskClass.REVERSIBLE, "moves applied or dry-run preview"),
    "browser.open": ToolSpec("browser.open", "browser", RiskClass.READ, "URL + title captured"),
    "devops.gh_status": ToolSpec("devops.gh_status", "developer", RiskClass.READ, "gh auth status ok"),
    "devops.vercel_inspect": ToolSpec("devops.vercel_inspect", "developer", RiskClass.READ, "project list returned"),
    "devops.health_check": ToolSpec("devops.health_check", "developer", RiskClass.READ, "HTTP 2xx/3xx + title captured"),
    "devops.vercel_deploy": ToolSpec("devops.vercel_deploy", "developer", RiskClass.PUBLISH, "deployment URL live + health 200"),
}
