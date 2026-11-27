from pathlib import Path


def test_dashboard_copies_are_identical():
    root = Path(__file__).resolve().parents[1]
    assert (root / 'docs/index.html').read_bytes() == (root / 'dashboard/index.html').read_bytes()
