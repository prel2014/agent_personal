from __future__ import annotations

import pytest
from pathlib import Path

from src.mcp_client.agentic.skills.models import SkillSpec
from src.mcp_client.agentic.skills.registry import SkillRegistry, load_skill_file


def _write_skill(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# load_skill_file
# ---------------------------------------------------------------------------

def test_load_skill_minimal_frontmatter(tmp_path: Path) -> None:
    f = _write_skill(
        tmp_path / "concise.md",
        "---\ndescription: Respuestas cortas.\n---\nResponde en máximo 3 líneas.\n",
    )
    spec = load_skill_file(f)
    assert spec.name == "concise"
    assert spec.description == "Respuestas cortas."
    assert "máximo" in spec.directive
    assert spec.directive == "Responde en máximo 3 líneas."
    assert spec.scope == "all"
    assert spec.tags == ()
    assert spec.version == ""
    assert spec.source == str(f)


def test_load_skill_full_frontmatter(tmp_path: Path) -> None:
    f = _write_skill(
        tmp_path / "code-style.md",
        "---\nname: code-style\ndescription: Estilo de codigo.\nscope: worker\ntags: style, quality\nversion: 2.1\n---\nSigue PEP8 siempre.\n",
    )
    spec = load_skill_file(f)
    assert spec.name == "code-style"
    assert spec.scope == "worker"
    assert spec.tags == ("style", "quality")
    assert spec.version == "2.1"
    assert spec.directive == "Sigue PEP8 siempre."


def test_load_skill_missing_description_raises(tmp_path: Path) -> None:
    f = _write_skill(tmp_path / "bad.md", "---\nname: bad\n---\nDirective sin desc.\n")
    with pytest.raises(ValueError, match="sin description"):
        load_skill_file(f)


def test_load_skill_invalid_scope_raises(tmp_path: Path) -> None:
    f = _write_skill(
        tmp_path / "bad.md",
        "---\ndescription: X.\nscope: planner\n---\nTexto.\n",
    )
    with pytest.raises(ValueError, match="scope invalido"):
        load_skill_file(f)


def test_load_skill_empty_body_raises(tmp_path: Path) -> None:
    f = _write_skill(tmp_path / "empty.md", "---\ndescription: Desc.\n---\n   \n")
    with pytest.raises(ValueError, match="sin cuerpo"):
        load_skill_file(f)


# ---------------------------------------------------------------------------
# SkillRegistry
# ---------------------------------------------------------------------------

def test_registry_from_paths_loads_files(tmp_path: Path) -> None:
    _write_skill(tmp_path / "a.md", "---\ndescription: A.\n---\nDirective A.\n")
    _write_skill(tmp_path / "b.md", "---\ndescription: B.\nscope: reviewer\n---\nDirective B.\n")
    reg = SkillRegistry.from_paths([tmp_path])
    assert len(reg.list_all()) == 2
    names = {s.name for s in reg.list_all()}
    assert names == {"a", "b"}


def test_registry_get_missing_returns_none() -> None:
    reg = SkillRegistry()
    assert reg.get("no-existe") is None


def test_registry_from_paths_ignores_bad_files(tmp_path: Path) -> None:
    _write_skill(tmp_path / "ok.md", "---\ndescription: Ok.\n---\nOk.\n")
    _write_skill(tmp_path / "bad.md", "---\nname: bad\n---\nSin desc.\n")
    reg = SkillRegistry.from_paths([tmp_path])
    assert len(reg.list_all()) == 1
    assert reg.get("ok") is not None


def test_skill_applies_to_role() -> None:
    worker_skill = SkillSpec(name="x", description="d", directive=".", scope="worker")
    reviewer_skill = SkillSpec(name="y", description="d", directive=".", scope="reviewer")
    all_skill = SkillSpec(name="z", description="d", directive=".", scope="all")

    assert worker_skill.applies_to_role("worker") is True
    assert worker_skill.applies_to_role("reviewer") is False
    assert reviewer_skill.applies_to_role("reviewer") is True
    assert reviewer_skill.applies_to_role("worker") is False
    assert all_skill.applies_to_role("worker") is True
    assert all_skill.applies_to_role("reviewer") is True
