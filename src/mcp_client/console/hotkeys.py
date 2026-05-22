from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable, Iterable


CTRL_T = "\x14"
CTRL_Y = "\x19"


class RuntimeHotkeyManager:
    def __init__(
        self,
        client,
        *,
        renderer=None,
        key_reader: Callable[[], Iterable[str]] | None = None,
        poll_interval: float = 0.05,
    ) -> None:
        self.client = client
        self.renderer = renderer or getattr(client, "renderer", None)
        self.key_reader = key_reader or self._default_key_reader()
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "RuntimeHotkeyManager":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    @property
    def active(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        if self.key_reader is None or self.active:
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="mcp-client-runtime-hotkeys",
            daemon=True,
        )
        self._thread.start()
        self._print(
            "Atajos activos durante ejecucion: Ctrl+T thinking, Ctrl+Y preguntas.",
            style="dim",
        )
        return True

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=0.5)
        self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                keys = self.key_reader() if self.key_reader is not None else ()
                for key in keys:
                    self.handle_key(key)
            except Exception:
                return
            time.sleep(self.poll_interval)

    def handle_key(self, key: str) -> bool:
        if key == CTRL_T:
            enabled = self.client.toggle_show_thinking()
            state = "ON" if enabled else "OFF"
            self._print(f"[hotkey] thinking: {state}", style="yellow")
            return True

        if key == CTRL_Y:
            enabled = self.client.toggle_auto_answer_questions()
            state = "AUTO" if enabled else "MANUAL"
            self._print(f"[hotkey] preguntas: {state}", style="yellow")
            return True

        return False

    def _print(self, text: str, *, style: str | None = None) -> None:
        if self.renderer is None:
            return
        printer = getattr(self.renderer, "print_line", None)
        if callable(printer):
            printer(text, style=style if getattr(self.renderer, "rich_output", False) else None)

    @staticmethod
    def _default_key_reader() -> Callable[[], Iterable[str]] | None:
        if sys.platform != "win32":
            return None

        try:
            import msvcrt
        except ImportError:
            return None

        def read_keys() -> list[str]:
            keys: list[str] = []
            while msvcrt.kbhit():
                key = msvcrt.getwch()
                if key in {"\x00", "\xe0"} and msvcrt.kbhit():
                    msvcrt.getwch()
                    continue
                keys.append(key)
            return keys

        return read_keys
