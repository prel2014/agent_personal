import json
from dataclasses import dataclass

from src.mcp_shared.contracts import ChatMessage

from ..agentic.ports import RendererPort, ToolRuntimePort
from ..agentic.state import ConversationMemory
from .inference import infer_target_paths, looks_like_write_request
from .markdown import extract_code_blocks


@dataclass
class AutoWriteService:
    runtime: ToolRuntimePort
    renderer: RendererPort
    enabled: bool = True

    def write_from_assistant_message(
        self,
        memory: ConversationMemory,
        assistant_message: ChatMessage,
    ) -> list[str]:
        if not self.enabled:
            return []

        assistant_content = assistant_message.content
        if not assistant_content.strip():
            return []

        blocks = extract_code_blocks(assistant_content)
        if not blocks:
            return []

        user_prompt = memory.last_user_prompt()
        if not looks_like_write_request(user_prompt):
            return []

        target_paths = infer_target_paths(user_prompt, assistant_content, blocks)
        if not target_paths:
            self._print(
                "[auto-write] Detecte codigo en Markdown pero no pude inferir una ruta unica para escribir archivos.",
                style="yellow" if self.renderer.rich_output else None,
                always=True,
            )
            return []

        if len(target_paths) < len(blocks):
            self._print(
                "[auto-write] Solo pude inferir algunas rutas; los bloques restantes se omitieron.",
                style="yellow" if self.renderer.rich_output else None,
                always=True,
            )

        written_files: list[str] = []
        for path, code in target_paths:
            if not code.strip():
                continue

            try:
                result = self.runtime.call_tool(
                    "writefile",
                    {
                        "path": path,
                        "content": code,
                    },
                )
            except Exception as exc:
                self._print(
                    f"[auto-write] Error escribiendo {path}: {exc}",
                    style="bold red" if self.renderer.rich_output else None,
                    always=True,
                )
                continue

            if not result.get("success"):
                self._print(
                    f"[auto-write] Fallo writefile para {path}: {result.get('error')}",
                    style="bold red" if self.renderer.rich_output else None,
                    always=True,
                )
                continue

            written_files.append(path)
            memory.append_tool("writefile", json.dumps(result, ensure_ascii=False))

        if written_files:
            self._print(
                f"[auto-write] Archivos escritos: {', '.join(written_files)}",
                style="green" if self.renderer.rich_output else None,
            )

        return written_files

    def _print(
        self,
        text: str,
        *,
        style: str | None = None,
        always: bool = False,
    ) -> None:
        presentation = getattr(self.renderer, "presentation", None)
        if not always and presentation is not None and presentation.is_minimal:
            return
        self.renderer.print_line(text, style=style)
