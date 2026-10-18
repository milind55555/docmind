"""Retrieval-augmented generation: retrieve -> build prompt -> stream answer."""
from __future__ import annotations

from collections.abc import AsyncIterator

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

SYSTEM = (
    "You are DocMind, an assistant that answers questions using ONLY the provided context "
    "excerpts from the user's documents. Cite sources inline like [1], [2] using the excerpt "
    "numbers. If the context does not contain the answer, say you could not find it in the "
    "documents instead of guessing. Be concise."
)

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM),
        ("human", "Conversation so far:\n{history}\n\nContext excerpts:\n{context}\n\nQuestion: {question}"),
    ]
)


def format_context(hits: list[tuple[Document, float]]) -> str:
    blocks = []
    for i, (doc, _) in enumerate(hits, start=1):
        loc = doc.metadata.get("page") or doc.metadata.get("rows") or doc.metadata.get("section") or ""
        blocks.append(f"[{i}] ({doc.metadata.get('source')}{', ' + str(loc) if loc else ''})\n{doc.page_content}")
    return "\n\n".join(blocks)


def format_history(history: list[dict], max_turns: int = 6) -> str:
    turns = history[-max_turns * 2 :]
    return "\n".join(f"{t['role']}: {t['content']}" for t in turns) or "(none)"


def sources_payload(hits: list[tuple[Document, float]]) -> list[dict]:
    return [
        {
            "n": i,
            "source": d.metadata.get("source"),
            "location": d.metadata.get("page") or d.metadata.get("rows") or d.metadata.get("section"),
            "score": round(max(0.0, min(1.0, float(score))), 3),
            "snippet": d.page_content[:280],
        }
        for i, (d, score) in enumerate(hits, start=1)
    ]


async def stream_answer(llm, question: str, history: list[dict], hits: list[tuple[Document, float]]) -> AsyncIterator[str]:
    if not hits:
        yield "I could not find anything in your documents yet. Upload a file first."
        return
    if llm is None:  # offline demo mode: show the best excerpts
        yield "(Demo mode: no LLM configured. Showing the most relevant excerpts.)\n\n"
        for i, (d, _) in enumerate(hits[:3], start=1):
            yield f"[{i}] {d.page_content[:400]}\n\n"
        return
    chain = PROMPT | llm | StrOutputParser()
    async for token in chain.astream(
        {"history": format_history(history), "context": format_context(hits), "question": question}
    ):
        yield token
