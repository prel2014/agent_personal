from src.mcp_client.agentic.state import AgentRunResult, ConversationMemory
from src.mcp_client.agentic.team.prompts import build_review_prompt
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
