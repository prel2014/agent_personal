# Uso Del Orquestador Ollama Distribuido

## Objetivo

El proyecto permite usar varias maquinas con Ollama como nodos de razonamiento
para un cliente local. No reparte una sola inferencia entre varias GPUs/RAM; lo
que distribuye es el trabajo por rol o por seleccion de nodo.

Responsabilidades:

- El cliente CLI/REPL vive en la maquina coordinadora y ejecuta las tools.
- `mcp_server` enruta mensajes HTTP hacia Ollama local o remoto.
- Cada nodo remoto expone Ollama por HTTP en la LAN.
- El routing puede usar roles `planner`, `worker`, `reviewer` u otros roles
  configurados.

## Arquitectura

Flujo normal con equipo agentico:

1. El cliente envia el prompt al `mcp_server`.
2. El `planner` genera un plan sin tools.
3. El `worker` inspecciona o modifica el workspace con tools locales.
4. El `reviewer` valida con lectura.
5. Si el reviewer pide cambios, el worker recibe feedback y corrige.

El razonamiento puede correr en nodos Ollama distintos. Las operaciones de
archivos, ejecucion, Git, KV, hardware y web siguen ocurriendo en la maquina
cliente y pasan por `src/mcp`.

## Requisitos

- Python 3.10+ en la maquina coordinadora.
- Ollama instalado y con modelos descargados en cada nodo.
- Conectividad HTTP desde la coordinadora hacia cada `http://IP:11434`.
- Firewall abierto para el puerto de Ollama cuando se use LAN.
- Autenticacion Bearer si `mcp_server` se expone fuera de loopback.

Verificacion por nodo:

```powershell
Invoke-RestMethod http://IP_DEL_NODO:11434/api/tags
```

## Configuracion Manual De Nodos

Ejemplo base: `examples/ollama_nodes.example.json`.

```json
{
  "nodes": [
    {
      "id": "planner-remote",
      "base_url": "http://192.168.1.20:11434",
      "model": "qwen2.5:7b-instruct-q4_K_M",
      "roles": ["planner"],
      "priority": 10,
      "enabled": true
    },
    {
      "id": "worker-remote",
      "base_url": "http://192.168.1.21:11434",
      "model": "deepseek-coder:6.7b-instruct-q4_K_M",
      "roles": ["worker"],
      "priority": 10,
      "enabled": true
    }
  ]
}
```

Campos:

- `id`: nombre logico del nodo.
- `base_url`: URL base de Ollama remoto.
- `model`: modelo usado en ese nodo.
- `roles`: roles atendidos por el nodo.
- `priority`: menor numero gana preferencia.
- `enabled`: opcional, por defecto `true`.
- `keep_alive`: opcional, se envia a Ollama.
- `think`: opcional, acepta `true`, `false`, `low`, `medium` o `high`.

## Arranque Del Servidor

Local:

```powershell
python -m src.mcp_server.server.cli `
  --host 127.0.0.1 `
  --port 8000 `
  --ollama-base-url http://127.0.0.1:11434 `
  --model auto
```

LAN con auth y nodos manuales:

```powershell
python -m src.mcp_server.server.cli `
  --host 0.0.0.0 `
  --port 8000 `
  --auth-mode bearer_static `
  --auth-static-tokens supersecreto `
  --ollama-base-url http://127.0.0.1:11434 `
  --model auto `
  --nodes-config examples/ollama_nodes.example.json
```

Si `--model auto`, el servidor intenta seleccionar un modelo local desde
`/api/tags`. Si no puede, usa un fallback de configuracion.

Para desactivar fallback local cuando falla un remoto:

```powershell
python -m src.mcp_server.server.cli `
  --nodes-config examples/ollama_nodes.example.json `
  --no-local-fallback
```

## Descubrimiento LAN

Discovery consulta `/api/tags` en hosts o CIDRs y reporta disponibilidad,
modelos y errores. Respeta TTL, timeout y limite de hosts.

Hosts concretos:

```powershell
python -m src.mcp_server.server.cli `
  --nodes-config examples/ollama_nodes.example.json `
  --discover-nodes `
  --discovery-hosts 192.168.1.20,192.168.1.21 `
  --discovery-timeout 1.0 `
  --discovery-ttl-seconds 30
```

CIDR:

```powershell
python -m src.mcp_server.server.cli `
  --discover-nodes `
  --discovery-cidrs 192.168.1.0/24 `
  --discovery-port 11434 `
  --discovery-max-hosts 64
```

Si `--discover-nodes` no recibe hosts ni CIDRs, por defecto intenta inferir la
LAN local. Puedes desactivar eso con `--no-discovery-auto-lan`.

## Auto-Promocion De Nodos Descubiertos

Por defecto, discovery observa nodos pero no los usa para routing si no estan en
`nodes-config`. Para convertir nodos descubiertos en candidatos de routing:

```powershell
python -m src.mcp_server.server.cli `
  --discover-nodes `
  --auto-promote-discovered-nodes `
  --auto-promote-roles planner,worker,reviewer `
  --auto-promote-priority 200 `
  --auto-promote-max-nodes 16
```

La auto-promocion:

- ignora nodos ya configurados manualmente
- requiere que el host sea reachable y exponga modelos
- descarta modelos de embeddings para roles de razonamiento
- puntua modelos de codigo para `worker`
- puntua modelos generales/razonamiento para `planner` y `reviewer`
- crea nodos con `source=auto_promoted`

## Cliente

Consultar nodos:

```powershell
python -m src.mcp_client.commands.cli `
  --server-url http://127.0.0.1:8000 `
  --server-bearer-token supersecreto `
  list-nodes
```

Health e info:

```powershell
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 health
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 info
```

Ejecutar trabajo:

```powershell
python -m src.mcp_client.commands.cli `
  --server-url http://127.0.0.1:8000 `
  --server-bearer-token supersecreto `
  ask "haz este cambio en el proyecto"
```

REPL:

```powershell
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 repl
```

## Seleccion De Nodos

El registry resuelve en este orden:

1. `agent_node_id` explicito en el contexto, si existe y esta disponible.
2. `agent_role`, buscando nodos no locales que atiendan ese rol.
3. nodo local por defecto.

Entre candidatos del mismo rol:

- se filtran nodos deshabilitados o no reachable cuando discovery esta activo
- se ordena por `priority` y `node_id`
- se aplica round-robin por rol entre candidatos equivalentes

Si falla la peticion a un remoto durante el inicio y el fallback esta activo,
el servidor vuelve al nodo local.

## Variables De Entorno

Servidor:

- `MCP_API_HOST`
- `MCP_API_PORT`
- `MCP_SERVER_AUTH_MODE`
- `MCP_SERVER_AUTH_TOKENS`
- `MCP_SERVER_NODES_CONFIG`
- `MCP_SERVER_ALLOW_LOCAL_FALLBACK`
- `MCP_SERVER_DISCOVERY_ENABLED`
- `MCP_SERVER_DISCOVERY_HOSTS`
- `MCP_SERVER_DISCOVERY_CIDRS`
- `MCP_SERVER_DISCOVERY_PORT`
- `MCP_SERVER_DISCOVERY_TIMEOUT`
- `MCP_SERVER_DISCOVERY_TTL_SECONDS`
- `MCP_SERVER_DISCOVERY_MAX_HOSTS`
- `MCP_SERVER_AUTO_PROMOTE_DISCOVERED_NODES`
- `MCP_SERVER_AUTO_PROMOTE_ROLES`
- `MCP_SERVER_AUTO_PROMOTE_PRIORITY`
- `MCP_SERVER_AUTO_PROMOTE_MAX_NODES`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_KEEP_ALIVE`
- `OLLAMA_REQUEST_TIMEOUT`

Cliente:

- `MCP_SERVER_URL`
- `MCP_SERVER_BEARER_TOKEN`
- `MCP_CLIENT_PLANNING_MODE`
- `MCP_CLIENT_MAX_STEPS`
- `MCP_CLIENT_OUTPUT_MODE`
- `MCP_CLIENT_SHOW_THINKING`

## Diagnostico

Si un nodo no aparece:

1. Abre `http://IP:11434/api/tags` desde la coordinadora.
2. Revisa firewall, puerto y conectividad LAN.
3. Usa `list-nodes` para ver `reachable`, `available_models` y `last_error`.
4. Baja `--discovery-timeout` solo si la red responde rapido; subelo en redes
   lentas.

Si aparece detectado pero no se usa:

1. Verifica que este en `nodes-config` o activa auto-promocion.
2. Confirma `roles`, `model`, `enabled` y `priority`.
3. Confirma que el modelo existe en ese nodo.
4. Revisa si discovery lo marco como no reachable.

## Notas De Seguridad

- Exponer `mcp_server` fuera de loopback requiere auth; el arranque falla si
  usas `--host 0.0.0.0 --auth-mode off`.
- `/v1/chat` exige Bearer token cuando `auth_mode=bearer_static`.
- `/info` y `/nodes` tambien quedan protegidos salvo `--no-auth-for-info`.
- `/health` es publico por defecto; usa `--private-health` para protegerlo.
- Las tools y el filesystem no salen del cliente. El servidor no debe recibir
  secretos salvo que el contexto enviado por el cliente los incluya.
