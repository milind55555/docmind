from app.ingestion import build_documents

CSV = b"name,dept,salary\nAsha,Cloud,120\nRavi,DevOps,100\nMeera,SRE,110\n"


def test_csv_builds_summary_and_rows():
    docs = build_documents("people.csv", CSV, "d1", 900, 100, rows_per_chunk=2)
    texts = [d.page_content for d in docs]
    assert any("3 rows and 3 columns" in t for t in texts)  # pandas summary
    assert any("Row 1: name: Asha" in t for t in texts)
    assert all(d.metadata["doc_id"] == "d1" for d in docs)


def test_text_is_chunked_with_overlap():
    text = ("Kubernetes schedules containers. " * 80).encode()
    docs = build_documents("notes.txt", text, "d2", 300, 50)
    assert len(docs) > 1
    assert docs[0].metadata["source"] == "notes.txt"


def test_unsupported_extension_rejected():
    import pytest

    with pytest.raises(ValueError):
        build_documents("virus.exe", b"x", "d3", 900, 100)
