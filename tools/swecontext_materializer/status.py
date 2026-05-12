from __future__ import annotations

import json
from pathlib import Path


class StatusStore:
    def __init__(self, path: Path):
        self.path = path
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")

    def mark(self, instance_id: str, stage: str) -> None:
        self._data.setdefault(instance_id, {})
        self._data[instance_id]["stage"] = stage
        self._data[instance_id].pop("error", None)
        self._save()

    def fail(self, instance_id: str, stage: str, error: str) -> None:
        self._data.setdefault(instance_id, {})
        self._data[instance_id]["stage"] = stage
        self._data[instance_id]["error"] = error
        self._save()

    def stage(self, instance_id: str) -> str | None:
        return self._data.get(instance_id, {}).get("stage")

    def error(self, instance_id: str) -> str | None:
        return self._data.get(instance_id, {}).get("error")

    def done(self, instance_id: str, stage: str) -> bool:
        return self.stage(instance_id) == stage and self.error(instance_id) is None

    def all(self) -> dict:
        return dict(self._data)

    def record_activation(self, instance_id: str, payload: dict) -> None:
        self._data.setdefault(instance_id, {})
        self._data[instance_id].update(payload)
        self._data[instance_id]["stage"] = "task_activated"
        self._data[instance_id].pop("error", None)
        self._save()
