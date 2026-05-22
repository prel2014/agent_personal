from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...config.model import ClientConfig
from ..policies import ToolAccessPolicy
from ..ports import OrchestratorPort, RendererPort, ToolRuntimePort
from ..roles import ReviewDecision
from ..state import AgentRunResult
from ..trace_store import SQLiteTraceStore, TraceStoreSettings, new_trace_id
from ..user_questions import detect_user_question
from .factory import RoleWorkflowFactory
from .results import PublicResultBuilder
from .runner import TeamRoleRunner
from .tracing import TeamTraceLifecycle


@dataclass
class AgentTeamOrchestrator:
    config: ClientConfig
    runtime: ToolRuntimePort
    renderer: RendererPort
    api: OrchestratorPort
    tool_policy: ToolAccessPolicy | None = None
    workflow_factory: RoleWorkflowFactory | None = None
    result_builder: PublicResultBuilder | None = None
    trace_store: SQLiteTraceStore | None = None
    trace_settings: TraceStoreSettings | None = None
    trace_lifecycle: TeamTraceLifecycle | None = None
    role_runner: TeamRoleRunner | None = None

    def __post_init__(self) -> None:
        if self.trace_lifecycle is None:
            self.trace_lifecycle = TeamTraceLifecycle.from_config(
                self.config,
                store=self.trace_store,
                settings=self.trace_settings,
            )
        self.trace_store = self.trace_lifecycle.store
        self.trace_settings = self.trace_lifecycle.settings

        if self.tool_policy is None:
            self.tool_policy = ToolAccessPolicy(_tool_categories_from_runtime(self.runtime))
        if self.workflow_factory is None:
            self.workflow_factory = RoleWorkflowFactory(
                config=self.config,
                runtime=self.runtime,
                api=self.api,
                tool_policy=self.tool_policy,
            )
        if self.result_builder is None:
            self.result_builder = PublicResultBuilder(renderer=self.renderer)
        if self.role_runner is None:
            self.role_runner = TeamRoleRunner(
                config=self.config,
                renderer=self.renderer,
                workflow_factory=self.workflow_factory,
                trace_lifecycle=self.trace_lifecycle,
            )

    def run(
        self,
        prompt: str,
        messages: list[dict[str, Any]] | None = None,
        *,
        trace_run_id: str | None = None,
    ) -> AgentRunResult:
        base_messages = list(messages or [])
        phase_traces: dict[str, Any] = {"mode": "team_orchestrator"}
        run_id = trace_run_id or new_trace_id()
        self.trace_lifecycle.create_run(run_id, prompt, base_messages)

        planner_result = self.role_runner.run_planner(
            prompt,
            base_messages,
            run_id=run_id,
        )
        phase_traces["planner"] = planner_result.trace
        plan_summary = planner_result.final.strip()
        sandbox_only = not self._prompt_requests_outside_sandbox(prompt, base_messages)
        phase_traces["sandbox_scope"] = "sandbox" if sandbox_only else "host"
        planner_question = detect_user_question(plan_summary)
        if planner_question is not None:
            phase_traces["planner_question"] = planner_question.to_dict()
            plan_summary = (
                f"{plan_summary}\n\n"
                "Nota: el planner formulo una pregunta, pero no se detiene la ejecucion. "
                "Continua con supuestos explicitos y resuelve la incertidumbre con inspeccion "
                "local si es posible."
            )

        delivery = self.role_runner.run_delivery_cycle(
            prompt=prompt,
            base_messages=base_messages,
            plan_summary=plan_summary,
            run_id=run_id,
            sandbox_only=sandbox_only,
        )
        final_worker = delivery.worker_runs[-1]

        phase_traces["worker_runs"] = [result.trace for result in delivery.worker_runs]
        phase_traces["review_runs"] = [result.trace for result in delivery.review_runs]
        phase_traces["plan_summary"] = plan_summary
        phase_traces["final_review"] = {
            "approved": delivery.review_decision.approved,
            "summary": delivery.review_decision.summary,
        }
        if delivery.user_question is not None:
            phase_traces["awaiting_user_input"] = delivery.user_question.to_dict()
            result = self.result_builder.build_user_question(
                prompt=prompt,
                base_messages=base_messages,
                source_result=final_worker,
                question=delivery.user_question,
                phase_traces=phase_traces,
            )
            self._complete_trace_run(
                run_id=run_id,
                prompt=prompt,
                base_messages=base_messages,
                result=result,
                plan_summary=plan_summary,
                review_decision=delivery.review_decision,
            )
            return result

        result = self.result_builder.build(
            prompt=prompt,
            base_messages=base_messages,
            final_worker=final_worker,
            worker_runs=delivery.worker_runs,
            review_decision=delivery.review_decision,
            phase_traces=phase_traces,
        )
        self._complete_trace_run(
            run_id=run_id,
            prompt=prompt,
            base_messages=base_messages,
            result=result,
            plan_summary=plan_summary,
            review_decision=delivery.review_decision,
        )
        return result

    def _complete_trace_run(
        self,
        *,
        run_id: str,
        prompt: str,
        base_messages: list[dict[str, Any]],
        result: AgentRunResult,
        plan_summary: str,
        review_decision: ReviewDecision,
    ) -> None:
        self.trace_lifecycle.complete_run(
            run_id=run_id,
            prompt=prompt,
            base_messages=base_messages,
            result=result,
            plan_summary=plan_summary,
            review_decision=review_decision,
        )

    @staticmethod
    def _prompt_requests_outside_sandbox(
        prompt: str,
        messages: list[dict[str, Any]],
    ) -> bool:
        normalized_prompt = " ".join(prompt.casefold().split())
        signals = (
            "fuera del sandbox",
            "outside sandbox",
            "sin sandbox",
            "fuera del aislamiento",
            "usa el host",
            "usar el host",
            "en el host",
            "directamente en el host",
            "sin aislamiento",
        )
        if any(signal in normalized_prompt for signal in signals):
            return True

        for message in reversed(messages):
            if message.get("role") != "user":
                continue
            content = str(message.get("content") or "")
            normalized_message = " ".join(content.casefold().split())
            if any(signal in normalized_message for signal in signals):
                return True
            break
        return False


def _tool_categories_from_runtime(runtime: ToolRuntimePort) -> dict[str, str]:
    context = runtime.build_context()
    raw_categories = context.get("tool_categories")
    if not isinstance(raw_categories, dict):
        return {}

    return {
        name: category
        for name, category in raw_categories.items()
        if isinstance(name, str) and isinstance(category, str)
    }
