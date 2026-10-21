from __future__ import annotations

from pathlib import Path

from src.pipelines.apply_governance import render_sql


def test_render_sql_substitutes_and_splits():
    template = Path("src/pipelines/governance.sql").read_text(encoding="utf-8")
    stmts = render_sql(template, "workspace", "retail_dev")
    assert stmts
    joined = "\n".join(stmts)
    assert "workspace.retail_dev.gold_customer_360" in joined
    assert "${catalog}" not in joined
    assert "mask_email" in joined
