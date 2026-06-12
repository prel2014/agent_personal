from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..agentic.ports import OrchestratorPort, RendererPort, ToolRuntimePort
from ..config.model import ClientConfig
from ..workflows import WorkflowRegistry

if TYPE_CHECKING:
    from ..agentic.memory.provider import MemoryContextProvider
    from ..agentic.skills import SkillRegistry


@dataclass
class AgentSession:
    config: ClientConfig
    runtime: ToolRuntimePort
    renderer: RendererPort
    api: OrchestratorPort
    skill_registry: SkillRegistry | None = None
    active_skill_name: str | None = None
    memory_provider: MemoryContextProvider | None = None
    workflows: WorkflowRegistry = field(init=False)

    def __post_init__(self) -> None:
        self.workflows = WorkflowRegistry(
            config=self.config,
            runtime=self.runtime,
            renderer=self.renderer,
            api=self.api,
            skill_registry=self.skill_registry,
            active_skill_name=self.active_skill_name,
            memory_provider=self.memory_provider,
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
