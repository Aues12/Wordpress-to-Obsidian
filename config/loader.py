import json
from pathlib import Path


def load_config(config_path: str = "config.json") -> dict:
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
