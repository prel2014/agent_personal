from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.mcp_shared.contracts import ChatMessage, ChatResponse

from ..ports import RendererPort
from ..roles import ReviewDecision
from ..state import AgentRunResult, ConversationMemory
from ..user_questions import UserQuestion

@dataclass
class PublicResultBuilder:
    renderer: RendererPort

    def build(
        self,
        *,
        prompt: str,
        base_messages: list[dict[str, Any]],
        final_worker: AgentRunResult,
        worker_runs: list[AgentRunResult],
        review_decision: ReviewDecision,
        phase_traces: dict[str, Any],
    ) -> AgentRunResult:
        final_text = final_worker.final
        if not review_decision.approved:
            final_text = (
                f"{final_worker.final}\n\n"
                "Nota de revision:\n"
                f"{review_decision.summary}"
            )
            self.renderer.print_line(
                f"[review] {review_decision.summary}",
                style="yellow" if self.renderer.rich_output else None,
            )

        self._print_public_final(final_text)

        public_memory = ConversationMemory.from_wire(base_messages)
        public_memory.append_user(prompt)
        public_memory.append_assistant(ChatMessage.assistant(content=final_text))
        response = ChatResponse(
            ok=True,
            model=final_worker.response.model,
            node_id=final_worker.response.node_id,
            node_model=final_worker.response.node_model,
            done=True,
            done_reason=(
                "review_approved"
                if review_decision.approved
                else "review_requires_changes"
            ),
            message=ChatMessage.assistant(content=final_text),
        )
        return AgentRunResult(
            final=final_text,
            memory=public_memory,
            response=response,
            auto_written_files=self._merge_auto_written_files(worker_runs),
            trace=phase_traces,
        )

    def build_user_question(
        self,
        *,
        prompt: str,
        base_messages: list[dict[str, Any]],
        source_result: AgentRunResult,
        question: UserQuestion,
        phase_traces: dict[str, Any],
    ) -> AgentRunResult:
        public_memory = ConversationMemory.from_wire(base_messages)
        public_memory.append_user(prompt)
        public_memory.append_assistant(ChatMessage.assistant(content=question.text))
        response = ChatResponse(
            ok=True,
            model=source_result.response.model,
            node_id=source_result.response.node_id,
            node_model=source_result.response.node_model,
            done=True,
            done_reason="awaiting_user_input",
            message=ChatMessage.assistant(content=question.text),
        )
        return AgentRunResult(
            final=question.text,
            memory=public_memory,
            response=response,
            auto_written_files=list(source_result.auto_written_files),
            trace=phase_traces,
        )

    @staticmethod
    def _merge_auto_written_files(results: list[AgentRunResult]) -> list[str]:
        merged: list[str] = []
        for result in results:
            for path in result.auto_written_files:
                if path not in merged:
                    merged.append(path)
        return merged

    def _print_public_final(self, final_text: str) -> None:
        presentation = getattr(self.renderer, "presentation", None)
        if presentation is not None and not presentation.show_public_final_from_team():
            return

        printer = getattr(self.renderer, "print_public_result", None)
        if callable(printer):
            printer(final_text)
            return

        self.renderer.print_line(final_text)
