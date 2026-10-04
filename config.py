"""Settings. Everything comes from environment variables with safe defaults.

DATASET defaults to "synthetic" so a hosted copy never touches anything else.
"""
import os
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
REFERENCE_DIR = DATA_DIR / "reference"

DATASET = os.environ.get("DATASET", "synthetic")
MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")  # chosen on the tuning reports in P2b; override with MODEL
PROMPT_VERSION = "v1"
ANSWERS = os.environ.get("ANSWERS", "saved")  # "saved" = answers from the final run; "fixture" = hand-written (tests)


def dataset_dir(dataset: str = DATASET) -> Path:
    return DATA_DIR / dataset


def load_dotenv() -> None:
    """Read local variables (such as the API key) from a gitignored .env file, if there is one."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
