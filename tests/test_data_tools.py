from __future__ import annotations

import pytest

from src.mcp.tools.helpers.data_tools import determinar_tipo_dato


def test_determinar_tipo_dato_reads_csv(tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("id,name\n1,Ana\n2,Luis\n", encoding="utf-8")

    result = determinar_tipo_dato(path=str(csv_path), max_rows=1)

    assert result["rows"] == 2
    assert result["columns"] == 2
    assert result["cabeceras"] == ["id", "name"]
    assert result["data"] == [["1", "Ana"]]
    assert set(result["tipos"]) == {"id", "name"}


def test_determinar_tipo_dato_rejects_unknown_extension(tmp_path):
    data_path = tmp_path / "sample.txt"
    data_path.write_text("id,name\n1,Ana\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Formato no soportado"):
        determinar_tipo_dato(path=str(data_path))
