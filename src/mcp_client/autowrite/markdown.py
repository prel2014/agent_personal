import re
from dataclasses import dataclass

PATH_ATTR_RE = re.compile(
    r"""(?ix)
    (?:path|file|filename|title)
    \s*=\s*
    ["']?
    (?P<path>[A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+)
    """
)

LINE_PATH_RE = re.compile(
    r"""(?imx)
    ^\s*
    (?:
        \# |
        // |
        -- |
        /\*
    )?
    \s*
    (?:
        archivo |
        file |
        filename |
        ruta |
        path
    )
    \s*:\s*
    (?P<path>[A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+)
    \s*
    (?:\*/)?
    \s*$
    """
)

TEXT_PATH_RE = re.compile(
    r"""(?imx)
    (?:
        archivo |
        file |
        filename |
        ruta |
        path
    )
    \s*:\s*
    (?P<path>[A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+)
    """
)


@dataclass(frozen=True)
class CodeBlock:
    language: str
    code: str
    path_hint: str | None = None


def extract_code_blocks(text: str) -> list[CodeBlock]:
    blocks: list[CodeBlock] = []

    fence_matches = list(iter_fenced_blocks_with_spans(text))
    previous_end = 0
    for block_match in fence_matches:
        info = block_match.info
        code = block_match.body
        path_hint = _extract_path_hint(
            info,
            code,
            full_text=text,
            previous_text=text[previous_end:block_match.start],
            total_blocks=len(fence_matches),
        )
        cleaned_code = _strip_path_hint_line(code)
        blocks.append(
            CodeBlock(
                language=block_match.language,
                code=cleaned_code,
                path_hint=path_hint,
            )
        )
        previous_end = block_match.end

    return blocks


@dataclass(frozen=True)
class _FenceMatch:
    start: int
    end: int
    info: str
    language: str
    body: str


def iter_fenced_blocks_with_spans(text: str):
    pattern = re.compile(
        r"```(?P<info>[^\n`]*)\n(?P<body>.*?)\n```",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        info = (match.group("info") or "").strip()
        yield _FenceMatch(
            start=match.start(),
            end=match.end(),
            info=info,
            language=info.split()[0] if info else "",
            body=match.group("body"),
        )


def _extract_path_hint(
    info: str,
    code: str,
    full_text: str,
    *,
    previous_text: str,
    total_blocks: int,
) -> str | None:
    info_match = PATH_ATTR_RE.search(info)
    if info_match:
        return info_match.group("path")

    line_match = LINE_PATH_RE.search(code)
    if line_match:
        return line_match.group("path")

    window_matches = list(TEXT_PATH_RE.finditer(previous_text))
    window_match = window_matches[-1] if window_matches else None
    if window_match:
        return window_match.group("path")

    if total_blocks == 1:
        text_matches = list(TEXT_PATH_RE.finditer(full_text))
        text_match = text_matches[-1] if text_matches else None
        if text_match:
            return text_match.group("path")

    return None


def _strip_path_hint_line(code: str) -> str:
    lines = code.splitlines()
    if not lines:
        return code

    first_line = lines[0]
    if LINE_PATH_RE.match(first_line):
        return "\n".join(lines[1:])

    return code
