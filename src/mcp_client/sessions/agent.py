from dataclasses import dataclass, field
from typing import Any

from ..agentic.ports import OrchestratorPort, RendererPort, ToolRuntimePort
from ..config.model import ClientConfig
from ..workflows import WorkflowRegistry


@dataclass
class AgentSession:
    config: ClientConfig
    runtime: ToolRuntimePort
    renderer: RendererPort
    api: OrchestratorPort
    workflows: WorkflowRegistry = field(init=False)

    def __post_init__(self) -> None:
        self.workflows = WorkflowRegistry(
            config=self.config,
            runtime=self.runtime,
            renderer=self.renderer,
            api=self.api,
        )

    def run(
        self,
        prompt: str,
        messages: list[dict[str, Any]] | None = None,
        *,
        force_team: bool = False,
    ) -> dict[str, Any]:
        return self.workflows.run(
            prompt,
            messages=messages,
            force_team=force_team,
        )
