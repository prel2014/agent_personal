from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..agentic.user_questions import OPTION_RE, UserQuestion


FREE_TEXT_SENTINEL = "__free_text__"
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
EMPHASIS_RE = re.compile(r"(\*\*|__|\*|_)(.+?)\1")


@dataclass
class UserQuestionAnswerReader:
    client: Any
    prompt_session: Any = None

    def read_answer(self, question: UserQuestion) -> str | None:
        automatic_answer = self._auto_answer_question(question)
        if automatic_answer is not None:
            return automatic_answer

        if question.options:
            interactive_answer = self._read_interactive_question_answer(question)
            if interactive_answer is not None:
                return interactive_answer
            self.client.renderer.print_line(
                "Selecciona una opcion:",
                style="bold cyan" if self.client.renderer.rich_output else None,
            )
            for index, option in enumerate(question.options, start=1):
                self.client.renderer.print_line(f"[{index}] {option}")
            self.client.renderer.print_line("[0] Responder con texto libre")

            while True:
                raw_answer = self._read_selection_prompt("elige> ")
                if raw_answer is None:
                    return None
                raw_answer = raw_answer.strip()
                if not raw_answer:
                    continue
                if raw_answer == "0":
                    break
                if raw_answer.isdigit():
                    index = int(raw_answer)
                    if 1 <= index <= len(question.options):
                        option = question.options[index - 1]
                        return self._selection_answer(index, option)
                self.client.renderer.print_line(
                    "Opcion invalida. Escribe el numero de la opcion.",
                    style="yellow" if self.client.renderer.rich_output else None,
                )

        interactive_text_answer = self._read_interactive_free_text_answer(question)
        if interactive_text_answer is not None:
            return interactive_text_answer

        answer = self._read_selection_prompt("respuesta> ")
        if answer is None:
            return None
        return answer.strip() or None

    def _auto_answer_question(self, question: UserQuestion) -> str | None:
        if not self.client.auto_answer_questions:
            return None

        if question.options:
            option = question.options[0]
            self.client.renderer.print_line(
                f"[auto-question] Seleccionando opcion 1: {option}",
                style="yellow" if self.client.renderer.rich_output else None,
            )
            return self._selection_answer(1, option)

        self.client.renderer.print_line(
            "[auto-question] Respondiendo automaticamente con criterio por defecto.",
            style="yellow" if self.client.renderer.rich_output else None,
        )
        return (
            "Continua con el criterio por defecto mas conservador y minimiza "
            "preguntas adicionales. Si realmente necesitas una decision, reformula "
            "la confirmacion con opciones explicitas."
        )

    def _read_interactive_question_answer(self, question: UserQuestion) -> str | None:
        if self.prompt_session is None or not question.options:
            return None

        try:
            from prompt_toolkit.shortcuts import input_dialog, radiolist_dialog
        except ImportError:
            return None

        style = _dialog_style(with_radio=True)
        values = [
            (str(index), option)
            for index, option in enumerate(question.options, start=1)
        ]
        values.append((FREE_TEXT_SENTINEL, "Responder con texto libre"))
        dialog_text = self._format_question_dialog_text(question)

        selection = radiolist_dialog(
            title="Pregunta del agente",
            text=(
                f"{dialog_text}\n\n"
                "Usa las flechas para navegar. Tab cambia entre lista y botones."
            ),
            values=values,
            ok_text="Enviar",
            cancel_text="Cancelar",
            style=style,
        ).run()

        if selection is None:
            return None

        if selection == FREE_TEXT_SENTINEL:
            answer = input_dialog(
                title="Respuesta libre",
                text="Escribe tu respuesta. Tab navega entre campo y botones.",
                ok_text="Enviar",
                cancel_text="Cancelar",
                style=style,
            ).run()
            if answer is None:
                return None
            return answer.strip() or None

        selected_index = int(selection)
        option = question.options[selected_index - 1]
        return self._selection_answer(selected_index, option)

    @staticmethod
    def _selection_answer(index: int, option: str) -> str:
        return (
            f"Selecciono la opcion {index}: {option}. "
            "Continua con esa opcion y ejecuta el trabajo con herramientas reales "
            "cuando corresponda. No te limites a describir el siguiente paso."
        )

    def _read_interactive_free_text_answer(self, question: UserQuestion) -> str | None:
        if self.prompt_session is None:
            return None

        try:
            from prompt_toolkit.shortcuts import input_dialog
        except ImportError:
            return None

        dialog_text = self._format_question_dialog_text(question)
        answer = input_dialog(
            title="Pregunta del agente",
            text=(
                f"{dialog_text}\n\n"
                "Escribe tu respuesta. Tab navega entre campo y botones."
            ),
            ok_text="Enviar",
            cancel_text="Cancelar",
            style=_dialog_style(),
        ).run()
        if answer is None:
            return None
        return answer.strip() or None

    def _format_question_dialog_text(self, question: UserQuestion) -> str:
        lines: list[str] = []
        for raw_line in question.text.splitlines():
            if question.options and OPTION_RE.match(raw_line):
                continue
            normalized = _normalize_markdown_line(raw_line)
            if normalized or (lines and lines[-1]):
                lines.append(normalized)

        text = "\n".join(lines).strip()
        return text or "El agente necesita una confirmacion."

    def _read_selection_prompt(self, prompt: str) -> str | None:
        try:
            if self.prompt_session is not None:
                return self.prompt_session.prompt(prompt)
            return input(prompt)
        except KeyboardInterrupt:
            self.client.renderer.print_line()
            return None
        except EOFError:
            self.client.renderer.print_line()
            return None


def _normalize_markdown_line(line: str) -> str:
    normalized = line.rstrip()
    normalized = MARKDOWN_LINK_RE.sub(r"\1", normalized)
    normalized = INLINE_CODE_RE.sub(r"\1", normalized)
    normalized = EMPHASIS_RE.sub(r"\2", normalized)
    normalized = normalized.replace("```", "")
    normalized = normalized.replace("`", "")
    normalized = re.sub(r"^\s{0,3}#{1,6}\s*", "", normalized)
    normalized = re.sub(r"^\s*>\s?", "", normalized)
    normalized = re.sub(r"^\s*[-*+]\s+\[[ xX]\]\s*", "", normalized)
    normalized = re.sub(r"^\s*[-*+]\s*", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _dialog_style(*, with_radio: bool = False):
    from prompt_toolkit.styles import Style

    values = {
        "dialog": "bg:#111111",
        "dialog frame.label": "bg:#111111 #8bd5ca bold",
        "dialog.body": "bg:#1a1a1a #f5f5f5",
        "dialog shadow": "bg:#000000",
        "button": "bg:#2a2a2a #d0d0d0",
        "button.focused": "bg:#8bd5ca #101010 bold",
    }
    if with_radio:
        values["radio"] = "#8bd5ca"
        values["radio-selected"] = "#8bd5ca bold"
    return Style.from_dict(values)
