from __future__ import annotations

from pathlib import Path

from src.mcp_client.agentic.memory.store import MemoryStore
from src.mcp_client.agentic.memory.provider import MemoryContextProvider


# ---------------------------------------------------------------------------
# MemoryStore — operaciones básicas
# ---------------------------------------------------------------------------

def test_remember_and_list(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "mem.sqlite")
    store.remember("lang", "siempre usar Python")
    entries = store.list_memories()
    assert len(entries) == 1
    assert entries[0]["key"] == "lang"
    assert entries[0]["value"] == "siempre usar Python"


def test_forget_removes_entry(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "mem.sqlite")
    store.remember("k", "v")
    store.forget("k")
    assert store.list_memories() == []


def test_search_bm25_finds_relevant(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "mem.sqlite")
    store.remember("pref_lang", "preferencia: usar Python siempre")
    store.remember("pref_style", "respuestas cortas y directas")
    results = store.search("lenguaje preferido", top_k=5)
    keys = [r.get("key") for r in results]
    assert "pref_lang" in keys


def test_search_returns_at_most_top_k(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "mem.sqlite")
    for i in range(8):
        store.remember(f"key_{i}", f"valor memoria numero {i}")
    results = store.search("memoria valor", top_k=3)
    assert len(results) <= 3


def test_remember_overwrites_existing_key(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "mem.sqlite")
    store.remember("k", "v1")
    store.remember("k", "v2")
    entries = store.list_memories()
    assert len(entries) == 1
    assert entries[0]["value"] == "v2"


# ---------------------------------------------------------------------------
# MemoryContextProvider — combinación proyecto + usuario
# ---------------------------------------------------------------------------

def test_provider_combines_both_stores(tmp_path: Path) -> None:
    proj = MemoryStore(tmp_path / "proj.sqlite")
    user = MemoryStore(tmp_path / "user.sqlite")
    proj.remember("style", "respuestas en markdown")
    user.remember("lang", "siempre Python")

    provider = MemoryContextProvider(project_store=proj, user_store=user, top_k=5)
    entries = provider.to_context_entries("estilo de respuesta")
    keys = {e["key"] for e in entries}
    assert "style" in keys or "lang" in keys


def test_provider_deduplicates_by_key(tmp_path: Path) -> None:
    proj = MemoryStore(tmp_path / "proj.sqlite")
    user = MemoryStore(tmp_path / "user.sqlite")
    proj.remember("lang", "Python")
    user.remember("lang", "JavaScript")

    provider = MemoryContextProvider(project_store=proj, user_store=user, top_k=5)
    results = provider.recall("lang")
    lang_entries = [r for r in results if r.get("key") == "lang"]
    assert len(lang_entries) == 1
    assert lang_entries[0]["value"] == "Python"


def test_provider_without_stores_returns_empty(tmp_path: Path) -> None:
    provider = MemoryContextProvider()
    assert provider.is_empty()
    assert provider.recall("query") == []
    assert provider.to_context_entries("query") == []


def test_provider_only_project_store(tmp_path: Path) -> None:
    proj = MemoryStore(tmp_path / "proj.sqlite")
    proj.remember("key1", "valor1")
    provider = MemoryContextProvider(project_store=proj)
    entries = provider.to_context_entries("key1")
    assert any(e["key"] == "key1" for e in entries)
