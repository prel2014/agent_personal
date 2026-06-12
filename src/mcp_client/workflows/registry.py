from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..agentic.team import AgentTeamOrchestrator
from ..agentic.policies import DirectAnswerRuntimeView, ToolAccessPolicy
from ..agentic.routing import PlanningRouter
from ..agentic.team.factory import RoleWorkflowFactory
from ..agentic.workflow import AgentWorkflow
from ..autowrite.service import AutoWriteService
from ..integrations.execution import ToolCallProcessor
from ..config.model import ClientConfig
from ..agentic.ports import OrchestratorPort, RendererPort, ToolRuntimePort
from .tracing import WorkflowTraceService

if TYPE_CHECKING:
    from ..agentic.memory.provider import MemoryContextProvider
    from ..agentic.skills import SkillRegistry


def _tool_categories_from_runtime(runtime: ToolRuntimePort) -> dict[str, str]:
    context = runtime.build_context()
    raw_categories = context.get("tool_categories")
    if not isinstance(raw_categories, dict):
        return {}
    return {k: v for k, v in raw_categories.items() if isinstance(k, str) and isinstance(v, str)}


@dataclass
class WorkflowRegistry:
    config: ClientConfig
    runtime: ToolRuntimePort
    renderer: RendererPort
    api: OrchestratorPort
    skill_registry: SkillRegistry | None = None
    active_skill_name: str | None = None
    memory_provider: MemoryContextProvider | None = None
    tool_call_processor: ToolCallProcessor = field(init=False)
    auto_write_service: AutoWriteService = field(init=False)
    workflow: AgentWorkflow = field(init=False)
    direct_answer_workflow: AgentWorkflow = field(init=False)
    team_orchestrator: AgentTeamOrchestrator = field(init=False)
    planning_router: PlanningRouter = field(init=False)
    trace_service: WorkflowTraceService = field(init=False)

    def __post_init__(self) -> None:
        direct_answer_runtime = DirectAnswerRuntimeView(self.runtime)
        self.tool_call_processor = ToolCallProcessor(
            runtime=self.runtime,
            renderer=self.renderer,
        )
        direct_answer_tool_call_processor = ToolCallProcessor(
            runtime=direct_answer_runtime,
            renderer=self.renderer,
        )
        self.auto_write_service = AutoWriteService(
            runtime=self.runtime,
            renderer=self.renderer,
            enabled=self.config.auto_write_code,
        )
        self.trace_service = WorkflowTraceService(self.config)
        self.workflow = AgentWorkflow(
            config=self.config,
            runtime=self.runtime,
            renderer=self.renderer,
            api=self.api,
            tool_call_processor=self.tool_call_processor,
            auto_write_service=self.auto_write_service,
        )
        self.direct_answer_workflow = AgentWorkflow(
            config=self.config,
            runtime=direct_answer_runtime,
            renderer=self.renderer,
            api=self.api,
            tool_call_processor=direct_answer_tool_call_processor,
            auto_write_service=AutoWriteService(
                runtime=direct_answer_runtime,
                renderer=self.renderer,
                enabled=False,
            ),
        )
        tool_policy = ToolAccessPolicy(_tool_categories_from_runtime(self.runtime))
        workflow_factory = RoleWorkflowFactory(
            config=self.config,
            runtime=self.runtime,
            api=self.api,
            tool_policy=tool_policy,
            skill_registry=self.skill_registry,
            active_skill_name=self.active_skill_name,
            memory_provider=self.memory_provider,
        )
        self.team_orchestrator = AgentTeamOrchestrator(
            config=self.config,
            runtime=self.runtime,
            renderer=self.renderer,
            api=self.api,
            trace_store=self.trace_service.store,
            trace_settings=self.trace_service.settings,
            tool_policy=tool_policy,
            workflow_factory=workflow_factory,
        )
        self.planning_router = PlanningRouter(
            api=self.api,
            runtime=self.runtime,
        )

    def run(
        self,
        prompt: str,
        messages: list[dict[str, Any]] | None = None,
        *,
        force_team: bool = False,
    ) -> dict[str, Any]:
        permission_result = self._blocked_by_missing_delete_permission(prompt, messages)
        if permission_result is not None:
            return permission_result
        permission_result = self._blocked_by_missing_media_permission(prompt, messages)
        if permission_result is not None:
            return permission_result

        if force_team and self.config.planning_mode != "never":
            self._print_route("team", "continuacion de pregunta del agente")
            return self.team_orchestrator.run(prompt, messages=messages).to_dict()

        if self.config.planning_mode == "always":
            return self.team_orchestrator.run(prompt, messages=messages).to_dict()

        if self.config.planning_mode == "never":
            run_id = self.trace_service.new_run_id()
            return self.workflow.run(
                prompt,
                messages=messages,
                hooks=self.trace_service.hooks(
                    run_id=run_id,
                    mode="single_workflow",
                    role="single",
                    complete_run=True,
                ),
            ).to_dict()

        decision = self.planning_router.decide(prompt, messages)
        self._print_route(decision.route, decision.reason)
        if decision.route == "team":
            run_id = self.trace_service.create_routed_run(
                prompt,
                messages,
                decision.route,
                decision.reason,
                decision.signals,
            )
            return self.team_orchestrator.run(
                prompt,
                messages=messages,
                trace_run_id=run_id,
            ).to_dict()

        run_id = self.trace_service.create_routed_run(
            prompt,
            messages,
            decision.route,
            decision.reason,
            decision.signals,
        )
        return self.direct_answer_workflow.run(
            prompt,
            messages=messages,
            hooks=self.trace_service.hooks(
                run_id=run_id,
                mode="direct_answer",
                role="direct_answer",
                complete_run=True,
                run_metadata={
                    "route": decision.route,
                    "route_reason": decision.reason,
                    "route_signals": decision.signals,
                },
            ),
        ).to_dict()

    def _print_route(self, route: str, reason: str) -> None:
        presentation = getattr(self.renderer, "presentation", None)
        if presentation is not None and not presentation.show_route():
            return
        self.renderer.print_line(
            f"[route] {route}: {reason}",
            style="dim" if self.renderer.rich_output else None,
        )

    def _blocked_by_missing_delete_permission(
        self,
        prompt: str,
        messages: list[dict[str, Any]] | None,
    ) -> dict[str, Any] | None:
        if self.config.runtime_config.allow_delete:
            return None

        normalized = " ".join(prompt.casefold().split())
        delete_signals = (
            "borra",
            "borrar",
            "elimina",
            "eliminar",
            "delete",
            "remove",
            "rm ",
            "quita la carpeta",
            "quita el archivo",
        )
        if not any(signal in normalized for signal in delete_signals):
            return None

        final = (
            "No puedo borrar archivos o carpetas porque el cliente fue iniciado sin "
            "permiso de borrado. Reinicia el cliente con `--allow-delete` y vuelve "
            "a pedirlo."
        )
        memory = list(messages or [])
        memory.append({"role": "user", "content": prompt})
        memory.append({"role": "assistant", "content": final})
        response = {
            "ok": True,
            "done": True,
            "done_reason": "delete_permission_required",
            "message": {"role": "assistant", "content": final},
        }
        printer = getattr(self.renderer, "print_public_result", None)
        if callable(printer):
            printer(final)
        else:
            self.renderer.print_line(final)
        return {
            "final": final,
            "messages": memory,
            "response": response,
            "auto_written_files": [],
            "trace": {"blocked_reason": "delete_permission_required"},
        }

    def _blocked_by_missing_media_permission(
        self,
        prompt: str,
        messages: list[dict[str, Any]] | None,
    ) -> dict[str, Any] | None:
        if self.config.runtime_config.allow_media_input:
            return None

        normalized = " ".join(prompt.casefold().split())
        media_signals = (
            "imagen",
            "imagenes",
            "image",
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".bmp",
            ".tif",
            ".tiff",
            ".gif",
            "lee su contenido",
            "extrae la informacion que veas",
        )
        if not any(signal in normalized for signal in media_signals):
            return None

        final = (
            "No puedo leer contenido visual porque el cliente fue iniciado sin "
            "entrada multimedia. Reinicia el cliente con `--allow-media-input` "
            "y configura `--vision-model <modelo>` si no quieres usar el fallback "
            "por defecto de la tool."
        )
        memory = list(messages or [])
        memory.append({"role": "user", "content": prompt})
        memory.append({"role": "assistant", "content": final})
        response = {
            "ok": True,
            "done": True,
            "done_reason": "media_input_permission_required",
            "message": {"role": "assistant", "content": final},
        }
        printer = getattr(self.renderer, "print_public_result", None)
        if callable(printer):
            printer(final)
        else:
            self.renderer.print_line(final)
        return {
            "final": final,
            "messages": memory,
            "response": response,
            "auto_written_files": [],
            "trace": {"blocked_reason": "media_input_permission_required"},
        }
