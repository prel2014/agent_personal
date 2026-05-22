import re

from .markdown import CodeBlock, TEXT_PATH_RE


FILENAME_RE = re.compile(
    r"""(?ix)
    (?<![\w./\\-])
    (?P<path>[A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+)
    (?![\w./\\-])
    """
)

WRITE_INTENT_RE = re.compile(
    r"""(?ix)
    \b(
        crea(?:r)? |
        escribe(?:r)? |
        guarda(?:r)? |
        genera(?:r)? |
        modifica(?:r)? |
        actualiza(?:r)? |
        reemplaza(?:r)? |
        guarda(?:lo|la|me)? |
        save |
        write |
        update |
        create
    )\b
    """
)


def looks_like_write_request(user_prompt: str) -> bool:
    return bool(WRITE_INTENT_RE.search(user_prompt))


def infer_target_paths(
    user_prompt: str,
    assistant_content: str,
    blocks: list[CodeBlock],
) -> list[tuple[str, str]] | None:
    if not blocks:
        return None

    if len(blocks) == 1:
        path = _first_path_hint(blocks, user_prompt, assistant_content)
        if not path:
            return None

        return [(path, blocks[0].code)]

    results: list[tuple[str, str]] = []
    seen_paths: set[str] = set()
    for block in blocks:
        path = block.path_hint
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        results.append((path, block.code))

    if results:
        return results

    return None


def _first_path_hint(
    blocks: list[CodeBlock],
    user_prompt: str,
    assistant_content: str,
) -> str | None:
    for block in blocks:
        if block.path_hint:
            return block.path_hint

    text_match = TEXT_PATH_RE.search(assistant_content)
    if text_match:
        return text_match.group("path")

    prompt_matches = [match.group("path") for match in FILENAME_RE.finditer(user_prompt)]
    prompt_unique = list(dict.fromkeys(prompt_matches))
    if len(prompt_unique) == 1:
        return prompt_unique[0]

    return None
