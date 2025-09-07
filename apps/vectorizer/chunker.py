from typing import List
from apps.core.types import Doc

def split_markdown(md: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    chunks, i = [], 0
    while i < len(md):
        j = min(len(md), i + max_chars)
        chunks.append(md[i:j])
        i = j - overlap if j - overlap > i else j
    return [c.strip() for c in chunks if c.strip()]

def chunk_docs(docs: List[Doc]) -> List[dict]:
    """Return list of {url,title,ordinal,text}."""
    out = []
    for d in docs:
        for idx, ch in enumerate(split_markdown(d.markdown)):
            out.append({"url": str(d.url), "title": d.title, "ordinal": idx, "text": ch})
    return out
