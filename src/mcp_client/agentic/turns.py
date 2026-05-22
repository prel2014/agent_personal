from __future__ import annotations

from dataclasses import dataclass

from src.mcp_shared.contracts import ChatMessage, ChatResponse

from ..config.model import ClientConfig
from ..integrations.execution import request_streamed_assistant_message
from ..sessions.tool_call_compat import (
    coerce_textual_tool_call,
    strip_unavailable_tool_calls,
)
from .context_meter import estimate_context_usage
from .ports import OrchestratorPort, RendererPort, ToolRuntimePort
from .state import ConversationMemory


@dataclass
class ChatTurnRequester:
    config: ClientConfig
    runtime: ToolRuntimePort
    renderer: RendererPort
    api: OrchestratorPort

    def request(
        self,
        step: int,
        memory: ConversationMemory,
    ) -> tuple[ChatResponse, ChatMessage]:
        if self.config.stream_responses:
            return self._request_streaming(step, memory)

        request_options = self._chat_request_options()
        self._show_context_usage(step, memory, request_options)
        response = ChatResponse.from_wire(
            self.api.chat(
                messages=memory.to_wire(),
                **request_options,
            )
        )
        if not response.ok:
            raise RuntimeError(response.error or "El servidor devolvio un error.")
        assistant_message = coerce_textual_tool_call(
            response.message,
            request_options["tools"],
        )
        assistant_message = strip_unavailable_tool_calls(
            assistant_message,
            request_options,
        )
        response.message = assistant_message
        self._show_assistant_message(step, assistant_message)
        return response, assistant_message

    def _request_streaming(
        self,
        step: int,
        memory: ConversationMemory,
    ) -> tuple[ChatResponse, ChatMessage]:
        request_options = self._chat_request_options()
        self._show_context_usage(step, memory, request_options)
        response, assistant_message = request_streamed_assistant_message(
            api=self.api,
            renderer=self.renderer,
            messages=memory.to_wire(),
            request_options=request_options,
            step=step,
            show_thinking=self.config.show_thinking,
        )

        return response, assistant_message

    def _chat_request_options(self) -> dict[str, object]:
        client_context = dict(self.runtime.build_context())
        client_context["context_window_tokens"] = self.config.context_window_tokens
        return {
            "tools": self.runtime.list_ollama_tools(),
            "client_context": client_context,
        }

    def _show_context_usage(
        self,
        step: int,
        memory: ConversationMemory,
        request_options: dict[str, object],
    ) -> None:
        presentation = getattr(self.renderer, "presentation", None)
        if presentation is not None:
            if not presentation.show_context_usage(self.config.show_context_meter):
                return
        elif not self.config.show_context_meter:
            return
        printer = getattr(self.renderer, "print_context_usage", None)
        if printer is None:
            return

        client_context = request_options.get("client_context")
        tools = request_options.get("tools")
        label = None
        if isinstance(client_context, dict):
            role = client_context.get("agent_role")
            if isinstance(role, str) and role:
                label = role

        usage = estimate_context_usage(
            messages=memory.to_wire(),
            tools=tools if isinstance(tools, list) else [],
            client_context=client_context if isinstance(client_context, dict) else {},
            max_tokens=self.config.context_window_tokens,
        )
        printer(step, usage, label=label)

    def _show_assistant_message(
        self,
        step: int,
        assistant_message: ChatMessage,
        *,
        show_thinking: bool | None = None,
    ) -> None:
        self.renderer.print_assistant_message(
            step,
            assistant_message.to_wire(),
            show_thinking=self.config.show_thinking if show_thinking is None else show_thinking,
        )
