from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from ...autowrite.service import AutoWriteService
from ...config.model import ClientConfig
from ...integrations.execution import ToolCallProcessor
from ...render.null import NullRenderer
from ..policies import RoleRuntimeView, ToolAccessPolicy
from ..ports import OrchestratorPort, RendererPort, ToolRuntimePort
from ..roles import AgentRole, RoleSpec
from ..subagents import SelectableToolRuntimeView, SubagentRegistry, SubagentSpec
from ..turns import ChatTurnRequester
from ..workflow import AgentWorkflow


INITIAL_ROLE_TOOLS: dict[str, set[str]] = {
    "worker": {
        "pwd",
        "listdir",
        "list_tree",
        "find_files",
        "fileinfo",
        "readfile",
        "read_lines",
        "search_code",
        "writefile",
        "replace",
        "movefile",
    },
    "reviewer": {
        "pwd",
        "listdir",
        "list_tree",
        "find_files",
        "fileinfo",
        "readfile",
        "read_lines",
        "search_code",
        "git_status",
        "git_diff",
    },
}


@dataclass
class RoleWorkflowFactory:
    config: ClientConfig
    runtime: ToolRuntimePort
    api: OrchestratorPort
    tool_policy: ToolAccessPolicy
    subagent_registry: SubagentRegistry | None = None

    def __post_init__(self) -> None:
        if self.subagent_registry is None:
            base_dir = self.config.runtime_config.base_dir
            self.subagent_registry = SubagentRegistry.from_paths(
                (
                    Path.home() / ".mcp_agents",
                    base_dir / ".mcp_agents",
                )
            )

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
        runtime_view = self._role_runtime_view(
            role=spec.role,
            directive=directive,
            tool_access=spec.tool_access,
            requested_tools=None,
            sandbox_only=sandbox_only,
        )
        runtime_for_workflow: ToolRuntimePort = runtime_view
        if spec.tool_access != "none":
            runtime_for_workflow = SelectableToolRuntimeView(
                runtime_view,
                initial_tools=INITIAL_ROLE_TOOLS.get(spec.role.value),
                subagent_catalog=self.subagent_registry.catalog(),
                delegate_handler=lambda agent, task, context: self._delegate_subagent(
                    agent=agent,
                    task=task,
                    context=context,
                    sandbox_only=sandbox_only,
                ),
                allow_delegate=spec.role == AgentRole.WORKER,
            )
        return self._build_from_runtime(
            runtime=runtime_for_workflow,
            renderer=renderer,
            auto_write=auto_write,
            max_steps=max_steps,
        )

    def build_subagent(
        self,
        *,
        spec: SubagentSpec,
        renderer: RendererPort,
        auto_write: bool,
        max_steps: int,
        sandbox_only: bool = True,
        allow_delegate: bool = False,
    ) -> AgentWorkflow:
        runtime_view = self._role_runtime_view(
            role=spec.name,
            directive=spec.directive,
            tool_access=spec.tool_access,
            requested_tools=set(spec.tools) if spec.tools is not None else None,
            sandbox_only=sandbox_only,
        )
        initial_tools = (
            set(spec.tools) if spec.tools is not None else INITIAL_ROLE_TOOLS.get(spec.name)
        )
        runtime_for_workflow: ToolRuntimePort = runtime_view
        if spec.tool_access != "none":
            runtime_for_workflow = SelectableToolRuntimeView(
                runtime_view,
                initial_tools=initial_tools,
                subagent_catalog=self.subagent_registry.catalog(),
                delegate_handler=lambda agent, task, context: self._delegate_subagent(
                    agent=agent,
                    task=task,
                    context=context,
                    sandbox_only=sandbox_only,
                ),
                allow_delegate=allow_delegate,
            )
        return self._build_from_runtime(
            runtime=runtime_for_workflow,
            renderer=renderer,
            auto_write=auto_write,
            max_steps=max_steps,
        )

    def _delegate_subagent(
        self,
        *,
        agent: str,
        task: str,
        context: str | None,
        sandbox_only: bool,
    ) -> dict[str, object]:
        spec = self.subagent_registry.get(agent)
        if spec is None:
            available = ", ".join(
                str(entry["name"]) for entry in self.subagent_registry.catalog()
            )
            return {
                "success": False,
                "result": None,
                "error": f"Subagente desconocido '{agent}'. Disponibles: {available}",
            }

        prompt = task
        if context:
            prompt = f"{task}\n\nContexto para esta subtarea:\n{context}"
        workflow = self.build_subagent(
            spec=spec,
            renderer=NullRenderer(),
            auto_write=False,
            max_steps=min(self.config.max_steps, 4),
            sandbox_only=sandbox_only,
            allow_delegate=False,
        )
        result = workflow.run(prompt, messages=[])
        return {
            "success": True,
            "result": {
                "agent": spec.name,
                "summary": result.final,
                "auto_written_files": result.auto_written_files,
                "trace": result.trace,
            },
            "error": None,
        }

    def _role_runtime_view(
        self,
        *,
        role: AgentRole | str,
        directive: str,
        tool_access: str,
        requested_tools: set[str] | None,
        sandbox_only: bool,
    ) -> RoleRuntimeView:
        allowed_tools = self.tool_policy.allowed_tool_names(
            tool_access,
            sandbox_only=sandbox_only,
        )
        if requested_tools is not None:
            if allowed_tools is None:
                allowed_tools = set(requested_tools)
            else:
                allowed_tools = allowed_tools.intersection(requested_tools)
        return RoleRuntimeView(
            self.runtime,
            role=role,
            directive=directive,
            allowed_tools=allowed_tools,
            sandbox_only=sandbox_only,
        )

    def _build_from_runtime(
        self,
        *,
        runtime: ToolRuntimePort,
        renderer: RendererPort,
        auto_write: bool,
        max_steps: int,
    ) -> AgentWorkflow:
        role_config = self._role_config(max_steps=max_steps, auto_write=auto_write)
        turn_requester = ChatTurnRequester(
            config=role_config,
            runtime=runtime,
            renderer=renderer,
            api=self.api,
        )
        return AgentWorkflow(
            config=role_config,
            runtime=runtime,
            renderer=renderer,
            api=self.api,
            tool_call_processor=ToolCallProcessor(
                runtime=runtime,
                renderer=renderer,
            ),
            auto_write_service=AutoWriteService(
                runtime=runtime,
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
