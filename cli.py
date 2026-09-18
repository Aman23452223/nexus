"""Command UI slice (PRD §30): outcome in → Done/Changed/Issues/Links out."""
import json
import sys

from nexus.orchestrator import execute


def main():
    args = sys.argv[1:]
    auto_approve = "--yes" in args
    dry_run = "--dry-run" in args  # READ steps always run; mutations preview unless --yes
    intent = " ".join(a for a in args if a not in ("--yes", "--dry-run")) or "Downloads folder organize kar"
    report = execute(intent, dry_run=dry_run, auto_approve=auto_approve)
    print(f"NEXUS report [{report['task_id']}] workspace={report['workspace']} status={report['status']}")
    print(f"Intent: {report['intent']}\nPlan: {' -> '.join(report['plan'])}")
    for r in report["results"]:
        print(f"- {r['tool']}: {r['status']} :: {json.dumps(r['detail'], default=str)[:500]}")
    if report["needs_confirmation"]:
        print("Needs confirmation:")
        for c in report["needs_confirmation"]:
            print(f"  ! {c['tool']}: {c['reason']}")


if __name__ == "__main__":
    main()
