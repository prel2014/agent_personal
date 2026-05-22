from src.mcp_client.agentic.routing import PlanningRouter


def test_image_question_routes_to_team_even_when_short() -> None:
    router = PlanningRouter(api=None, runtime=None)  # type: ignore[arg-type]

    decision = router.decide("en esta ruta hay imagens de que tratan cada una?")

    assert decision.route == "team"
    assert "workspace_or_tool_signal" in decision.signals


def test_simple_short_question_still_routes_direct() -> None:
    router = PlanningRouter(api=None, runtime=None)  # type: ignore[arg-type]

    decision = router.decide("que es python?")

    assert decision.route == "direct"
