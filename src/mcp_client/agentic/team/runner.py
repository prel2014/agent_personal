from __future__ import annotations

from dataclasses import dataclass

from ...config.model import ClientConfig
from ...render.null import NullRenderer, ThinkingOnlyRenderer, ToolEventRenderer
from ..ports import RendererPort
from ..roles import PLANNER_SPEC, REVIEWER_SPEC, WORKER_SPEC, ReviewDecision, RoleSpec
from ..state import AgentRunResult
from ..user_questions import UserQuestion, detect_user_question
from .factory import RoleWorkflowFactory
from .prompts import build_review_prompt, build_worker_directive, build_worker_retry_prompt
from .tracing import TeamTraceLifecycle


@dataclass(frozen=True)
class DeliveryCycleResult:
    worker_runs: list[AgentRunResult]
    review_runs: list[AgentRunResult]
    review_decision: ReviewDecision
    user_question: UserQuestion | None = None


@dataclass
class TeamRoleRunner:
    config: ClientConfig
    renderer: RendererPort
    workflow_factory: RoleWorkflowFactory
    trace_lifecycle: TeamTraceLifecycle

    def run_planner(
        self,
        prompt: str,
        base_messages: list[dict[str, object]],
        *,
        run_id: str,
    ) -> AgentRunResult:
        self._announce("planner")
        return self._run_role(
            spec=PLANNER_SPEC,
            directive=PLANNER_SPEC.directive,
            prompt=prompt,
            messages=base_messages,
            renderer=self._silent_or_thinking_renderer("planner"),
            auto_write=False,
            max_steps=self.config.planner_max_steps,
            run_id=run_id,
            attempt=1,
            sandbox_only=True,
        )

    def run_delivery_cycle(
        self,
        *,
        prompt: str,
        base_messages: list[dict[str, object]],
        plan_summary: str,
        run_id: str,
        sandbox_only: bool = True,
    ) -> DeliveryCycleResult:
        worker_runs: list[AgentRunResult] = []
        review_runs: list[AgentRunResult] = []
        worker_directive = build_worker_directive(plan_summary)
        worker_messages = list(base_messages)
        worker_prompt = prompt
        attempt_count = self.config.review_retries + 1

        for attempt in range(1, attempt_count + 1):
            worker_result = self._run_worker_attempt(
                attempt=attempt,
                directive=worker_directive,
                prompt=worker_prompt,
                messages=worker_messages,
                run_id=run_id,
                sandbox_only=sandbox_only,
            )
            worker_runs.append(worker_result)
            user_question = detect_user_question(worker_result.final)
            if user_question is not None:
                self._announce("esperando respuesta del usuario")
                return DeliveryCycleResult(
                    worker_runs=worker_runs,
                    review_runs=review_runs,
                    review_decision=ReviewDecision(
                        approved=True,
                        summary="awaiting_user_input",
                    ),
                    user_question=user_question,
                )

            reviewer_result = self._run_reviewer(
                prompt=prompt,
                base_messages=base_messages,
                plan_summary=plan_summary,
                worker_result=worker_result,
                attempt=attempt,
                run_id=run_id,
                sandbox_only=sandbox_only,
            )
            review_runs.append(reviewer_result)

            review_decision = ReviewDecision.from_text(reviewer_result.final)
            if review_decision.approved:
                self._announce("review aprobado")
                return DeliveryCycleResult(
                    worker_runs=worker_runs,
                    review_runs=review_runs,
                    review_decision=review_decision,
                )

            if attempt < attempt_count:
                self._announce("review pidio cambios; corrigiendo")
                worker_messages = worker_result.memory.to_wire()
                worker_prompt = build_worker_retry_prompt(reviewer_result.final)

        return DeliveryCycleResult(
            worker_runs=worker_runs,
            review_runs=review_runs,
            review_decision=ReviewDecision.from_text(review_runs[-1].final),
        )

    def _run_worker_attempt(
        self,
        *,
        attempt: int,
        directive: str,
        prompt: str,
        messages: list[dict[str, object]],
        run_id: str,
        sandbox_only: bool,
    ) -> AgentRunResult:
        self._announce("worker" if attempt == 1 else f"worker retry {attempt - 1}")
        renderer = self.renderer
        presentation = getattr(self.renderer, "presentation", None)
        if presentation is not None and not presentation.show_intermediate_assistant():
            renderer = ToolEventRenderer(self.renderer)
        return self._run_role(
            spec=WORKER_SPEC,
            directive=directive,
            prompt=prompt,
            messages=messages,
            renderer=renderer,
            auto_write=self.config.auto_write_code,
            max_steps=self.config.max_steps,
            run_id=run_id,
            attempt=attempt,
            sandbox_only=sandbox_only,
        )

    def _run_reviewer(
        self,
        *,
        prompt: str,
        base_messages: list[dict[str, object]],
        plan_summary: str,
        worker_result: AgentRunResult,
        attempt: int,
        run_id: str,
        sandbox_only: bool,
    ) -> AgentRunResult:
        self._announce("reviewer")
        return self._run_role(
            spec=REVIEWER_SPEC,
            directive=REVIEWER_SPEC.directive,
            prompt=build_review_prompt(
                original_prompt=prompt,
                plan_summary=plan_summary,
                worker_result=worker_result,
            ),
            messages=base_messages,
            renderer=self._silent_or_thinking_renderer("reviewer"),
            auto_write=False,
            max_steps=self.config.reviewer_max_steps,
            run_id=run_id,
            attempt=attempt,
            sandbox_only=sandbox_only,
        )

    def _run_role(
        self,
        *,
        spec: RoleSpec,
        directive: str,
        prompt: str,
        messages: list[dict[str, object]],
        renderer: RendererPort,
        auto_write: bool,
        max_steps: int,
        run_id: str,
        attempt: int,
        sandbox_only: bool,
    ) -> AgentRunResult:
        workflow = self.workflow_factory.build(
            spec=spec,
            directive=directive,
            renderer=renderer,
            auto_write=auto_write,
            max_steps=max_steps,
            sandbox_only=sandbox_only,
        )
        return workflow.run(
            prompt,
            messages=messages,
            hooks=self.trace_lifecycle.hooks(
                run_id=run_id,
                role=spec.role.value,
                attempt=attempt,
            ),
        )

    def _announce(self, label: str) -> None:
        presentation = getattr(self.renderer, "presentation", None)
        if presentation is not None and not presentation.show_team_phase():
            return
        self.renderer.print_line(
            f"[team] {label}",
            style="bold blue" if self.renderer.rich_output else None,
        )

    def _silent_or_thinking_renderer(self, label: str) -> RendererPort:
        if self.config.show_context_meter or self.config.show_thinking:
            return ThinkingOnlyRenderer(self.renderer, label=label)
        return NullRenderer()
