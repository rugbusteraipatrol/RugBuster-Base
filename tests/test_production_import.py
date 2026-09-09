"""Import the app the way production does, not the way a test finds convenient.

This file exists because of a boot crash it would have caught. Adding sibling
modules under api/ and importing them by bare name worked in every test --
because the tests put api/ on sys.path themselves -- and failed in production,
where gunicorn runs `api.server:app` and imports the file as part of a package
with api/ left off the path. The service 502'd until api/ was added to sys.path
inside server.py.

A test that arranges the import differently from the deployment is testing a
program that does not exist.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_app_imports_as_a_package_from_the_repo_root():
    """Exactly `api.server:app`, with nothing added to sys.path first."""
    result = subprocess.run(
        [sys.executable, "-c",
         "import importlib; m = importlib.import_module('api.server'); "
         "assert m.app is not None; print('ok')"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (
        "gunicorn imports the app this way; if this fails the service will not "
        f"boot.\nstdout: {result.stdout}\nstderr: {result.stderr[-2000:]}"
    )


def test_the_start_command_is_supplied_by_the_service_not_this_repo():
    """Worth knowing, because it limits what this test can promise.

    railway.json here runs `sh -c "$START_COMMAND"`, and START_COMMAND lives in
    the Railway service variables -- today
    `gunicorn --bind 0.0.0.0:$PORT api.server:app` on base-api. An ordinary
    environment variable is read reliably, unlike the RAILWAY_CONFIG_PATH that
    the BNB service lost on a rebuild while reporting SUCCESS.

    But the command is not in git, so the test above proves the app imports the
    way the deployment *currently* invokes it, and cannot prove the deployment
    still invokes it that way. The Procfile is a leftover and is not what runs.
    """
    import json

    config = json.loads((ROOT / "railway.json").read_text(encoding="utf-8-sig"))
    assert "$START_COMMAND" in config["deploy"]["startCommand"]


def test_the_response_helpers_are_importable_beside_the_app():
    for name in ("build_identity", "evidence", "plain_language"):
        assert importlib.import_module(name)
