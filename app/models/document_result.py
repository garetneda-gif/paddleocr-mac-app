from dataclasses import dataclass, field
from pathlib import Path

from .enums import BlockType


@dataclass
class BlockResult:
    block_type: BlockType
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2) pixels
    text: str
    confidence: float | None = None
    html: str | None = None
    markdown: str | None = None
    table_cells: list[list[str]] | None = None


@dataclass
class PageResult:
    page_index: int
    width: int
    height: int
    blocks: list[BlockResult] = field(default_factory=list)


@dataclass
class DocumentResult:
    source_path: Path
    page_count: int
    pages: list[PageResult] = field(default_factory=list)
    plain_text: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
