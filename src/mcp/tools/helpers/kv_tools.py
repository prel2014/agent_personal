from .kv_functions import *
from ..models import ToolDefinition, ToolParameter
from ..registry import ToolRegistry
from ..categories import READ, WRITE


registry = ToolRegistry()


registry.register(
    ToolDefinition(
        name="kv_get",
        description="Lee una entrada del KV cache local por namespace y key.",
        category=READ,
        parameters=[
            ToolParameter(name="namespace", type="string", description="Namespace del cache."),
            ToolParameter(name="key", type="string", description="Clave a leer."),
        ],
    ),
    kv_get,
)

registry.register(
    ToolDefinition(
        name="kv_list",
        description="Lista entradas del KV cache local, opcionalmente por namespace y prefijo.",
        category=READ,
        parameters=[
            ToolParameter(name="namespace", type="string", description="Namespace opcional.", required=False),
            ToolParameter(name="prefix", type="string", description="Prefijo opcional de key.", required=False),
            ToolParameter(name="limit", type="integer", description="Cantidad maxima de entradas.", required=False),
        ],
    ),
    kv_list,
)

registry.register(
    ToolDefinition(
        name="kv_set",
        description="Escribe una entrada en el KV cache local con TTL opcional.",
        category=WRITE,
        parameters=[
            ToolParameter(name="namespace", type="string", description="Namespace del cache."),
            ToolParameter(name="key", type="string", description="Clave a escribir."),
            ToolParameter(name="value", type="object", description="Valor JSON a guardar."),
            ToolParameter(name="ttl_seconds", type="integer", description="TTL opcional en segundos.", required=False),
            ToolParameter(name="metadata", type="object", description="Metadata JSON opcional.", required=False),
        ],
    ),
    kv_set,
)

registry.register(
    ToolDefinition(
        name="kv_delete",
        description="Borra una entrada del KV cache local.",
        category=WRITE,
        parameters=[
            ToolParameter(name="namespace", type="string", description="Namespace del cache."),
            ToolParameter(name="key", type="string", description="Clave a borrar."),
        ],
    ),
    kv_delete,
)

registry.register(
    ToolDefinition(
        name="kv_clear_expired",
        description="Borra entradas expiradas del KV cache local.",
        category=WRITE,
        parameters=[
            ToolParameter(name="namespace", type="string", description="Namespace opcional.", required=False),
        ],
    ),
    kv_clear_expired,
)
