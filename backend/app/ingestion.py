"""Turn uploaded files into LangChain Documents.

PDF / TXT / MD are split with a recursive splitter.
CSV / XLSX are handled with Pandas: one schema+statistics document, plus row batches
rendered as "column: value" text so questions about tabular data can be answered.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

SUPPORTED = {".pdf", ".txt", ".md", ".csv", ".xlsx"}


def _splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def load_pdf(data: bytes) -> list[tuple[str, dict]]:
    reader = PdfReader(io.BytesIO(data))
    return [
        (page.extract_text() or "", {"page": i + 1})
        for i, page in enumerate(reader.pages)
    ]


def load_text(data: bytes) -> list[tuple[str, dict]]:
    return [(data.decode("utf-8", errors="ignore"), {})]


def load_table(data: bytes, ext: str, rows_per_chunk: int) -> list[tuple[str, dict]]:
    """Pandas-based loader for CSV / XLSX."""
    df = pd.read_csv(io.BytesIO(data)) if ext == ".csv" else pd.read_excel(io.BytesIO(data))
    df = df.dropna(how="all").reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]

    parts: list[tuple[str, dict]] = []

    summary = [f"Table with {len(df)} rows and {len(df.columns)} columns."]
    summary.append("Columns and types: " + ", ".join(f"{c} ({t})" for c, t in df.dtypes.astype(str).items()))
    numeric = df.select_dtypes("number")
    if not numeric.empty:
        summary.append("Numeric summary:\n" + numeric.describe().round(2).to_string())
    for col in df.select_dtypes(exclude="number").columns[:5]:
        top = df[col].value_counts().head(5)
        summary.append(f"Top values of {col}: " + ", ".join(f"{k} ({v})" for k, v in top.items()))
    parts.append(("\n".join(summary), {"section": "summary"}))

    for start in range(0, len(df), rows_per_chunk):
        block = df.iloc[start : start + rows_per_chunk]
        lines = [
            f"Row {start + i + 1}: " + "; ".join(f"{c}: {v}" for c, v in row.items() if pd.notna(v))
            for i, (_, row) in enumerate(block.iterrows())
        ]
        parts.append(("\n".join(lines), {"rows": f"{start + 1}-{start + len(block)}"}))
    return parts


def build_documents(
    filename: str,
    data: bytes,
    doc_id: str,
    chunk_size: int,
    chunk_overlap: int,
    rows_per_chunk: int = 20,
) -> list[Document]:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Unsupported file type '{ext}'. Use: {', '.join(sorted(SUPPORTED))}")

    if ext == ".pdf":
        sections = load_pdf(data)
    elif ext in {".csv", ".xlsx"}:
        sections = load_table(data, ext, rows_per_chunk)
    else:
        sections = load_text(data)

    splitter = _splitter(chunk_size, chunk_overlap)
    docs: list[Document] = []
    for text, meta in sections:
        if not text.strip():
            continue
        for piece in splitter.split_text(text):
            docs.append(
                Document(page_content=piece, metadata={"doc_id": doc_id, "source": filename, **meta})
            )
    for i, d in enumerate(docs):
        d.metadata["chunk"] = i
    if not docs:
        raise ValueError("No extractable text found in this file.")
    return docs
