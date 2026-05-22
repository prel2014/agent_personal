from .agent import AgentSession
from .store import DEFAULT_SESSION_DB_PATH, SQLiteSessionStore, SessionRecord

__all__ = [
    "AgentSession",
    "DEFAULT_SESSION_DB_PATH",
    "REPLSession",
    "SQLiteSessionStore",
    "SessionRecord",
]


def __getattr__(name: str):
    if name == "REPLSession":
        from ..console import ConsoleREPLSession

        return ConsoleREPLSession
    raise AttributeError(name)
