from __future__ import annotations

import json
from pathlib import Path

from ivd.store import Store

DEFAULT_SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data" / ".state.json"


def load(path: Path = DEFAULT_SNAPSHOT_PATH) -> Store:
    if not path.exists():
        return Store()
    return Store.from_dict(json.loads(path.read_text()))


def save(store: Store, path: Path = DEFAULT_SNAPSHOT_PATH) -> None:
    path.write_text(json.dumps(store.to_dict(), indent=2))
