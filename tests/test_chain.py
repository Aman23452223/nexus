from nexus.orchestrator import extract_send, plan_for


def test_chain_open_send():
    assert plan_for("open whatsapp and send hey to chirag") == [
        "computer.open", "computer.whatsapp_send"]


def test_send_parse():
    info = extract_send('open whatsapp and send "hey, kya haal" to chirag')
    assert info["contact"] == "chirag"
    assert info["message"] == "hey, kya haal"


def test_send_parse_unquoted():
    info = extract_send("send hey msg to chirag on whatsapp")
    assert info["contact"] == "chirag"
    assert "hey" in info["message"]


def test_send_unknown_contact_gated(monkeypatch):
    import os
    from nexus import orchestrator
    monkeypatch.delenv("NEXUS_TRUSTED_CONTACTS", raising=False)
    rep = orchestrator.execute("open whatsapp and send hey to chirag")
    send = [r for r in rep["results"] if r["tool"] == "computer.whatsapp_send"][0]
    assert send["status"] == "awaiting-confirmation"


def test_start_search_fallback_plan():
    assert plan_for("open notepad") == ["computer.open"]
