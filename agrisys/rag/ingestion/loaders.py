"""Document Loaders for RAG Ingestion Pipeline.

Fulfills §10.1: Supports PDF, HTML, CSV, and TXT sources
with clean extraction and robust error handling.
"""

from pathlib import Path
from typing import List, Optional
import csv
import io
import re
from agrisys.rag.ingestion.models import Document


class DocumentLoader:
    """Unified document loader across multiple formats."""

    @classmethod
    def load(cls, file_path: str | Path, source_name: Optional[str] = None) -> List[Document]:
        """Load a file and return one or more Document instances."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return cls._load_pdf(path, source_name)
        elif suffix in [".html", ".htm"]:
            return cls._load_html(path, source_name)
        elif suffix == ".csv":
            return cls._load_csv(path, source_name)
        elif suffix in [".txt", ".md", ".json"]:
            return cls._load_txt(path, source_name)
        else:
            # Fallback to plain text
            return cls._load_txt(path, source_name)

    @staticmethod
    def _load_pdf(path: Path, source_name: Optional[str]) -> List[Document]:
        text_content = ""
        # Try pypdf or pypdf2 if available
        try:
            import pypdf  # type: ignore
            reader = pypdf.PdfReader(str(path))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n\n"
        except Exception:
            # Fallback byte scanner for plain readable text streams
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                matches = re.findall(rb"\(([\w\s,.:;'-]+)\)\s*Tj", raw)
                text_content = " ".join([m.decode("latin1", errors="ignore") for m in matches])
            except Exception:
                text_content = ""

        return [
            Document(
                content=text_content.strip(),
                metadata={"source_path": str(path), "format": "pdf", "source": source_name or "icar"},
                source_path=str(path),
            )
        ]

    @staticmethod
    def _load_html(path: Path, source_name: Optional[str]) -> List[Document]:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        # Clean HTML tags and scripts
        cleaned = re.sub(r"<(script|style).*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return [
            Document(
                content=cleaned,
                metadata={"source_path": str(path), "format": "html", "source": source_name or "icar"},
                source_path=str(path),
            )
        ]

    @staticmethod
    def _load_csv(path: Path, source_name: Optional[str]) -> List[Document]:
        docs: List[Document] = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                line_parts = [f"{k}: {v}" for k, v in row.items() if v and v.strip()]
                content = " | ".join(line_parts)
                docs.append(
                    Document(
                        content=content,
                        metadata={
                            "source_path": str(path),
                            "format": "csv",
                            "row_index": i,
                            "source": source_name or "agmarknet",
                            **row,
                        },
                        source_path=str(path),
                    )
                )
        return docs

    @staticmethod
    def _load_txt(path: Path, source_name: Optional[str]) -> List[Document]:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [
            Document(
                content=content.strip(),
                metadata={"source_path": str(path), "format": "txt", "source": source_name or "kcc"},
                source_path=str(path),
            )
        ]
