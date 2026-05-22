import shlex


def parse_command_line(line: str) -> list[str]:
    try:
        tokens = shlex.split(line, posix=False)
    except ValueError as exc:
        raise ValueError(f"No pude parsear el comando: {exc}") from exc

    return [strip_wrapping_quotes(token) for token in tokens if token]


def strip_wrapping_quotes(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
        return token[1:-1]

    return token
