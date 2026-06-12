from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.mcp_client.agentic.skills.models import SkillSpec
from src.mcp_client.agentic.skills.registry import SkillRegistry
from src.mcp_client.agentic.memory.provider import MemoryContextProvider
from src.mcp_client.agentic.memory.store import MemoryStore
from src.mcp_client.agentic.policies import RoleRuntimeView
from src.mcp_client.agentic.roles import AgentRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_runtime() -> MagicMock:
    runtime = MagicMock()
    runtime.build_context.return_value = {
        "available_tools": ["readfile", "writefile"],
        "tool_categories": {"readfile": "read", "writefile": "write"},
    }
    runtime.list_ollama_tools.return_value = []
    return runtime


def _make_skill(name: str, scope: str = "all") -> SkillSpec:
    return SkillSpec(
        name=name,
        description="Skill de prueba.",
        directive=f"Directiva del skill {name}.",
        scope=scope,  # type: ignore[arg-type]
    )


def _make_registry(*skills: SkillSpec) -> SkillRegistry:
    return SkillRegistry(specs=skills)


# ---------------------------------------------------------------------------
# _apply_skill via RoleWorkflowFactory
# ---------------------------------------------------------------------------

def _make_factory(skill: SkillSpec | None = None, memory_provider=None):
    from src.mcp_client.agentic.team.factory import RoleWorkflowFactory
    from src.mcp_client.agentic.policies import ToolAccessPolicy
    from unittest.mock import MagicMock

    config = MagicMock()
    config.runtime_config.base_dir = Path(".")
    config.max_steps = 5
    config.auto_write_code = False

    registry = _make_registry(skill) if skill else SkillRegistry()

    factory = RoleWorkflowFactory(
        config=config,
        runtime=_make_runtime(),
        api=MagicMock(),
        tool_policy=MagicMock(allowed_tool_names=MagicMock(return_value=None)),
        skill_registry=registry,
        active_skill_name=skill.name if skill else None,
        memory_provider=memory_provider,
    )
    return factory


def test_apply_skill_worker_scope_only_applies_to_worker() -> None:
    skill = _make_skill("s1", scope="worker")
    factory = _make_factory(skill)

    directive_worker = factory._apply_skill("BASE", AgentRole.WORKER)
    directive_reviewer = factory._apply_skill("BASE", AgentRole.REVIEWER)

    assert "Directiva del skill s1" in directive_worker
    assert "Directiva del skill s1" not in directive_reviewer


def test_apply_skill_reviewer_scope_only_applies_to_reviewer() -> None:
    skill = _make_skill("s2", scope="reviewer")
    factory = _make_factory(skill)

    assert "Directiva del skill s2" not in factory._apply_skill("BASE", AgentRole.WORKER)
    assert "Directiva del skill s2" in factory._apply_skill("BASE", AgentRole.REVIEWER)


def test_apply_skill_all_scope_applies_to_both_roles() -> None:
    skill = _make_skill("s3", scope="all")
    factory = _make_factory(skill)

    assert "Directiva del skill s3" in factory._apply_skill("BASE", AgentRole.WORKER)
    assert "Directiva del skill s3" in factory._apply_skill("BASE", AgentRole.REVIEWER)


def test_no_active_skill_returns_original_directive() -> None:
    factory = _make_factory(skill=None)
    assert factory._apply_skill("ORIGINAL", AgentRole.WORKER) == "ORIGINAL"


def test_unknown_skill_name_returns_original_directive() -> None:
    factory = _make_factory(skill=None)
    factory.active_skill_name = "no-existe"
    assert factory._apply_skill("ORIGINAL", AgentRole.WORKER) == "ORIGINAL"


# ---------------------------------------------------------------------------
# RoleRuntimeView — inyección en contexto
# ---------------------------------------------------------------------------

def test_build_context_includes_active_skill() -> None:
    runtime = _make_runtime()
    view = RoleRuntimeView(
        runtime,
        role=AgentRole.WORKER,
        directive="dir",
        allowed_tools=None,
        active_skill={"name": "concise", "scope": "all"},
    )
    wire = view.build_context()
    assert wire.get("active_skill", {}).get("name") == "concise"


def test_build_context_includes_memories() -> None:
    runtime = _make_runtime()
    view = RoleRuntimeView(
        runtime,
        role=AgentRole.WORKER,
        directive="dir",
        allowed_tools=None,
        memories=[{"key": "pref_lang", "value": "Python"}],
    )
    wire = view.build_context()
    memories = wire.get("memories", [])
    assert any(m.get("key") == "pref_lang" for m in memories)


def test_build_context_no_skill_no_extra_keys() -> None:
    runtime = _make_runtime()
    view = RoleRuntimeView(
        runtime,
        role=AgentRole.WORKER,
        directive="dir",
        allowed_tools=None,
    )
    wire = view.build_context()
    assert "active_skill" not in wire or wire["active_skill"] == {}
    assert "memories" not in wire or wire["memories"] == []


# ---------------------------------------------------------------------------
# MemoryContextProvider integrado con factory
# ---------------------------------------------------------------------------

def test_factory_recall_memories_returns_entries(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "mem.sqlite")
    store.remember("pref_style", "usa markdown siempre")
    provider = MemoryContextProvider(project_store=store, top_k=3)
    factory = _make_factory(memory_provider=provider)
    entries = factory._recall_memories("estilo de respuesta")
    assert entries is not None
    assert any(e.get("key") == "pref_style" for e in entries)


def test_factory_recall_memories_none_when_no_provider() -> None:
    factory = _make_factory(memory_provider=None)
    assert factory._recall_memories("query") is None
