"""Write openapi.json for client codegen. Run via `make openapi`."""
from __future__ import annotations

import json
from pathlib import Path

from app.main import create_app


def main() -> None:
    spec = create_app().openapi()
    out = Path(__file__).resolve().parents[1] / "openapi.json"
    out.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
