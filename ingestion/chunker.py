from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict
import re


def clean_text(text: str) -> str:
    """
    Clean and normalize text from crawler
    """
    text = re.sub(r"\s+", " ", text)
    text = text.replace("\n", " ").replace("\t", " ")
    return text.strip()


def is_valid_chunk(chunk: str) -> bool:
    """
    Filter out low-quality chunks
    """
    if len(chunk.strip()) < 80:
        return False
    if len(re.findall(r"[a-zA-Z]", chunk)) < 30:
        return False
    return True


def get_section_hint(text: str) -> str:
    """
    Extract lightweight semantic hints
    """
    text_lower = text.lower()
    if any(k in text_lower for k in ["admission", "apply", "enroll"]):
        return "admissions"
    elif any(k in text_lower for k in ["fee", "tuition", "cost"]):
        return "fees"
    elif any(k in text_lower for k in ["curriculum", "academic", "learning"]):
        return "curriculum"
    elif any(k in text_lower for k in ["facility", "campus", "infrastructure"]):
        return "facilities"
    elif any(k in text_lower for k in ["sports", "activity", "extra"]):
        return "activities"
    else:
        return "general"


def chunk_text(text: str) -> list[str]:
    """
    Simple chunking for a single text block
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=120,
        separators=["\n\n", "\n", ". ", "? ", "! ", " "]
    )
    text = clean_text(text)
    chunks = [c for c in splitter.split_text(text) if is_valid_chunk(c)]
    return chunks


def chunk_documents(pages: List[Dict]) -> List[Dict]:
    """
    Chunk multiple pages from crawler output
    """
    all_chunks = []

    for page in pages:
        text = clean_text(page.get("content", ""))
        if not text:
            continue

        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):
            section = get_section_hint(chunk)
            all_chunks.append({
                "content": chunk,
                "url": page["url"],
                "chunk_id": i,
                "section": section,
                "length": len(chunk)
            })

    return all_chunks