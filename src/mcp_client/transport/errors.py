class MCPClientTransportError(RuntimeError):
    pass


class MCPServerResponseError(MCPClientTransportError):
    pass


class MCPServerTimeoutError(MCPClientTransportError):
    pass


class MCPServerConnectionError(MCPClientTransportError):
    pass
