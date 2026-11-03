from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Post:
    """
    Core content object used across the pipeline.

    A Post represents a single piece of content after it has entered
    the library, regardless of where it originally came from
    (WordPress API, imported JSON, markdown file, etc.).
    """
    title: str = ""
    content: str = ""
    excerpt: str = ""
    date: Optional[str] = None
    slug: Optional[str] = None

    frontmatter: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    source_path: Optional[str] = None
    source_type: Optional[str] = None


@dataclass
class DocumentUnit:
    """
    Write-ready output object.

    A DocumentUnit is produced by the assembler layer and consumed
    by the writer layer.
    """
    filename: str
    content: str

    frontmatter: str = ""
    title: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


class Link:
    def __init__(self, target, link_type, confidence=1.0, source="parser", reason=None):
        self.target = target            # slug / id
        self.link_type = link_type      # "hard" | "soft"
        self.confidence = confidence    # 0–1
        self.source = source            # "parser" | "llm"
        self.reason = reason            # kısa açıklama (soft için)
