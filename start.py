"""Start the self-hosted ThoughtHarbor Compose stack on any host OS."""

import os
import subprocess
import webbrowser
from pathlib import Path


DEFAULT_APPLICATION_URL = "http://localhost:3000"


def main() -> int:
    repository_root = Path(__file__).resolve().parent
    result = subprocess.run(
        ["docker", "compose", "up", "-d", "--build"],
        cwd=repository_root,
        check=False,
    )
    if result.returncode == 0:
        webbrowser.open(os.environ.get("THOUGHTHARBOR_URL", DEFAULT_APPLICATION_URL))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
