"""Export the canonical FastAPI OpenAPI document for client generation."""

import json
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root / "src"))

from thoughtharbor.api.main import app  # noqa: E402, I001


if __name__ == "__main__":
    json.dump(app.openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
