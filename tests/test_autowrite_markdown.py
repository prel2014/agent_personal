from __future__ import annotations

from src.mcp_client.autowrite.markdown import extract_code_blocks


def test_extract_code_blocks_uses_full_text_path_hint_without_argument_collision() -> None:
    blocks = extract_code_blocks(
        "Archivo: alumnos.csv\n\n"
        "```csv\n"
        "id,primer_nombre\n"
        "1,Ana\n"
        "```"
    )

    assert len(blocks) == 1
    assert blocks[0].path_hint == "alumnos.csv"
    assert blocks[0].code == "id,primer_nombre\n1,Ana"
