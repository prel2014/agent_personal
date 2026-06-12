from src.mcp_client.console.input import ConsoleInputReader
from src.mcp_client.prompts import build_compact_prompt, build_routing_classifier_prompt
from src.mcp_server.ollama.prompt_registry import load_default_prompt_registry
from src.mcp_server.ollama.prompts import OllamaPromptBuilder


class FakePromptSession:
    def __init__(self, value: str) -> None:
        self.value = value
        self.labels: list[str] = []

    def prompt(self, label: str) -> str:
        self.labels.append(label)
        return self.value


def test_console_input_reader_strips_prompt_session_text() -> None:
    session = FakePromptSession("  hola  ")
    reader = ConsoleInputReader(prompt_session=session)

    assert reader.read_prompt("tu> ") == "hola"
    assert session.labels == ["tu> "]


def test_prompt_templates_live_outside_handlers() -> None:
    compact_prompt = build_compact_prompt("solo riesgos")
    routing_prompt = build_routing_classifier_prompt("arregla tests")

    assert "Compacta la conversacion anterior" in compact_prompt
    assert "solo riesgos" in compact_prompt
    assert '"route":"direct|team"' in routing_prompt
    assert "arregla tests" in routing_prompt


def test_ollama_prompt_builder_delegates_mode_rules() -> None:
    prompt = OllamaPromptBuilder("BASE").build(
        {
            "prompt_mode": "compact",
            "available_tools": ["readfile"],
        }
    )

    assert prompt.startswith("BASE")
    assert "Contexto actual del cliente" in prompt
    assert "Produce solo un resumen operativo" in prompt
    assert "No uses herramientas ni tool calls" in prompt


def test_ollama_prompt_builder_includes_dynamic_tool_and_subagent_context() -> None:
    prompt = OllamaPromptBuilder("BASE").build(
        {
            "prompt_mode": "worker",
            "available_tools": ["readfile", "request_tools", "delegate_agent"],
            "tool_categories": {
                "readfile": "read",
                "request_tools": "orchestration",
                "delegate_agent": "orchestration",
            },
            "tool_selection": {
                "dynamic": True,
                "active_tools": ["readfile"],
                "activatable_tools": ["readfile", "python_interpreter"],
                "inactive_tools": ["python_interpreter"],
            },
            "subagents": [
                {
                    "name": "code-reviewer",
                    "description": "Revisa riesgos y regresiones.",
                    "tool_access": "read_only",
                }
            ],
        }
    )

    assert "request_tools" in prompt
    assert "python_interpreter" in prompt
    assert "delegate_agent" in prompt
    assert "code-reviewer" in prompt
    assert "Catalogo de subagentes" in prompt


def test_default_prompt_registry_resolves_worker_as_tool_workflow() -> None:
    registry = load_default_prompt_registry()

    assert registry is not None
    template = registry.resolve("worker")

    assert template is not None
    assert template.id == "mcp.tool_workflow"
