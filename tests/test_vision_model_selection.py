from src.mcp.tools.helpers.hardware_tools import _best_vision_model


def test_best_vision_model_prefers_gemm4_over_text_model() -> None:
    assert _best_vision_model(["llama3.1:8b", "gemm4:latest"]) == "gemm4:latest"


def test_best_vision_model_uses_only_available_model_as_fallback() -> None:
    assert _best_vision_model(["custom-local-model:latest"]) == "custom-local-model:latest"


def test_best_vision_model_rejects_ambiguous_text_models() -> None:
    assert _best_vision_model(["llama3.1:8b", "qwen3:8b"]) is None
