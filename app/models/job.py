from dataclasses import dataclass, field
from pathlib import Path

from .enums import OutputFormat


@dataclass
class OCRJob:
    source_path: Path
    output_format: OutputFormat
    language: str = "ch"
    enable_preprocess: bool = False
    preserve_layout: bool = False
