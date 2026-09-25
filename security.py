"""Scan staged Git blobs, including XLSX contents. Print names only, never matching secrets."""

import getpass
import io
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from dotenv import load_dotenv

PATTERNS = [
    re.compile(rb"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}"),
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def contains_secret(data: bytes, exact_secret: bytes | None = None) -> bool:
    if any(p.search(data) for p in PATTERNS) or (exact_secret and exact_secret in data):
        return True
    if data.startswith(b"PK\x03\x04"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return any(
                contains_secret(archive.read(name), exact_secret) for name in archive.namelist()
            )
    return False


def check_secrets():
    secret = os.environ.get("OPENAI_API_KEY", "").encode() or None
    paths = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
    failed = []
    for raw in filter(None, paths):
        path = raw.decode()
        forbidden = any(
            part == ".env" or (part.startswith(".env.") and part != ".env.example")
            for part in path.split("/")
        )
        data = subprocess.check_output(["git", "show", ":" + path])
        if forbidden or contains_secret(data, secret):
            failed.append(path)
    if failed:
        print("Secret scan failed; remove credentials from these staged files:")
        for path in failed:
            print(path)
        return 1
    print("Staged-file secret scan passed (including XLSX members).")
    return 0


def save_key():
    key = getpass.getpass("OpenAI API key (hidden): ").strip()
    if not key or any(c.isspace() or c in "\"'\\" for c in key):
        raise SystemExit("Invalid key; nothing saved.")
    path = Path(__file__).resolve().parent / ".env"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("OPENAI_API_KEY=" + key + "\nOPENAI_MODEL=gpt-6-astra\n")
    print("Saved to Git-ignored, owner-only .env.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--set-key"]:
        save_key()
    elif sys.argv[1:] == ["--check"]:
        load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
        sys.exit(check_secrets())
    else:
        raise SystemExit("Usage: uv run python security.py --set-key | --check")
