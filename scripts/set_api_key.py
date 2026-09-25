"""Save a key locally without terminal echo, command-line arguments, or shell history."""

import getpass
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
key = getpass.getpass("OpenAI API key (hidden): ").strip()
if not key or any(c.isspace() for c in key) or any(c in key for c in "\"'\\"):
    raise SystemExit("No valid key supplied; nothing saved.")
path = root / ".env"
if path.is_symlink():
    raise SystemExit("Refusing to write through a symlink.")
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.fchmod(fd, 0o600)
with os.fdopen(fd, "w") as f:
    f.write("OPENAI_API_KEY=" + key + "\nOPENAI_MODEL=gpt-6-astra\n")
print("Saved to ignored .env with owner-only permissions. Key was not displayed.")
