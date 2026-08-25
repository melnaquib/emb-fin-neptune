from __future__ import annotations

import json
from pathlib import Path

from ivd.models import Invoice

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "invoices.sample.json"


class JsonFileSource:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self._path = path

    async def fetch(self) -> list[Invoice]:
        raw = json.loads(self._path.read_text())
        return [Invoice.model_validate(item) for item in raw]
