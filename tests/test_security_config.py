"""Security configuration: the app must refuse to start without a real JWT secret,
and no credentials may live in the repository."""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VALID_KEY = "k" * 16 + "-test-only-not-a-real-secret-" + "z" * 8


def run_python(code: str, key: str | None, *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET_KEY"}
    if key is not None:
        env["JWT_SECRET_KEY"] = key
    return subprocess.run(
        [sys.executable, *(["-c", code] if code else []), *args],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
    )


IMPORT_JWT = "import src.auth.jwt_utils"


@pytest.mark.parametrize("key", [
    None,
    "",
    "short-key",
    "your-super-secret-jwt-key-change-this-in-production",
    "development-secret-key-change-in-production",
])
def test_jwt_utils_rejects_missing_short_or_placeholder_key(key):
    result = run_python(IMPORT_JWT, key)
    assert result.returncode != 0
    assert "JWT_SECRET_KEY must be set" in result.stderr


def test_jwt_utils_signs_and_verifies_with_a_valid_key():
    code = (
        "from src.auth.jwt_utils import create_access_token, verify_token\n"
        "token = create_access_token({'sub': 'someone'})\n"
        "assert verify_token(token)['sub'] == 'someone'\n"
        "assert verify_token(token + 'x') is None\n"
    )
    result = run_python(code, VALID_KEY)
    assert result.returncode == 0, result.stderr


def test_start_script_exits_without_key_instead_of_using_a_fallback():
    pytest.importorskip("uvicorn")
    result = run_python("", None, "start.py")
    assert result.returncode == 1
    assert "JWT_SECRET_KEY is not set" in result.stdout
    assert "Starting uvicorn" not in result.stdout


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def test_no_code_assigns_a_default_jwt_secret():
    pattern = re.compile(r"""os\.environ\[\s*["']JWT_SECRET_KEY["']\s*\]\s*=|os\.environ\.setdefault\(\s*["']JWT_SECRET_KEY""")
    # tests/ sets a throwaway key on purpose; application code must not.
    app_code = [f for f in tracked_files() if f.endswith(".py") and not f.startswith("tests/")]
    offenders = [f for f in app_code if pattern.search((ROOT / f).read_text(encoding="utf-8"))]
    assert offenders == []


def test_no_credentials_files_are_tracked():
    tracked = tracked_files()
    assert [f for f in tracked if "user_credentials" in f or f.startswith("credentials/")] == []
    for generated in ["scripts/user_credentials.json", "credentials/user_credentials_x.json"]:
        assert subprocess.run(["git", "check-ignore", "-q", generated], cwd=ROOT).returncode == 0, generated


def test_no_shared_default_passwords_in_tracked_files():
    literal = re.compile(r"\b(?:admin|password)\d{3}\b")
    offenders = []
    for f in tracked_files():
        path = ROOT / f
        if path.suffix in {".py", ".md", ".yml", ".yaml", ".toml", ".json", ".txt", ".env", ".example", ".sh", ".bat"}:
            if literal.search(path.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(f)
    assert offenders == []


def test_env_example_and_compose_ship_no_jwt_secret():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^JWT_SECRET_KEY=\s*$", env_example, re.M)
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert re.search(r"JWT_SECRET_KEY=\$\{JWT_SECRET_KEY:\?", compose)


def test_seed_passwords_are_random_per_account(monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    from seed_passwords import seed_password

    monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)
    values = {seed_password() for _ in range(50)}
    assert len(values) == 50 and min(map(len, values)) >= 16
    assert seed_password("SEED_ADMIN_PASSWORD") not in values
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "chosen-by-the-operator")
    assert seed_password("SEED_ADMIN_PASSWORD") == "chosen-by-the-operator"


def test_debug_endpoint_reveals_no_part_of_the_database_url():
    code = (
        "from fastapi.testclient import TestClient\n"
        "import main\n"
        "body = TestClient(main.app).get('/debug').json()\n"
        "assert 'database_url_prefix' not in body, body\n"
        "assert 'operator' not in str(body), body\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60,
        env={**{k: v for k, v in os.environ.items() if k != "JWT_SECRET_KEY"},
             "JWT_SECRET_KEY": VALID_KEY, "DATABASE_URL": "postgresql://operator:pw@db.invalid/x", "SENTRY_DSN": ""},
    )
    assert result.returncode == 0, result.stderr[-2000:]
