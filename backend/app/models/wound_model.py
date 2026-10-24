"""Inference adapter boundaries for explicitly configured, trusted models.

The workflow uses segmentation masks, without wound size or depth measurements.
The user will define the healing assessment and graph comparison method later.
Keep model results/version/provenance separate from immutable uploaded originals.
Factories receive weights_path: Path, model_version: str, parameters: dict.
Adapters own architecture loading, exact training preprocessing and postprocessing.
Return an existing, complete image mask aligned to the original image pixels;
the service copies it into private storage without guessing thresholds or labels.
The adapter owns and must clean up its working files; never modify input files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol


@dataclass(frozen=True)
class SegmentationResult:
    mask_path: Path
    model_version: str


@dataclass(frozen=True)
class TissueResult:
    mask_path: Path
    model_version: str


@dataclass(frozen=True)
class HealingResult:
    model_version: str
    outputs: Mapping[str, float | str]


class WoundSegmentationAdapter(Protocol):
    def predict(self, image_path: Path) -> SegmentationResult: ...


class TissueSegmentationAdapter(Protocol):
    def predict(self, image_path: Path, wound_mask: Path) -> TissueResult: ...


class HealingAnalysisAdapter(Protocol):
    def predict(self, visits: list[Mapping]) -> HealingResult: ...
