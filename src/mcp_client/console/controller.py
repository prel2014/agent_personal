from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repl import ConsoleREPLSession


@dataclass
class ConsoleREPLController:
    def run(
        self,
        session: "ConsoleREPLSession",
        *,
        session_id: str | None = None,
        continue_session: bool = False,
    ) -> int:
        self._load_initial_session(
            session,
            session_id=session_id,
            continue_session=continue_session,
        )
        self._print_startup(session)

        while True:
            prompt = session.input_reader.read_prompt()
            if prompt is None:
                session.client.renderer.print_line()
                return 0

            if not prompt:
                continue

            if prompt.lower() in {"exit", "quit", "salir"}:
                return 0

            if session.slash_router.handles(prompt):
                if self._run_slash_command(session, prompt):
                    return 0
                continue

            session.conversation_runner.run_prompt_until_complete(session, prompt)

    def _print_startup(self, session: "ConsoleREPLSession") -> None:
        session.client.renderer.print_line(
            "Cliente MCP listo. Escribe tu prompt o 'exit' para salir.",
            style="bold green" if session.client.renderer.rich_output else None,
        )
        if session.prompt_session is not None:
            session.client.renderer.print_line(
                "Atajos: Ctrl+T alterna thinking, Ctrl+Y alterna auto-preguntas. Respaldo: /thinking y /questions.",
                style="dim" if session.client.renderer.rich_output else None,
            )
        else:
            session.client.renderer.print_line(
                "Atajos de teclado no disponibles en esta terminal. Usa /thinking y /questions.",
                style="yellow" if session.client.renderer.rich_output else None,
            )
        if session.current_session_id:
            session.client.renderer.print_line(
                f"Sesion activa: {session.current_session_id}",
                style="dim" if session.client.renderer.rich_output else None,
            )

    def _run_slash_command(self, session: "ConsoleREPLSession", prompt: str) -> bool:
        try:
            command_result = session.slash_router.run(prompt, session.command_context)
            if command_result.clear_messages:
                session.messages = []
            return command_result.exit_repl
        except Exception as exc:
            session.client.renderer.print_line(f"[error] {exc}", style="bold red")
            return False

    def _load_initial_session(
        self,
        session: "ConsoleREPLSession",
        *,
        session_id: str | None,
        continue_session: bool,
    ) -> None:
        if session_id and continue_session:
            raise ValueError("Usa --session o --continue, no ambos.")

        if continue_session:
            latest = session.client.session_store.latest_session()
            if latest is None:
                session.messages = []
                session.current_session_id = None
                return
            session_id = latest.id

        if session_id:
            session.client.session_store.require_session(session_id)
            session.messages = session.client.session_store.load_messages(session_id)
            session.current_session_id = session_id
            return

        session.messages = []
        session.current_session_id = None
