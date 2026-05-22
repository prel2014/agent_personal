from __future__ import annotations

from pathlib import Path
from typing import Any
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..models import ToolDefinition, ToolParameter
from ..registry import ToolRegistry
from ..categories import READ, EXECUTE


def guardar_grafico_estadistico(path: str, data: dict[str, Any], titulo: str) -> dict[str, Any]:
    categorias = data["categorias"]
    subgrupos = data["subgrupos"]
    matriz = np.asarray(data["matriz"], dtype=float)
    if matriz.shape != (len(categorias), len(subgrupos)):
        raise ValueError(
            "La matriz debe tener una fila por categoria y una columna por subgrupo."
        )

    x = np.arange(len(categorias))
    n = len(subgrupos)
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    for i in range(n):
        desplazamiento = (i - (n - 1) / 2) * width

        ax.bar(
            x + desplazamiento,
            matriz[:, i],
            width,
            label=subgrupos[i]
        )
    ax.set_title(titulo)
    ax.set_xlabel("Carreras profesionales")
    ax.set_ylabel("Cantidad de alumnos")
    ax.set_xticks(x)
    ax.set_xticklabels(categorias, rotation=35, ha="right")
    ax.legend()
    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return {
        "success": True,
        "path": str(Path(path)),
        "categorias": len(categorias),
        "subgrupos": len(subgrupos),
    }



SUPPORTED_DATA_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xls", ".json"}


def determinar_tipo_dato(
    path: str | None = None,
    url: str | None = None,
    max_rows: int = 5,
) -> dict[str, Any]:
    source = path or url
    if not source:
        raise ValueError("Debes indicar 'path' con la ruta del archivo.")

    file_path = Path(source)
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_DATA_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_DATA_SUFFIXES))
        raise ValueError(f"Formato no soportado: {suffix or '(sin extension)'}. Usa {supported}.")

    if not file_path.exists():
        raise FileNotFoundError(f"El archivo no existe: {source}")

    if suffix == ".csv":
        df = pd.read_csv(file_path)
    elif suffix == ".tsv":
        df = pd.read_csv(file_path, sep="\t")
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(file_path)
    else:
        df = pd.read_json(file_path)

    row_limit = max(1, min(int(max_rows), 50))
    info = {
        "path": str(file_path),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "cabeceras": [str(column) for column in df.columns],
        "tipos": {str(column): str(dtype) for column, dtype in df.dtypes.items()},
        "data": df.head(row_limit).astype(str).values.tolist(),
    }
    return info


registry = ToolRegistry()
registry.register(
    ToolDefinition(
        name="determinar_tipo_dato",
        description="Lee un archivo tabular y devuelve cabeceras, tipos y una muestra de filas.",
        category=READ,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del archivo CSV, TSV, XLSX, XLS o JSON a cargar.",
            ),
            ToolParameter(
                name="max_rows",
                type="integer",
                description="Cantidad maxima de filas de muestra a devolver.",
                required=False,
            ),
            ToolParameter(
                name="url",
                type="string",
                description="Alias heredado de path. Preferir path.",
                required=False,
            ),
        ],
    ),
    determinar_tipo_dato,
)


registry.register(
    ToolDefinition(
        name="generar_grafico_barras",
        description="Genera un grafico de barras agrupadas desde categorias, subgrupos y matriz de valores.",
        category=EXECUTE,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta donde se guardara el grafico, por ejemplo salida.png.",
                required=True,
            ),
            ToolParameter(
                name="data",
                type="object",
                description=(
                    "Objeto con categorias, subgrupos y matriz. "
                    "Ejemplo: {'categorias':['Ing'], 'subgrupos':['Aprobados'], 'matriz':[[10]]}."
                ),
                required=True,
            ),
            ToolParameter(
                name="titulo",
                type="string",
                description="Titulo para el grafico.",
                required=True,
            )
        ],
    ),
    guardar_grafico_estadistico
)
