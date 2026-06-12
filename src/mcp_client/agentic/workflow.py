from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from ..autowrite.service import AutoWriteService
from ..config.model import ClientConfig
from ..integrations.execution import ToolCallProcessor
from .hooks import CompositeWorkflowHook, TraceWorkflowHook, WorkflowHook
from .policies import FinalAnswerRuntimeView
from .ports import OrchestratorPort, RendererPort, ToolRuntimePort
from .state import AgentRunResult, AgentWorkflowState, ConversationMemory, WorkflowStage
from .tracing import TraceRecorder
from .context_window import trim_messages
from .turns import ChatTurnRequester


@dataclass
class AgentWorkflow:
    config: ClientConfig
    runtime: ToolRuntimePort
    renderer: RendererPort
    api: OrchestratorPort
    tool_call_processor: ToolCallProcessor
    auto_write_service: AutoWriteService
    turn_requester: ChatTurnRequester | None = None

    def __post_init__(self) -> None:
        if self.turn_requester is None:
            self.turn_requester = ChatTurnRequester(
                config=self.config,
                runtime=self.runtime,
                renderer=self.renderer,
                api=self.api,
            )

    def run(
        self,
        prompt: str,
        messages: list[dict[str, object]] | None = None,
        *,
        hooks: Iterable[WorkflowHook] = (),
        trace_recorder: TraceRecorder | None = None,
    ) -> AgentRunResult:
        recorder = trace_recorder or TraceRecorder()
        hook_chain = CompositeWorkflowHook((TraceWorkflowHook(recorder), *hooks))

        memory = ConversationMemory.from_wire(messages)
        memory.append_user(prompt)

        state = AgentWorkflowState(
            memory=memory,
            stage=WorkflowStage.PLANNING,
        )
        hook_chain.on_workflow_started(state)

        for step in range(1, self.config.max_steps + 1):
            state.current_step = step
            state.stage = WorkflowStage.REQUESTING_ASSISTANT
            hook_chain.on_stage_changed(state, detail="requesting assistant turn")

            if self.config.context_auto_trim:
                state.memory.messages, _ = trim_messages(
                    state.memory.messages,
                    max_tokens=self.config.context_window_tokens,
                    ratio=self.config.context_trim_ratio,
                    min_turns=self.config.context_trim_min_turns,
                )

            response, assistant_message = self.turn_requester.request(step, state.memory)
            state.last_response = response
            state.memory.append_assistant(assistant_message)
            hook_chain.on_assistant_response(state, response)

            if not assistant_message.tool_calls:
                state.stage = WorkflowStage.AUTO_WRITING
                hook_chain.on_stage_changed(state, detail="finalizing response")

                auto_written_files = self.auto_write_service.write_from_assistant_message(
                    state.memory,
                    assistant_message,
                )
                hook_chain.on_auto_write(state, auto_written_files)

                state.stage = WorkflowStage.COMPLETED
                result = AgentRunResult(
                    final=assistant_message.content,
                    memory=state.memory,
                    response=response,
                    auto_written_files=auto_written_files,
                )
                hook_chain.on_workflow_completed(state, result)
                persisted_trace = dict(result.trace)
                result.trace = recorder.to_dict()
                result.trace.update(persisted_trace)
                return result

            state.stage = WorkflowStage.EXECUTING_TOOLS
            hook_chain.on_stage_changed(state, detail="executing tool calls")
            outcomes = self.tool_call_processor.process(
                assistant_message.tool_calls,
                state.memory,
            )
            for outcome in outcomes:
                hook_chain.on_tool_outcome(state, outcome)

        return self._finalize_after_tool_limit(state, hook_chain, recorder)

    def _finalize_after_tool_limit(
        self,
        state: AgentWorkflowState,
        hook_chain: CompositeWorkflowHook,
        recorder: TraceRecorder,
    ) -> AgentRunResult:
        state.memory.append_user(
            "Se alcanzo el maximo de iteraciones con herramientas. "
            "No uses mas herramientas. Entrega una respuesta final concreta con la "
            "informacion disponible; si falta informacion, indicalo como limitacion."
        )
        state.current_step = self.config.max_steps + 1
        state.stage = WorkflowStage.REQUESTING_ASSISTANT
        hook_chain.on_stage_changed(state, detail="requesting final answer without tools")

        final_requester = ChatTurnRequester(
            config=replace(self.config, stream_responses=False),
            runtime=FinalAnswerRuntimeView(
                self.runtime,
                directive=(
                    "Cierra ahora sin herramientas. No pidas ni emitas tool calls. "
                    "Usa solo los resultados ya presentes en la conversacion."
                ),
            ),
            renderer=self.renderer,
            api=self.api,
        )
        response, assistant_message = final_requester.request(
            state.current_step,
            state.memory,
        )
        if assistant_message.tool_calls:
            raise RuntimeError(
                f"Se alcanzo el maximo de iteraciones ({self.config.max_steps}) "
                "y el modelo siguio solicitando herramientas durante el cierre."
            )

        state.last_response = response
        state.memory.append_assistant(assistant_message)
        hook_chain.on_assistant_response(state, response)

        state.stage = WorkflowStage.AUTO_WRITING
        hook_chain.on_stage_changed(state, detail="finalizing response after tool limit")
        auto_written_files = self.auto_write_service.write_from_assistant_message(
            state.memory,
            assistant_message,
        )
        hook_chain.on_auto_write(state, auto_written_files)

        state.stage = WorkflowStage.COMPLETED
        result = AgentRunResult(
            final=assistant_message.content,
            memory=state.memory,
            response=response,
            auto_written_files=auto_written_files,
        )
        hook_chain.on_workflow_completed(state, result)
        persisted_trace = dict(result.trace)
        result.trace = recorder.to_dict()
        result.trace.update(persisted_trace)
        result.trace["tool_limit_finalized"] = True
        return result
