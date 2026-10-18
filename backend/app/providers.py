"""Factories for embeddings and chat models, selected by environment config."""
from __future__ import annotations

from langchain_core.embeddings import Embeddings

from .config import Settings


def get_embeddings(s: Settings) -> Embeddings:
    p = s.embeddings_provider
    if p == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=s.embeddings_model or "text-embedding-3-small", api_key=s.openai_api_key)
    if p == "fastembed":
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        return FastEmbedEmbeddings(model_name=s.embeddings_model or "BAAI/bge-small-en-v1.5")
    if p == "fake":
        from langchain_core.embeddings import DeterministicFakeEmbedding

        return DeterministicFakeEmbedding(size=256)
    raise ValueError(f"Unknown EMBEDDINGS_PROVIDER '{p}'")


def get_llm(s: Settings):
    """Return a LangChain chat model, or None for the offline 'mock' provider."""
    p = s.llm_provider
    if p == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=s.llm_model or "gpt-4o-mini", api_key=s.openai_api_key, temperature=0, streaming=True)
    if p == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=s.llm_model or "claude-sonnet-4-5", api_key=s.anthropic_api_key, temperature=0)
    if p == "mock":
        return None
    raise ValueError(f"Unknown LLM_PROVIDER '{p}'")
