from __future__ import annotations

from dataclasses import dataclass, replace

from ...autowrite.service import AutoWriteService
from ...config.model import ClientConfig
from ...integrations.execution import ToolCallProcessor
from ..turns import ChatTurnRequester
from ..workflow import AgentWorkflow
from ..policies import RoleRuntimeView, ToolAccessPolicy
from ..ports import OrchestratorPort, RendererPort, ToolRuntimePort
from ..roles import RoleSpec

@dataclass
class RoleWorkflowFactory:
    config: ClientConfig
    runtime: ToolRuntimePort
    api: OrchestratorPort
    tool_policy: ToolAccessPolicy

    def build(
        self,
        *,
        spec: RoleSpec,
        directive: str,
        renderer: RendererPort,
        auto_write: bool,
        max_steps: int,
        sandbox_only: bool = True,
    ) -> AgentWorkflow:
        runtime_view = RoleRuntimeView(
            self.runtime,
            role=spec.role,
            directive=directive,
            allowed_tools=self.tool_policy.allowed_tools_for(
                spec,
                sandbox_only=sandbox_only,
            ),
            sandbox_only=sandbox_only,
        )
        role_config = self._role_config(max_steps=max_steps, auto_write=auto_write)
        turn_requester = ChatTurnRequester(
            config=role_config,
            runtime=runtime_view,
            renderer=renderer,
            api=self.api,
        )
        return AgentWorkflow(
            config=role_config,
            runtime=runtime_view,
            renderer=renderer,
            api=self.api,
            tool_call_processor=ToolCallProcessor(
                runtime=runtime_view,
                renderer=renderer,
            ),
            auto_write_service=AutoWriteService(
                runtime=runtime_view,
                renderer=renderer,
                enabled=auto_write,
            ),
            turn_requester=turn_requester,
        )

    def _role_config(self, *, max_steps: int, auto_write: bool) -> ClientConfig:
        return replace(
            self.config,
            max_steps=max_steps,
            auto_write_code=auto_write,
        )
