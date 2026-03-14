from enum import Enum


class BlockType(str, Enum):
    TITLE = "title"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    CAPTION = "caption"
    FORMULA = "formula"
    FIGURE = "figure"
    OTHER = "other"


class OutputFormat(str, Enum):
    TXT = "txt"
    PDF = "pdf"
    WORD = "word"
    HTML = "html"
    EXCEL = "excel"
    RTF = "rtf"
