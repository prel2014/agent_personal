"""Cliente CLI que expone tools locales y delega el razonamiento al servidor."""

from .app import MCPClient
from .config import ClientConfig

__all__ = ["ClientConfig", "MCPClient"]
