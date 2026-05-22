from __future__ import annotations

import sys

from ..app import MCPClient
from ..config import load_client_config
from .handlers import dispatch_command
from .parser import build_parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        client = MCPClient(load_client_config(args))
        return dispatch_command(client, args, parser)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
