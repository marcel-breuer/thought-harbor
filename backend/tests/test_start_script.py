import importlib.util
from pathlib import Path
from unittest.mock import patch

START_SCRIPT = Path(__file__).parents[2] / "start.py"
SPEC = importlib.util.spec_from_file_location("thought_harbor_start", START_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
start = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(start)


def test_start_script_runs_compose_from_repository_root() -> None:
    with (
        patch.object(start.subprocess, "run") as run,
        patch.object(start.webbrowser, "open") as open_browser,
    ):
        run.return_value.returncode = 0

        assert start.main() == 0

    run.assert_called_once_with(
        ["docker", "compose", "up", "-d", "--build"],
        cwd=START_SCRIPT.parent,
        check=False,
    )
    open_browser.assert_called_once_with(start.DEFAULT_APPLICATION_URL)


def test_start_script_does_not_open_browser_when_compose_fails() -> None:
    with (
        patch.object(start.subprocess, "run") as run,
        patch.object(start.webbrowser, "open") as open_browser,
    ):
        run.return_value.returncode = 1

        assert start.main() == 1

    open_browser.assert_not_called()
