"""Tiny JSON registry of uploaded documents (name, size, chunk ids)."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


class Registry:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._items: dict[str, dict] = {}
        if path.exists():
            self._items = json.loads(path.read_text())

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._items, indent=2))

    def add(self, doc_id: str, filename: str, size: int, chunk_ids: list[str]) -> dict:
        with self._lock:
            item = {
                "id": doc_id,
                "filename": filename,
                "size": size,
                "chunks": len(chunk_ids),
                "chunk_ids": chunk_ids,
                "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            self._items[doc_id] = item
            self._flush()
            return item

    def remove(self, doc_id: str) -> dict | None:
        with self._lock:
            item = self._items.pop(doc_id, None)
            self._flush()
            return item

    def get(self, doc_id: str) -> dict | None:
        return self._items.get(doc_id)

    def list(self) -> list[dict]:
        return [{k: v for k, v in i.items() if k != "chunk_ids"} for i in self._items.values()]
