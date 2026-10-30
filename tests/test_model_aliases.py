from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path("src/app").resolve()))

from services import _normalize_model_aliases  # noqa: E402


def test_aliases_dict():
    assert _normalize_model_aliases({"champion": "3", "challenger": 2}) == {
        "champion": "3",
        "challenger": "2",
    }


def test_aliases_objects():
    raw = [SimpleNamespace(alias="champion", version="1")]
    assert _normalize_model_aliases(raw) == {"champion": "1"}


def test_aliases_empty():
    assert _normalize_model_aliases(None) == {}
    assert _normalize_model_aliases([]) == {}
