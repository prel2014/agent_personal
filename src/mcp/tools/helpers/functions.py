import hashlib
import json
import os
import shutil
from pathlib import Path

from .read_policy import is_read_protected


WRITE_PREVIEW_LIMIT = 240


def writefile(path: str, content: str, modo: str = "w") -> dict[str, object]:
    mode = (modo or "w").strip()
    if mode == "x" and Path(path).exists():
        raise FileExistsError(
            "El archivo ya existe. Si el usuario pidio exactamente esta ruta y "
            "quieres reemplazar su contenido, vuelve a llamar writefile con modo='w'. "
            "Si no debes sobrescribir, usa un nombre alternativo o pide confirmacion."
        )

    with open(path, mode=mode, encoding="utf-8") as file:
        file.write(content)

    return _write_result(path, content, mode=mode, operation="writefile")


def readfile(path: str) -> str:
    try:
        with open(path, mode="r", encoding="utf-8") as file:
            return file.read()
    except UnicodeDecodeError as exc:
        suffix = Path(path).suffix.lower()
        if suffix in {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}:
            raise ValueError(
                "El archivo es una imagen/binario; usa image_describe para leer "
                "contenido visual en lugar de readfile."
            ) from exc
        raise


def appendfile(path: str, content: str) -> dict[str, object]:
    with open(path, mode="a", encoding="utf-8") as file:
        file.write(content)

    return _write_result(path, content, mode="a", operation="appendfile")


def listdir(path: str = ".") -> str:
    root = Path(path)
    items = [
        child.name
        for child in root.iterdir()
        if not is_read_protected(child, base_dir=root)
    ]
    return json.dumps(items, ensure_ascii=False, indent=2)


def mkdir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return "ok"


def deletefile(path: str) -> str:
    os.remove(path)
    return "ok"


def deletedir(path: str, recursive: bool = True) -> dict[str, object]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"La carpeta no existe: {path}")
    if not target.is_dir():
        raise NotADirectoryError(f"La ruta no es una carpeta: {path}")

    if recursive:
        removed_files = sum(1 for child in target.rglob("*") if child.is_file())
        removed_dirs = sum(1 for child in target.rglob("*") if child.is_dir()) + 1
        shutil.rmtree(target)
    else:
        removed_files = 0
        removed_dirs = 1
        target.rmdir()

    return {
        "success": True,
        "operation": "deletedir",
        "path": str(target),
        "recursive": bool(recursive),
        "removed_files": removed_files,
        "removed_dirs": removed_dirs,
    }


def movefile(path: str, target_path: str, overwrite: bool = False) -> dict[str, object]:
    source = Path(path)
    target = Path(target_path)
    if not source.exists():
        raise FileNotFoundError(f"La ruta origen no existe: {path}")
    if target.exists() and not overwrite:
        raise FileExistsError(f"La ruta destino ya existe: {target_path}")

    target.parent.mkdir(parents=True, exist_ok=True)
    bytes_moved = source.stat().st_size if source.is_file() else None
    shutil.move(str(source), str(target))
    return {
        "success": True,
        "operation": "movefile",
        "path": str(source),
        "target_path": str(target),
        "overwrite": bool(overwrite),
        "bytes_moved": bytes_moved,
    }


def exists(path: str) -> str:
    return "true" if os.path.exists(path) else "false"


def fileinfo(path: str) -> str:
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"El archivo o carpeta no existe: {path}")

    info = {
        "path": str(p),
        "name": p.name,
        "is_file": p.is_file(),
        "is_dir": p.is_dir(),
        "size_bytes": p.stat().st_size,
        "absolute_path": str(p.resolve())
    }

    return json.dumps(info, ensure_ascii=False, indent=2)


def _write_result(
    path: str,
    written_content: str,
    *,
    mode: str,
    operation: str,
) -> dict[str, object]:
    content = Path(path).read_text(encoding="utf-8")
    encoded = content.encode("utf-8")
    preview = content[:WRITE_PREVIEW_LIMIT]
    if len(content) > WRITE_PREVIEW_LIMIT:
        preview += "..."
    written_bytes = written_content.encode("utf-8")

    return {
        "success": True,
        "operation": operation,
        "path": str(Path(path)),
        "mode": mode,
        "characters_written": len(written_content),
        "final_characters": len(content),
        "written_bytes": len(written_bytes),
        "bytes_written": len(encoded),
        "content_preview": preview,
        "content_sha256": hashlib.sha256(encoded).hexdigest(),
    }
