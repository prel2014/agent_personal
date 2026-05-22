
from .code_functions import *
from .code_tool_registry import (
    register_dotnet_tools,
    register_node_tools,
    register_python_tools,
    register_read_write,
)
from ..registry import ToolRegistry

registry = ToolRegistry()
register_read_write(registry)
register_python_tools(registry)
register_node_tools(registry)
register_dotnet_tools(registry)
