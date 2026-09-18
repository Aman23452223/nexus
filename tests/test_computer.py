from nexus.orchestrator import extract_app, extract_computer_target, plan_for


def test_extract_app():
    assert extract_app("nexus whatsapp khol") == "whatsapp"
    assert extract_app("open antigravity") == "antigravity"
    assert extract_app("kuch aur kar") == ""


def test_extract_target_folder():
    t = extract_computer_target(r"antigravity me khol C:\Users\amanc\nexus")
    assert t == r"C:\Users\amanc\nexus"


def test_extract_target_url():
    t = extract_computer_target("chrome me khol https://example.com")
    assert t == "https://example.com"


def test_plan_open():
    assert plan_for("nexus whatsapp khol") == ["computer.open"]
    assert plan_for("screenshot le") == ["computer.screenshot"]
    assert plan_for("open instagram") == ["computer.open"]


def test_site_extract():
    from nexus.orchestrator import extract_site
    assert extract_site("open instagram") == "https://www.instagram.com"
    assert extract_site("gmail khol") == "https://mail.google.com"


def test_unknown_open_fails_honest():
    from nexus import orchestrator
    rep = orchestrator.execute("nexus xqqzzz khol")
    assert rep["results"][0]["status"] == "failed"
    assert rep["status"] == "partial"


def test_type_needs_plan():
    assert plan_for('notepad me "hello" likh') == ["computer.type"]
