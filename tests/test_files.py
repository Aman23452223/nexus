from nexus.tools import files


def test_categorize(tmp_path):
    (tmp_path / "setup.exe").write_bytes(b"x" * 10)
    (tmp_path / "photo.jpg").write_bytes(b"y" * 10)
    (tmp_path / "notes.pdf").write_bytes(b"z" * 10)
    scan = files.scan_downloads(str(tmp_path))
    assert scan["file_count"] == 3
    moves = files.plan_moves(scan)
    cats = {m["category"] for m in moves}
    assert cats == {"Installers", "Images", "Documents"}


def test_duplicates_reported(tmp_path):
    (tmp_path / "a.zip").write_bytes(b"dup" * 100)
    (tmp_path / "b.zip").write_bytes(b"dup" * 100)
    scan = files.scan_downloads(str(tmp_path))
    assert len(scan["duplicate_groups"]) == 1


def test_dry_run_moves_nothing(tmp_path):
    (tmp_path / "setup.exe").write_bytes(b"x")
    scan = files.scan_downloads(str(tmp_path))
    moves = files.plan_moves(scan)
    out = files.apply_moves(moves, dry_run=True)
    assert out["mode"] == "dry-run" and out["pending_moves"] == 1
    assert (tmp_path / "setup.exe").exists()  # untouched


def test_apply_moves_in_tmp(tmp_path):
    (tmp_path / "setup.exe").write_bytes(b"x")
    scan = files.scan_downloads(str(tmp_path))
    moves = files.plan_moves(scan)
    out = files.apply_moves(moves, dry_run=False)
    assert out["moved"] == 1 and not out["failed"]
    assert (tmp_path / "Installers" / "setup.exe").exists()
