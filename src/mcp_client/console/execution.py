from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..agentic.user_questions import detect_user_question
from .hotkeys import RuntimeHotkeyManager

if TYPE_CHECKING:
    from .repl import ConsoleREPLSession


@dataclass
class ConsoleConversationRunner:
    def run_prompt_until_complete(
        self,
        session: "ConsoleREPLSession",
        prompt: str,
    ) -> None:
        next_prompt: str | None = prompt
        force_team_next = False
        while next_prompt:
            try:
                with RuntimeHotkeyManager(session.client):
                    result = session.client.ask(
                        next_prompt,
                        messages=session.messages,
                        force_team=force_team_next,
                    )
                force_team_next = False
            except Exception as exc:
                session.client.renderer.print_line(f"[error] {exc}", style="bold red")
                return

            session.messages = result["messages"]
            self.persist_active_session(session)
            response = result.get("response")
            if not (
                isinstance(response, dict)
                and response.get("done_reason") == "awaiting_user_input"
            ):
                return
            question = detect_user_question(result.get("final", ""))
            if question is None:
                return
            next_prompt = session.question_reader.read_answer(question)
            force_team_next = next_prompt is not None

    def persist_active_session(self, session: "ConsoleREPLSession") -> None:
        if not session.current_session_id:
            return
        session.client.session_store.replace_messages(
            session.current_session_id,
            session.messages,
        )
