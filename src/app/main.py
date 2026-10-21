"""Entrypoint helpers: run FastAPI (API) or rely on app.yaml for Streamlit UI.

For local dual-process demos:
  uvicorn api:app --host 0.0.0.0 --port 8080
  streamlit run streamlit_app.py --server.port 8000

Databricks Apps uses app.yaml (Streamlit). The API can be mounted alongside
or run as a separate process — see docs/DEMO_SCRIPT.md.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_api(host: str = "0.0.0.0", port: int = 8080) -> None:
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=str(Path(__file__).parent),
    )


if __name__ == "__main__":
    run_api()
