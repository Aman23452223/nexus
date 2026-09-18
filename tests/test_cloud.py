import os

from nexus.tools import computer


def test_cloud_open_needs_laptop(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    try:
        computer.open_app("whatsapp")
        assert False, "should have raised"
    except computer.NeedsLaptop as e:
        assert "cli.py" in str(e)


def test_orchestrator_maps_needs_laptop(monkeypatch):
    from nexus import orchestrator

    def raiser(name, target=""):
        raise computer.NeedsLaptop("open whatsapp")

    monkeypatch.setattr(computer, "open_app", raiser)
    rep = orchestrator.execute("nexus whatsapp khol")
    assert rep["results"][0]["status"] == "needs-laptop"
    assert rep["status"] == "partial"
