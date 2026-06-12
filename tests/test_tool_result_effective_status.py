from __future__ import annotations

import json

from src.mcp_client.agentic.state import (
    AgentRunResult,
    ConversationMemory,
    ToolExecutionOutcome,
)
from src.mcp_client.agentic.team.prompts import build_review_prompt
from src.mcp_client.agentic.tracing import TraceRecorder
from src.mcp_client.presentation.formatters import format_tool_result
from src.mcp_client.tool_results import tool_effective_error, tool_effective_success
from src.mcp_shared.contracts import ChatMessage, ChatResponse


def _failed_process_result() -> dict[str, object]:
    return {
        "success": True,
        "result": {
            "command": ["python", "crear_grafico.py"],
            "cwd": "C:/repo",
            "returncode": 1,
            "stdout": "",
            "stderr": "pandas.errors.ParserError: Expected 9 fields in line 31, saw 17",
            "success": False,
        },
        "error": None,
    }


def test_effective_success_detects_nested_process_failure() -> None:
    result = _failed_process_result()

    assert tool_effective_success(result) is False
    assert "returncode 1" in str(tool_effective_error(result))
    assert "ParserError" in str(tool_effective_error(result))


def test_effective_success_preserves_direct_tool_error_and_successful_process() -> None:
    direct_error = {"success": False, "result": None, "error": "permiso denegado"}
    successful_process = {
        "success": True,
        "result": {
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
            "success": True,
        },
        "error": None,
    }

    assert tool_effective_success(direct_error) is False
    assert tool_effective_error(direct_error) == "permiso denegado"
    assert tool_effective_success(successful_process) is True
    assert tool_effective_error(successful_process) is None


def test_format_tool_result_reports_nested_process_failure_as_error() -> None:
    text = format_tool_result(
        "run_python_file",
        _failed_process_result(),
        detailed=False,
    )

    assert text.startswith("run_python_file error:")
    assert "returncode 1" in text
    assert "ParserError" in text


def test_review_prompt_reports_nested_process_failure_as_error() -> None:
    memory = ConversationMemory()
    memory.append_tool(
        "run_python_file",
        json.dumps(_failed_process_result(), ensure_ascii=False),
    )
    worker_result = AgentRunResult(
        final="Listo.",
        memory=memory,
        response=ChatResponse(message=ChatMessage.assistant(content="Listo.")),
    )

    prompt = build_review_prompt(
        original_prompt="ejecuta crear_grafico.py",
        plan_summary="Ejecutar el script.",
        worker_result=worker_result,
    )

    assert "run_python_file: ERROR" in prompt
    assert "returncode 1" in prompt
    assert "ParserError" in prompt


def test_trace_records_nested_process_failure_as_unsuccessful() -> None:
    recorder = TraceRecorder()
    outcome = ToolExecutionOutcome(
        name="run_python_file",
        arguments={"path": "crear_grafico.py"},
        result=_failed_process_result(),
        duration_ms=10.0,
    )

    recorder.record_tool_outcome(1, outcome)

    trace = recorder.trace.tool_executions[0]
    assert trace.success is False
    assert trace.error is not None
    assert "returncode 1" in trace.error
