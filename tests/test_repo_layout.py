from __future__ import annotations

from scripts.check_repo_layout import main


def test_repo_layout():
    assert main() == 0
