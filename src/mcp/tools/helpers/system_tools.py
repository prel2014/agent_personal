from .functions import *
from ..registry import ToolRegistry
from ..models import ToolDefinition, ToolParameter
from ..categories import DELETE, READ, WRITE

registry = ToolRegistry()

registry.register(
    ToolDefinition(
        name="writefile",
        description="Escribe contenido en un archivo de texto plano",
        category=WRITE,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del archivo donde se escribirá el contenido"
            ),
            ToolParameter(
                name="content",
                type="string",
                description="Contenido que se escribirá en el archivo"
            ),
            ToolParameter(
                name="modo",
                type="string",
                description="Modo de apertura del archivo, por ejemplo w, a o x",
                required=False
            ),
        ]
    ),
    writefile
)


registry.register(
    ToolDefinition(
        name="readfile",
        description="Lee el contenido de un archivo de texto plano",
        category=READ,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del archivo que se desea leer"
            ),
        ]
    ),
    readfile
)


registry.register(
    ToolDefinition(
        name="appendfile",
        description="Agrega contenido al final de un archivo de texto",
        category=WRITE,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del archivo"
            ),
            ToolParameter(
                name="content",
                type="string",
                description="Contenido que se agregará al final del archivo"
            ),
        ]
    ),
    appendfile
)


registry.register(
    ToolDefinition(
        name="listdir",
        description="Lista los archivos y carpetas dentro de una ruta",
        category=READ,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta de la carpeta que se desea listar",
                required=False
            ),
        ]
    ),
    listdir
)


registry.register(
    ToolDefinition(
        name="mkdir",
        description="Crea una carpeta en la ruta indicada",
        category=WRITE,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta de la carpeta que se desea crear"
            ),
        ]
    ),
    mkdir
)


registry.register(
    ToolDefinition(
        name="deletefile",
        description="Elimina un archivo",
        category=DELETE,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del archivo que se desea eliminar"
            ),
        ]
    ),
    deletefile
)


registry.register(
    ToolDefinition(
        name="deletedir",
        description="Elimina una carpeta. Puede borrar su contenido cuando recursive=true.",
        category=DELETE,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta de la carpeta que se desea eliminar"
            ),
            ToolParameter(
                name="recursive",
                type="boolean",
                description="Si debe eliminar tambien todo el contenido de la carpeta",
                required=False
            ),
        ]
    ),
    deletedir
)


registry.register(
    ToolDefinition(
        name="movefile",
        description="Mueve o renombra un archivo o carpeta preservando su contenido original.",
        category=WRITE,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta origen del archivo o carpeta"
            ),
            ToolParameter(
                name="target_path",
                type="string",
                description="Ruta destino con el nuevo nombre o ubicacion"
            ),
            ToolParameter(
                name="overwrite",
                type="boolean",
                description="Si puede sobrescribir el destino cuando ya existe",
                required=False
            ),
        ]
    ),
    movefile
)


registry.register(
    ToolDefinition(
        name="exists",
        description="Verifica si existe un archivo o carpeta",
        category=READ,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta que se desea verificar"
            ),
        ]
    ),
    exists
)


registry.register(
    ToolDefinition(
        name="fileinfo",
        category=READ,
        description="Obtiene información básica de un archivo o carpeta",
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Ruta del archivo o carpeta"
            ),
        ]
    ),
    fileinfo
)
