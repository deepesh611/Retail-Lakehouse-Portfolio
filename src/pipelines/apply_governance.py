"""Apply governance SQL (tags, mask UDF, secured views) against gold tables."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _default_sql_file() -> str:
    # spark_python_task on Databricks exec()s the script, so __file__ may be missing.
    try:
        return str(Path(__file__).with_name("governance.sql"))
    except NameError:
        return str(Path(sys.argv[0]).resolve().with_name("governance.sql"))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--sql-file", default=None)
    args = p.parse_args()
    if not args.sql_file:
        args.sql_file = _default_sql_file()
    return args


def render_sql(template: str, catalog: str, schema: str) -> list[str]:
    text = template.replace("${catalog}", catalog).replace("${schema}", schema)
    statements: list[str] = []
    buf: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            buf = []
    if buf:
        stmt = "\n".join(buf).strip().rstrip(";").strip()
        if stmt:
            statements.append(stmt)
    return statements


def main() -> None:
    args = _parse_args()
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    sql_path = Path(args.sql_file)
    if not sql_path.exists():
        raise FileNotFoundError(
            f"governance SQL not found at {sql_path}. "
            "Pass --sql-file explicitly if needed."
        )
    sql_text = sql_path.read_text(encoding="utf-8")
    for stmt in render_sql(sql_text, args.catalog, args.schema):
        print(f"Running: {stmt[:120]}...")
        spark.sql(stmt)
    print({"status": "ok", "catalog": args.catalog, "schema": args.schema})


if __name__ == "__main__":
    main()
