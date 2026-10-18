"""Loaded deployment artifacts for the diet detector."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DietDetector:
    model: Any
    class_names: dict[int, str]
    metadata: dict
