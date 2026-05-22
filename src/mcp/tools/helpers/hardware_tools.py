from __future__ import annotations

import base64
import json
import os
import socket
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..models import ToolDefinition, ToolParameter
from ..registry import ToolRegistry
from ..categories import HARDWARE, MEDIA_INPUT


DEFAULT_VISION_PROMPT = (
    "Describe la imagen de forma concreta. Incluye objetos visibles, texto legible, "
    "estado relevante y cualquier detalle util para tomar una decision."
)

_VISION_MODEL_DEFAULT: str | None = None
_VISION_BASE_URL_DEFAULT: str | None = None
_VISION_MODEL_AUTO_CACHE: dict[str, str] = {}

AUTO_VISION_MODEL_VALUES = {"auto", "discover", "discovery", "detectar"}
VISION_MODEL_KEYWORDS = (
    "llava",
    "bakllava",
    "moondream",
    "minicpm-v",
    "qwen-vl",
    "qwen2-vl",
    "qwen2.5-vl",
    "vision",
    "-vl",
    "gemma3",
    "gemma-3",
    "gemma4",
    "gemma-4",
    "gemm4",
)


def configure_media_tools(config: Any) -> None:
    global _VISION_MODEL_DEFAULT, _VISION_BASE_URL_DEFAULT

    _VISION_MODEL_DEFAULT = _clean_optional(getattr(config, "vision_model", None))
    _VISION_BASE_URL_DEFAULT = _clean_optional(getattr(config, "vision_ollama_base_url", None))


def _import_serial():
    try:
        import serial
        from serial.tools import list_ports
    except ImportError as exc:
        raise RuntimeError(
            "pyserial no esta instalado. Instala las dependencias con "
            "`pip install -r requirements.txt`."
        ) from exc

    return serial, list_ports


def _import_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "opencv-python no esta instalado. Instala las dependencias con "
            "`pip install -r requirements.txt`."
        ) from exc

    return cv2


def serial_list_ports() -> list[dict[str, Any]]:
    _, list_ports = _import_serial()
    ports = []
    for port in list_ports.comports():
        ports.append(
            {
                "device": port.device,
                "name": getattr(port, "name", None),
                "description": getattr(port, "description", None),
                "hwid": getattr(port, "hwid", None),
                "manufacturer": getattr(port, "manufacturer", None),
                "serial_number": getattr(port, "serial_number", None),
                "vid": getattr(port, "vid", None),
                "pid": getattr(port, "pid", None),
            }
        )
    return ports


def serial_send(
    port: str,
    data: str,
    baudrate: int = 9600,
    timeout: float = 2.0,
    encoding: str = "utf-8",
    read_response: bool = True,
    data_format: str = "text",
    append_newline: bool = False,
    bytesize: int = 8,
    parity: str = "N",
    stopbits: float = 1.0,
) -> dict[str, Any]:
    serial, _ = _import_serial()
    payload = _encode_serial_payload(data, data_format, encoding)
    if append_newline:
        payload += b"\n"

    normalized_parity = _normalize_parity(serial, parity)
    with serial.Serial(
        port=port,
        baudrate=int(baudrate),
        timeout=float(timeout),
        write_timeout=float(timeout),
        bytesize=int(bytesize),
        parity=normalized_parity,
        stopbits=float(stopbits),
    ) as connection:
        written = connection.write(payload)
        connection.flush()
        response = (
            _read_serial_response(connection, float(timeout))
            if read_response
            else b""
        )

    return {
        "port": port,
        "baudrate": int(baudrate),
        "written_bytes": int(written),
        "response_bytes": len(response),
        "response_text": response.decode(encoding, errors="replace") if response else "",
        "response_base64": base64.b64encode(response).decode("ascii") if response else "",
    }


def _encode_serial_payload(data: str, data_format: str, encoding: str) -> bytes:
    normalized = data_format.strip().lower()
    if normalized == "text":
        return data.encode(encoding)

    if normalized == "hex":
        compact = "".join(data.split())
        return bytes.fromhex(compact)

    if normalized == "base64":
        return base64.b64decode(data)

    raise ValueError("data_format debe ser text, hex o base64.")


def _normalize_parity(serial_module, parity: str) -> str:
    normalized = parity.strip().upper()
    allowed = {
        "N": serial_module.PARITY_NONE,
        "E": serial_module.PARITY_EVEN,
        "O": serial_module.PARITY_ODD,
        "M": serial_module.PARITY_MARK,
        "S": serial_module.PARITY_SPACE,
    }
    if normalized not in allowed:
        raise ValueError("parity debe ser N, E, O, M o S.")

    return allowed[normalized]


def _read_serial_response(connection, timeout: float) -> bytes:
    deadline = time.monotonic() + max(timeout, 0.0)
    chunks: list[bytes] = []

    while time.monotonic() <= deadline:
        waiting = int(getattr(connection, "in_waiting", 0) or 0)
        if waiting > 0:
            chunks.append(connection.read(waiting))
            continue

        time.sleep(0.02)

    return b"".join(chunks)


def image_describe(
    source: str,
    source_type: str = "auto",
    prompt: str = DEFAULT_VISION_PROMPT,
    frame_index: int = 0,
    timeout: float = 30.0,
    model: str | None = None,
    ollama_base_url: str | None = None,
    save_frame_path: str | None = None,
) -> dict[str, Any]:
    cv2 = _import_cv2()
    resolved_source_type = _resolve_image_source_type(source, source_type)
    frame = _load_frame(
        cv2,
        source=source,
        source_type=resolved_source_type,
        frame_index=int(frame_index),
        timeout=float(timeout),
    )

    height, width = frame.shape[:2]
    saved_frame_path = None
    if save_frame_path:
        saved_frame_path = str(Path(save_frame_path))
        if not cv2.imwrite(saved_frame_path, frame):
            raise RuntimeError(f"No se pudo guardar el frame en {saved_frame_path}.")

    image_base64 = _encode_frame_as_jpeg_base64(cv2, frame)
    base_url = _vision_base_url(ollama_base_url)
    model_name = _vision_model(model, base_url=base_url, timeout=float(timeout))
    description = _describe_with_ollama(
        image_base64=image_base64,
        prompt=prompt or DEFAULT_VISION_PROMPT,
        model=model_name,
        base_url=base_url,
        timeout=float(timeout),
    )

    return {
        "source_type": resolved_source_type,
        "width": int(width),
        "height": int(height),
        "channels": int(frame.shape[2]) if len(frame.shape) > 2 else 1,
        "saved_frame_path": saved_frame_path,
        "model": model_name,
        "ollama_base_url": base_url,
        "description": description,
    }


def _resolve_image_source_type(source: str, source_type: str) -> str:
    normalized = (source_type or "auto").strip().lower()
    if normalized in {"file", "camera", "rtsp"}:
        return normalized

    if normalized != "auto":
        raise ValueError("source_type debe ser auto, file, camera o rtsp.")

    stripped = source.strip()
    if stripped.isdigit():
        return "camera"

    if stripped.lower().startswith(("rtsp://", "rtsps://", "http://", "https://")):
        return "rtsp"

    return "file"


def _load_frame(
    cv2,
    *,
    source: str,
    source_type: str,
    frame_index: int,
    timeout: float,
):
    if source_type == "file":
        frame = cv2.imread(source)
        if frame is None:
            raise FileNotFoundError(f"No se pudo leer la imagen: {source}")
        return frame

    capture_source: int | str = int(source) if source_type == "camera" else source
    capture = cv2.VideoCapture(capture_source)
    try:
        if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
            capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(max(timeout, 0) * 1000))
        if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
            capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(max(timeout, 0) * 1000))

        if not capture.isOpened():
            raise RuntimeError(f"No se pudo abrir la fuente de imagen: {source}")

        deadline = time.monotonic() + max(timeout, 0.0)
        current_index = 0
        last_error = "No se recibio ningun frame valido."
        while time.monotonic() <= deadline:
            ok, frame = capture.read()
            if not ok or frame is None:
                last_error = "La fuente no entrego frames validos."
                time.sleep(0.03)
                continue

            if current_index >= max(frame_index, 0):
                return frame
            current_index += 1

        raise TimeoutError(f"Timeout leyendo la fuente de imagen. {last_error}")
    finally:
        capture.release()


def _encode_frame_as_jpeg_base64(cv2, frame) -> str:
    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("No se pudo codificar el frame como JPEG.")

    return base64.b64encode(encoded.tobytes()).decode("ascii")


def _vision_model(
    model: str | None,
    *,
    base_url: str,
    timeout: float,
) -> str:
    configured = (
        _clean_optional(model)
        or _VISION_MODEL_DEFAULT
        or os.getenv("MCP_VISION_MODEL")
        or os.getenv("OLLAMA_VISION_MODEL")
    )
    if configured and configured.strip().lower() not in AUTO_VISION_MODEL_VALUES:
        return configured

    return _auto_vision_model(base_url=base_url, timeout=min(max(timeout, 1.0), 5.0))


def _vision_base_url(raw_value: str | None) -> str:
    candidate = (
        _clean_optional(raw_value)
        or _VISION_BASE_URL_DEFAULT
        or os.getenv("MCP_VISION_OLLAMA_BASE_URL")
        or os.getenv("OLLAMA_BASE_URL")
        or "http://127.0.0.1:11434"
    ).rstrip("/")
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"URL invalida para Ollama: {candidate}")
    return candidate


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _chat_url(base_url: str) -> str:
    if base_url.endswith("/api"):
        return f"{base_url}/chat"
    return f"{base_url}/api/chat"


def _tags_url(base_url: str) -> str:
    if base_url.endswith("/api"):
        return f"{base_url}/tags"
    return f"{base_url}/api/tags"


def _auto_vision_model(*, base_url: str, timeout: float) -> str:
    cached = _VISION_MODEL_AUTO_CACHE.get(base_url)
    if cached:
        return cached

    models = _list_ollama_models(base_url=base_url, timeout=timeout)
    selected = _best_vision_model(models)
    if selected is None:
        available = ", ".join(models[:12]) or "(sin modelos)"
        suffix = "" if len(models) <= 12 else f", +{len(models) - 12} mas"
        raise RuntimeError(
            "No se pudo detectar automaticamente un modelo de vision en Ollama. "
            f"Modelos disponibles: {available}{suffix}. "
            "Configura --vision-model <modelo> o MCP_VISION_MODEL con un modelo capaz de analizar imagenes."
        )

    _VISION_MODEL_AUTO_CACHE[base_url] = selected
    return selected


def _list_ollama_models(*, base_url: str, timeout: float) -> list[str]:
    request = Request(
        url=_tags_url(base_url),
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(
            f"No se pudo consultar modelos de Ollama para vision: HTTP {exc.code}."
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError(
            f"No se pudo consultar modelos de Ollama para vision: timeout en {timeout:.0f} segundos."
        ) from exc
    except URLError as exc:
        raise RuntimeError(
            f"No se pudo consultar modelos de Ollama para vision: {exc.reason}."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "No se pudo consultar modelos de Ollama para vision: respuesta JSON invalida."
        ) from exc

    raw_models = payload.get("models", [])
    models: list[str] = []
    if isinstance(raw_models, list):
        for item in raw_models:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("model")
            if isinstance(name, str) and name.strip():
                models.append(name.strip())
    return models


def _best_vision_model(models: list[str]) -> str | None:
    if not models:
        return None

    scored = [
        (model, _vision_model_score(model))
        for model in models
    ]
    candidates = [(model, score) for model, score in scored if score > 0]
    if candidates:
        candidates.sort(key=lambda item: (-item[1], item[0].lower()))
        return candidates[0][0]

    if len(models) == 1:
        return models[0]

    return None


def _vision_model_score(model: str) -> int:
    lowered = model.lower()
    score = 0
    for index, keyword in enumerate(VISION_MODEL_KEYWORDS):
        if keyword in lowered:
            score = max(score, 100 - index)
    if "embed" in lowered or "embedding" in lowered:
        score -= 200
    return score


def _describe_with_ollama(
    *,
    image_base64: str,
    prompt: str,
    model: str,
    base_url: str,
    timeout: float,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_base64],
            }
        ],
        "stream": False,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url=_chat_url(base_url),
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama respondio {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"No se pudo conectar a Ollama: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"Ollama no respondio en {timeout:.0f} segundos.") from exc

    message = result.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]

    if isinstance(result.get("response"), str):
        return result["response"]

    raise RuntimeError("Ollama no devolvio una descripcion de imagen reconocible.")


registry = ToolRegistry()

registry.register(
    ToolDefinition(
        name="serial_list_ports",
        description=(
            "Lista puertos seriales disponibles, incluyendo adaptadores USB serial "
            "y Bluetooth SPP cuando el sistema los expone como puertos COM/TTY."
        ),
        category=HARDWARE,
        parameters=[],
    ),
    serial_list_ports,
)

registry.register(
    ToolDefinition(
        name="serial_send",
        description=(
            "Envia datos por un puerto serial cableado o Bluetooth serial, "
            "opcionalmente leyendo la respuesta hasta timeout."
        ),
        category=HARDWARE,
        parameters=[
            ToolParameter(name="port", type="string", description="Puerto serial, por ejemplo COM3 o /dev/ttyUSB0."),
            ToolParameter(name="data", type="string", description="Datos a enviar."),
            ToolParameter(name="baudrate", type="integer", description="Velocidad en baudios.", required=False),
            ToolParameter(name="timeout", type="number", description="Timeout de lectura/escritura en segundos.", required=False),
            ToolParameter(name="encoding", type="string", description="Encoding usado para data_format=text y respuesta.", required=False),
            ToolParameter(name="read_response", type="boolean", description="Si debe leer respuesta despues de escribir.", required=False),
            ToolParameter(name="data_format", type="string", description="Formato de data: text, hex o base64.", required=False),
            ToolParameter(name="append_newline", type="boolean", description="Agrega salto de linea al final antes de enviar.", required=False),
            ToolParameter(name="bytesize", type="integer", description="Bits de datos, normalmente 8.", required=False),
            ToolParameter(name="parity", type="string", description="Paridad: N, E, O, M o S.", required=False),
            ToolParameter(name="stopbits", type="number", description="Bits de parada, normalmente 1.", required=False),
        ],
    ),
    serial_send,
)

registry.register(
    ToolDefinition(
        name="image_describe",
        description=(
            "Describe una imagen desde archivo, camara web o fuente RTSP/HTTP "
            "capturando un frame y enviandolo a un modelo de vision en Ollama."
        ),
        category=MEDIA_INPUT,
        parameters=[
            ToolParameter(name="source", type="string", description="Ruta de imagen, indice de camara como 0, o URL RTSP/HTTP."),
            ToolParameter(name="source_type", type="string", description="auto, file, camera o rtsp.", required=False),
            ToolParameter(name="prompt", type="string", description="Instruccion para el modelo de vision.", required=False),
            ToolParameter(name="frame_index", type="integer", description="Frame a tomar en camara/stream, desde 0.", required=False),
            ToolParameter(name="timeout", type="number", description="Timeout para captura y llamada a Ollama.", required=False),
            ToolParameter(name="model", type="string", description="Modelo de vision de Ollama.", required=False),
            ToolParameter(name="ollama_base_url", type="string", description="URL base de Ollama.", required=False),
            ToolParameter(name="save_frame_path", type="string", description="Ruta opcional dentro de BASE_DIR para guardar el frame.", required=False),
        ],
    ),
    image_describe,
)
