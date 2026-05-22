from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..slash import CommandContext, SlashCommandRouter, create_default_router
from .controller import ConsoleREPLController
from .execution import ConsoleConversationRunner
from .input import ConsoleInputReader, create_console_prompt_session
from .questions import UserQuestionAnswerReader

if TYPE_CHECKING:
    from ..app import MCPClient


@dataclass
class ConsoleREPLSession:
    client: "MCPClient"
    slash_router: SlashCommandRouter = field(init=False)
    command_context: CommandContext = field(init=False)
    prompt_session: Any = field(init=False, default=None)
    input_reader: ConsoleInputReader = field(init=False)
    question_reader: UserQuestionAnswerReader = field(init=False)
    conversation_runner: ConsoleConversationRunner = field(init=False)
    controller: ConsoleREPLController = field(init=False)
    messages: list[dict[str, Any]] = field(default_factory=list)
    current_session_id: str | None = None

    def __post_init__(self) -> None:
        self.slash_router = create_default_router()
        self.command_context = CommandContext(
            client=self.client,
            repl_session=self,
        )
        self.prompt_session = create_console_prompt_session(
            self.slash_router,
            self.command_context,
        )
        self.input_reader = ConsoleInputReader(self.prompt_session)
        self.question_reader = UserQuestionAnswerReader(
            client=self.client,
            prompt_session=self.prompt_session,
        )
        self.conversation_runner = ConsoleConversationRunner()
        self.controller = ConsoleREPLController()

    def run(
        self,
        *,
        session_id: str | None = None,
        continue_session: bool = False,
    ) -> int:
        return self.controller.run(
            self,
            session_id=session_id,
            continue_session=continue_session,
        )
