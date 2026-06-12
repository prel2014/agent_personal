from src.mcp_client.agentic.state import AgentRunResult, ConversationMemory
from src.mcp_client.agentic.roles import PLANNER_DIRECTIVE, REVIEWER_DIRECTIVE
from src.mcp_client.agentic.team.prompts import (
    build_review_prompt,
    build_worker_directive,
    build_worker_retry_prompt,
)
from src.mcp_client.integrations.execution import _duplicate_writefile_path
from src.mcp_shared.contracts import ChatMessage, ChatResponse


def test_review_prompt_uses_tool_results_not_only_auto_write() -> None:
    memory = ConversationMemory()
    memory.append_tool(
        "writefile",
        (
            '{"success": true, "result": {'
            '"operation": "writefile", '
            '"path": "C:/tmp/Historia Uno.txt", '
            '"bytes_written": 120, '
            '"content_sha256": "abc"'
            "}}"
        ),
    )
    worker_result = AgentRunResult(
        final="Listo.",
        memory=memory,
        response=ChatResponse(message=ChatMessage.assistant(content="Listo.")),
    )

    prompt = build_review_prompt(
        original_prompt="crea una historia",
        plan_summary="crear archivo",
        worker_result=worker_result,
    )

    assert "Archivos escritos por auto-write Markdown:\n(ninguno)" in prompt
    assert "writefile: ok" in prompt
    assert "Historia Uno.txt" in prompt
    assert "evidencia real de cambios" in prompt


def test_planner_no_modify_rule_is_scoped_to_planner_only() -> None:
    assert "aplica solo al planner" in PLANNER_DIRECTIVE
    assert "no impide que el worker modifique archivos" in PLANNER_DIRECTIVE
    assert "No modifiques archivos." not in PLANNER_DIRECTIVE


def test_worker_prompt_does_not_treat_planner_limits_as_global_policy() -> None:
    prompt = build_worker_directive(
        "PLAN\n- Agregar filas ficticias al CSV.\nRIESGOS\n- El planner no modifica archivos."
    )

    assert "no una politica de seguridad" in prompt
    assert "no las apliques al worker" in prompt


def test_review_prompt_accepts_permitted_append_for_user_edit_request() -> None:
    memory = ConversationMemory()
    memory.append_tool(
        "appendfile",
        (
            '{"success": true, "result": {'
            '"operation": "appendfile", '
            '"path": "C:/tmp/alumnos.csv", '
            '"bytes_written": 72'
            "}}"
        ),
    )
    worker_result = AgentRunResult(
        final="Agregue nuevas filas ficticias en alumnos.csv.",
        memory=memory,
        response=ChatResponse(message=ChatMessage.assistant(content="Listo.")),
    )

    prompt = build_review_prompt(
        original_prompt="al csv de alumnos.csv agrega mas filas con registros ficticios",
        plan_summary="Agregar filas al CSV existente.",
        worker_result=worker_result,
    )

    assert "appendfile: ok" in prompt
    assert "resultado esperado, no una violacion" in prompt
    assert "no trates las limitaciones del rol planner" in prompt
    assert "escritura permitida con exito" in REVIEWER_DIRECTIVE


def test_worker_retry_prompt_rejects_false_write_violation_feedback() -> None:
    prompt = build_worker_retry_prompt(
        "REQUIERE_CAMBIOS: el worker modifico un archivo aunque el planner no podia modificar."
    )

    assert "no deshagas" in prompt
    assert "escritura permitida" in prompt
    assert "cumplido la solicitud" in prompt


def test_duplicate_writefile_path_guard_detects_repeated_path() -> None:
    seen_paths: set[str] = set()

    first = _duplicate_writefile_path(
        "writefile",
        {"path": r"C:\tmp\Historia Cinco.txt"},
        seen_paths,
    )
    second = _duplicate_writefile_path(
        "writefile",
        {"path": "C:/tmp/Historia Cinco.txt"},
        seen_paths,
    )

    assert first is None
    assert second == "C:/tmp/Historia Cinco.txt"
