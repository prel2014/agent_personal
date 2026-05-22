# Uso Del Orquestador Ollama Distribuido

## Objetivo

Este proyecto permite usar varias maquinas con Ollama instalado como un equipo distribuido de agentes.

La idea es:

- El cliente CLI y las tools locales viven en tu maquina principal.
- El `mcp_server` actua como orquestador central.
- Cada nodo remoto expone Ollama por HTTP en su red local.
- El orquestador decide que nodo usa cada rol: `planner`, `worker`, `reviewer`.

No se reparte la RAM de varias PCs para un solo modelo. Lo que se distribuye es el trabajo entre varios nodos.

## Arquitectura

Flujo normal:

1. El cliente envia el prompt al `mcp_server`.
2. El `planner` razona el plan.
3. El `worker` ejecuta el cambio usando las tools locales del cliente.
4. El `reviewer` valida el resultado.
5. Si el reviewer detecta problemas, el worker recibe feedback y corrige.

El razonamiento puede correr en distintos nodos Ollama, pero las tools de archivos y ejecucion siguen ocurriendo en la maquina cliente.

## Requisitos

- Python instalado en la maquina coordinadora.
- Ollama instalado en cada nodo remoto.
- Cada nodo remoto debe ser accesible por HTTP desde la maquina coordinadora.
- Los modelos necesarios deben estar descargados en cada nodo.
- El puerto de Ollama debe estar abierto en la LAN.

## Preparar Cada Nodo Remoto

En cada maquina remota:

1. Instala Ollama.
2. Descarga el modelo que vas a asignar a ese nodo.
3. Asegurate de que Ollama responda por red local.
4. Verifica desde la maquina coordinadora que puedes abrir `http://IP_DEL_NODO:11434/api/tags`.

El endpoint `/api/tags` debe devolver la lista de modelos disponibles en ese nodo.

## Configuracion Manual De Nodos

Puedes definir los nodos en un JSON y decidir explicitamente que modelo usa cada uno.

Ejemplo base: `examples/ollama_nodes.example.json`.

Ejemplo:

```json
{
  "nodes": [
    {
      "id": "planner-remote",
      "base_url": "http://192.168.1.20:11434",
      "model": "qwen2.5:7b-instruct-q4_K_M",
      "roles": ["planner"],
      "priority": 10
    },
    {
      "id": "worker-remote",
      "base_url": "http://192.168.1.21:11434",
      "model": "deepseek-coder:6.7b-instruct-q4_K_M",
      "roles": ["worker"],
      "priority": 10
    },
    {
      "id": "reviewer-remote",
      "base_url": "http://192.168.1.22:11434",
      "model": "llama3.1:8b-instruct-q4_K_M",
      "roles": ["reviewer"],
      "priority": 10
    }
  ]
}
```

Campos importantes:

- `id`: nombre logico del nodo.
- `base_url`: URL base de Ollama remoto.
- `model`: modelo que usara ese nodo.
- `roles`: roles que puede atender.
- `priority`: prioridad de seleccion. Menor numero = mayor preferencia.
- `enabled`: opcional, por defecto `true`.
- `keep_alive`: opcional.
- `think`: opcional.

## Arrancar El Orquestador

Ejemplo minimo con nodos manuales:

```powershell
python -m src.mcp_server.server.cli `
  --host 0.0.0.0 `
  --port 8000 `
  --ollama-base-url http://127.0.0.1:11434 `
  --model qwen3 `
  --nodes-config examples/ollama_nodes.example.json
```

Notas:

- El nodo local sigue existiendo como fallback.
- Si un nodo remoto falla y el fallback local esta habilitado, el orquestador puede volver a tu Ollama local.

Si quieres desactivar el fallback local:

```powershell
python -m src.mcp_server.server.cli `
  --host 0.0.0.0 `
  --port 8000 `
  --nodes-config examples/ollama_nodes.example.json `
  --no-local-fallback
```

## Descubrimiento Automatico De Nodos

El servidor puede sondear hosts concretos o rangos CIDR para detectar instancias Ollama disponibles en red.

Que hace el descubrimiento:

- Consulta `GET /api/tags` en cada host candidato.
- Marca si el host esta `reachable`.
- Reporta `available_models`.
- Evita enrutar trabajo a nodos configurados que aparecen caidos.

Importante:

- Un nodo descubierto automaticamente no se usa para routing por rol si no esta configurado en el JSON.
- El descubrimiento sirve para observabilidad, validacion de red y control de disponibilidad.
- El modelo por rol lo sigues definiendo tu en el archivo JSON.

### Sondeo Por Hosts

```powershell
python -m src.mcp_server.server.cli `
  --host 0.0.0.0 `
  --port 8000 `
  --nodes-config examples/ollama_nodes.example.json `
  --discover-nodes `
  --discovery-hosts 192.168.1.20,192.168.1.21,192.168.1.22 `
  --discovery-timeout 1.0 `
  --discovery-ttl-seconds 30
```

Tambien puedes pasar URLs completas:

```powershell
python -m src.mcp_server.server.cli `
  --nodes-config examples/ollama_nodes.example.json `
  --discover-nodes `
  --discovery-hosts http://192.168.1.20:11434,http://192.168.1.21:11434
```

### Sondeo Por Rango CIDR

```powershell
python -m src.mcp_server.server.cli `
  --nodes-config examples/ollama_nodes.example.json `
  --discover-nodes `
  --discovery-cidrs 192.168.1.0/24 `
  --discovery-port 11434 `
  --discovery-max-hosts 64 `
  --discovery-timeout 1.0
```

Flags relevantes:

- `--discover-nodes`
- `--discovery-hosts`
- `--discovery-cidrs`
- `--discovery-port`
- `--discovery-timeout`
- `--discovery-ttl-seconds`
- `--discovery-max-hosts`

## Consultar Los Nodos Desde El Cliente

Una vez levantado el servidor:

```powershell
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 list-nodes
```

Tambien puedes revisar:

```powershell
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 health
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 info
```

`list-nodes` te mostrara:

- nodos configurados
- nodos detectados
- si responden
- que modelos exponen
- si son `managed` o `unmanaged`

## Ejecutar Trabajo Con El Cliente

Consulta directa:

```powershell
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 ask "haz este cambio en el proyecto"
```

Sesion interactiva:

```powershell
python -m src.mcp_client.commands.cli --server-url http://127.0.0.1:8000 repl
```

Por defecto el cliente usa el flujo orquestado `planner -> worker -> reviewer`.

En ese flujo:

- `planner` no recibe tools. Su responsabilidad es planear y delegar.
- `worker` ejecuta tools dentro del sandbox por defecto.
- `reviewer` valida con lectura.

El worker solo sale del sandbox si el usuario lo pide explicitamente, por
ejemplo con "fuera del sandbox", "usa el host" o "sin aislamiento".

Si quieres desactivarlo y usar un solo agente:

```powershell
python -m src.mcp_client.commands.cli `
  --server-url http://127.0.0.1:8000 `
  --no-orchestrate-agents `
  ask "haz este cambio"
```

## Seleccion De Nodos Y Roles

El routing actual funciona asi:

- `planner` busca un nodo remoto con rol `planner`.
- `worker` busca un nodo remoto con rol `worker`.
- `reviewer` busca un nodo remoto con rol `reviewer`.
- Si no encuentra uno valido, cae al nodo local.
- Si el nodo remoto falla durante el inicio de la peticion y el fallback esta habilitado, vuelve al nodo local.

Si hay varios nodos para el mismo rol:

- se ordenan por `priority`
- entre nodos equivalentes se usa round-robin

## Recomendacion Practica De Roles

Con varias maquinas pequenas, una distribucion razonable es:

- `planner`: modelo compacto pero bueno para instrucciones.
- `worker`: modelo coder/instruct.
- `reviewer`: modelo estable para validacion y consistencia.

Ejemplo:

- `planner`: Qwen 7B quantizado
- `worker`: DeepSeek Coder 6.7B quantizado
- `reviewer`: Llama 8B instruct quantizado

## Variables De Entorno Utiles

Servidor:

- `MCP_SERVER_NODES_CONFIG`
- `MCP_SERVER_ALLOW_LOCAL_FALLBACK`
- `MCP_SERVER_DISCOVERY_ENABLED`
- `MCP_SERVER_DISCOVERY_HOSTS`
- `MCP_SERVER_DISCOVERY_CIDRS`
- `MCP_SERVER_DISCOVERY_PORT`
- `MCP_SERVER_DISCOVERY_TIMEOUT`
- `MCP_SERVER_DISCOVERY_TTL_SECONDS`
- `MCP_SERVER_DISCOVERY_MAX_HOSTS`

Cliente:

- `MCP_SERVER_URL`
- `MCP_CLIENT_ORCHESTRATE_AGENTS`

## Diagnostico Rapido

Si un nodo no aparece como disponible:

1. Abre `http://IP:11434/api/tags` desde la maquina coordinadora.
2. Verifica firewall y conectividad LAN.
3. Revisa que Ollama este escuchando por red.
4. Usa `list-nodes` para ver `reachable`, `available_models` y `last_error`.

Si aparece detectado pero no se usa:

1. Verifica que el nodo este tambien en `nodes-config`.
2. Revisa que tenga `roles` correctos.
3. Confirma que el `model` exista realmente en ese nodo.
4. Comprueba la `priority`.

## Flujo Recomendado

1. Configura los nodos manuales con modelo y rol.
2. Activa descubrimiento para validar que realmente estan vivos.
3. Arranca el servidor.
4. Ejecuta `list-nodes`.
5. Lanza una prueba con `ask`.
6. Ajusta modelos o prioridades segun resultados.

## Estado Actual

Actualmente el sistema ya soporta:

- orquestacion por roles
- nodos remotos por modelo
- fallback local
- autodeteccion de instancias Ollama
- reporte de nodos disponibles

Lo que no hace automaticamente:

- asignar roles a nodos descubiertos sin configuracion manual
- elegir un modelo remoto sin que tu lo declares
- sincronizar archivos entre maquinas
- repartir una sola inferencia entre varias GPUs o varias RAMs

## Notas De CLI

El render Markdown del REPL requiere salida rich habilitada. Si usas
`--plain-output`, la respuesta se imprime como texto simple.

El campo `thinking` esta apagado por defecto. Puedes alternarlo en el REPL con
`Ctrl+T` o con:

```text
/thinking off
```
