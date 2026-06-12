from .kv_search_functions import kv_search
from ..models import ToolDefinition, ToolParameter
from ..registry import ToolRegistry
from ..categories import READ


registry = ToolRegistry()

registry.register(
    ToolDefinition(
        name="kv_search",
        description=(
            "Busca entradas del KV cache por similitud semantica (embeddings) "
            "o por texto (BM25 si embeddings no disponibles). "
            "Util para recuperar entradas sin saber la clave exacta."
        ),
        category=READ,
        parameters=[
            ToolParameter(name="query", type="string", description="Texto o pregunta a buscar."),
            ToolParameter(name="namespace", type="string", description="Namespace opcional para acotar la busqueda.", required=False),
            ToolParameter(name="top_k", type="integer", description="Maximo de resultados a retornar (default 5).", required=False),
            ToolParameter(name="min_score", type="number", description="Score minimo de similitud para incluir un resultado (default 0.0).", required=False),
        ],
    ),
    kv_search,
)
