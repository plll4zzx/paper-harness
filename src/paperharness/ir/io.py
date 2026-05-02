from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from paperharness.ir.schema import ReproKit


def write_yaml(path: Path, data: ReproKit | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = data.model_dump(mode="json") if isinstance(data, ReproKit) else data
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def read_yaml(path: Path) -> ReproKit:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ReproKit.model_validate(raw)
