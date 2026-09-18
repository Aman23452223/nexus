from nexus.policy import RiskClass, evaluate
from nexus.vault import redact


def test_publish_needs_confirmation():
    g = evaluate(RiskClass.PUBLISH, "personal")
    assert g.needs_confirmation


def test_read_auto():
    g = evaluate(RiskClass.READ, "personal")
    assert not g.needs_confirmation


def test_destructive_needs_confirmation():
    g = evaluate(RiskClass.DESTRUCTIVE, "personal")
    assert g.needs_confirmation


def test_redact():
    assert redact("key ghp_abc123XYZ here") == "key [REDACTED] here"
    assert redact("tok vcp_hello123 here") == "tok [REDACTED] here"
