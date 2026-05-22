from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


STATUS_LABELS = {
    " ": "unmodified",
    "M": "modified",
    "A": "added",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "U": "unmerged",
    "?": "untracked",
    "!": "ignored",
}

DEFAULT_DIFF_MAX_BYTES = 50_000
DEFAULT_SHOW_MAX_BYTES = 50_000


def git_status(path: str = ".", include_untracked: bool = True) -> dict[str, Any]:
    repo_root, pathspec = _resolve_repo_target(path)
    command = [
        "status",
        "--short",
        "--branch",
        "--untracked-files=all" if include_untracked else "--untracked-files=no",
    ]
    if pathspec is not None:
        command.extend(["--", pathspec])

    stdout = _run_git(command, cwd=repo_root)
    branch = {
        "head": None,
        "upstream": None,
        "ahead": 0,
        "behind": 0,
        "detached": False,
        "no_commits": False,
    }
    entries: list[dict[str, Any]] = []

    for line in stdout.splitlines():
        if line.startswith("## "):
            branch = _parse_branch_line(line[3:].strip())
            continue

        if not line:
            continue

        index_code = line[0]
        worktree_code = line[1]
        raw_path = line[3:]
        old_path = None
        path_text = raw_path
        if " -> " in raw_path and (index_code in {"R", "C"} or worktree_code in {"R", "C"}):
            old_path, path_text = raw_path.split(" -> ", 1)

        untracked = index_code == "?" and worktree_code == "?"
        ignored = index_code == "!" and worktree_code == "!"
        staged = not untracked and not ignored and index_code != " "
        unstaged = not untracked and not ignored and worktree_code != " "

        entries.append(
            {
                "path": path_text,
                "old_path": old_path,
                "index_code": index_code,
                "index_status": STATUS_LABELS.get(index_code, "unknown"),
                "worktree_code": worktree_code,
                "worktree_status": STATUS_LABELS.get(worktree_code, "unknown"),
                "staged": staged,
                "unstaged": unstaged,
                "untracked": untracked,
                "ignored": ignored,
            }
        )

    return {
        "repo_root": str(repo_root),
        "pathspec": pathspec,
        "branch": branch,
        "entries": entries,
        "clean": all(entry["ignored"] for entry in entries) if entries else True,
        "staged_count": sum(1 for entry in entries if entry["staged"]),
        "unstaged_count": sum(1 for entry in entries if entry["unstaged"]),
        "untracked_count": sum(1 for entry in entries if entry["untracked"]),
    }


def git_diff(
    path: str = ".",
    staged: bool = False,
    base_ref: str | None = None,
    target_ref: str | None = None,
    context_lines: int = 3,
    max_bytes: int = DEFAULT_DIFF_MAX_BYTES,
) -> dict[str, Any]:
    if context_lines < 0:
        raise ValueError("'context_lines' no puede ser negativo.")
    if max_bytes <= 0:
        raise ValueError("'max_bytes' debe ser mayor a 0.")
    if staged and (base_ref is not None or target_ref is not None):
        raise ValueError("'staged' no puede combinarse con 'base_ref' o 'target_ref'.")
    if target_ref is not None and base_ref is None:
        raise ValueError("'target_ref' requiere tambien 'base_ref'.")

    repo_root, pathspec = _resolve_repo_target(path)
    command = [
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        f"--unified={context_lines}",
    ]

    mode = "working_tree"
    if staged:
        command.append("--cached")
        mode = "staged"
    elif base_ref is not None and target_ref is not None:
        command.extend([base_ref, target_ref])
        mode = "refs"
    elif base_ref is not None:
        command.append(base_ref)
        mode = "ref_vs_worktree"

    if pathspec is not None:
        command.extend(["--", pathspec])

    stdout = _run_git(command, cwd=repo_root)
    diff_text, truncated = _truncate_text(stdout, max_bytes=max_bytes)
    return {
        "repo_root": str(repo_root),
        "pathspec": pathspec,
        "mode": mode,
        "staged": staged,
        "base_ref": base_ref,
        "target_ref": target_ref,
        "diff": diff_text,
        "truncated": truncated,
        "max_bytes": max_bytes,
    }


def git_log(
    path: str = ".",
    max_count: int = 10,
    ref: str | None = None,
) -> dict[str, Any]:
    if max_count <= 0:
        raise ValueError("'max_count' debe ser mayor a 0.")

    repo_root, pathspec = _resolve_repo_target(path)
    format_string = "%H%x1f%P%x1f%an%x1f%ae%x1f%aI%x1f%s%x1e"
    command = ["log", f"--max-count={max_count}", f"--format={format_string}"]
    if ref is not None:
        command.append(ref)
    if pathspec is not None:
        command.extend(["--", pathspec])

    stdout = _run_git(command, cwd=repo_root)
    commits: list[dict[str, Any]] = []
    for raw_entry in stdout.split("\x1e"):
        entry = raw_entry.strip()
        if not entry:
            continue

        parts = entry.split("\x1f")
        if len(parts) < 6:
            continue

        commit_hash, parents, author_name, author_email, authored_at, subject = parts[:6]
        commits.append(
            {
                "commit": commit_hash,
                "parents": [value for value in parents.split() if value],
                "author_name": author_name,
                "author_email": author_email,
                "authored_at": authored_at,
                "subject": subject,
            }
        )

    return {
        "repo_root": str(repo_root),
        "pathspec": pathspec,
        "ref": ref,
        "commits": commits,
    }


def git_show(
    revision: str,
    path: str = ".",
    max_bytes: int = DEFAULT_SHOW_MAX_BYTES,
) -> dict[str, Any]:
    if max_bytes <= 0:
        raise ValueError("'max_bytes' debe ser mayor a 0.")

    repo_root, pathspec = _resolve_repo_target(path)
    command = [
        "show",
        "--stat",
        "--format=fuller",
        "--no-ext-diff",
        "--no-textconv",
        revision,
    ]
    if pathspec is not None:
        command.extend(["--", pathspec])

    stdout = _run_git(command, cwd=repo_root)
    text, truncated = _truncate_text(stdout, max_bytes=max_bytes)
    return {
        "repo_root": str(repo_root),
        "pathspec": pathspec,
        "revision": revision,
        "text": text,
        "truncated": truncated,
        "max_bytes": max_bytes,
    }


def git_branches(
    path: str = ".",
    all_branches: bool = False,
    contains: str | None = None,
) -> dict[str, Any]:
    repo_root, _ = _resolve_repo_target(path)
    current_branch = _run_git(["branch", "--show-current"], cwd=repo_root).strip() or None
    format_string = "%(HEAD)\t%(refname:short)\t%(objectname)\t%(upstream:short)\t%(upstream:trackshort)\t%(subject)"
    command = ["branch", "--list", f"--format={format_string}"]
    if all_branches:
        command.append("--all")
    if contains is not None:
        command.extend(["--contains", contains])

    stdout = _run_git(command, cwd=repo_root)
    branches: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue

        parts = line.split("\t", 5)
        while len(parts) < 6:
            parts.append("")

        head_marker, name, commit_hash, upstream, tracking, subject = parts[:6]
        branches.append(
            {
                "name": name.strip(),
                "current": head_marker.strip() == "*" or name.strip() == current_branch,
                "commit": commit_hash.strip(),
                "upstream": upstream.strip() or None,
                "tracking": tracking.strip() or None,
                "subject": subject.strip() or None,
                "remote": name.strip().startswith("remotes/"),
            }
        )

    return {
        "repo_root": str(repo_root),
        "current_branch": current_branch,
        "all_branches": all_branches,
        "contains": contains,
        "branches": branches,
    }


def git_blame(
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
    revision: str = "HEAD",
) -> dict[str, Any]:
    if start_line is not None and start_line < 1:
        raise ValueError("'start_line' debe ser mayor o igual a 1.")
    if end_line is not None and end_line < 1:
        raise ValueError("'end_line' debe ser mayor o igual a 1.")
    if start_line is not None and end_line is not None and end_line < start_line:
        raise ValueError("'end_line' debe ser mayor o igual a 'start_line'.")

    repo_root, pathspec = _resolve_repo_target(path, require_file=True)
    command = ["blame", "--line-porcelain"]
    if start_line is not None or end_line is not None:
        line_start = start_line or 1
        line_end = end_line or line_start
        command.extend(["-L", f"{line_start},{line_end}"])
    command.extend([revision, "--", pathspec or ""])

    stdout = _run_git(command, cwd=repo_root)
    lines: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in stdout.splitlines():
        if raw_line.startswith("\t"):
            if current is None:
                continue
            entry = {
                "line": current.get("final_line"),
                "commit": current.get("commit"),
                "original_line": current.get("original_line"),
                "author": current.get("author"),
                "author_email": current.get("author_email"),
                "author_time": current.get("author_time"),
                "author_tz": current.get("author_tz"),
                "summary": current.get("summary"),
                "text": raw_line[1:],
            }
            lines.append(entry)
            current = None
            continue

        if current is None:
            header_parts = raw_line.split()
            if len(header_parts) < 3:
                continue
            current = {
                "commit": header_parts[0],
                "original_line": int(header_parts[1]),
                "final_line": int(header_parts[2]),
            }
            continue

        if " " not in raw_line:
            continue

        key, value = raw_line.split(" ", 1)
        if key == "author":
            current["author"] = value
        elif key == "author-mail":
            current["author_email"] = value.strip("<>")
        elif key == "author-time":
            current["author_time"] = int(value)
        elif key == "author-tz":
            current["author_tz"] = value
        elif key == "summary":
            current["summary"] = value

    return {
        "repo_root": str(repo_root),
        "path": pathspec,
        "revision": revision,
        "lines": lines,
    }


def git_ls_files(path: str = ".", pattern: str | None = None) -> dict[str, Any]:
    repo_root, pathspec = _resolve_repo_target(path)
    command = ["ls-files"]
    pathspecs: list[str] = []
    if pathspec is not None:
        pathspecs.append(pathspec)
    if pattern is not None and pattern.strip():
        pathspecs.append(pattern.strip())
    if pathspecs:
        command.extend(["--", *pathspecs])

    stdout = _run_git(command, cwd=repo_root)
    files = [line for line in stdout.splitlines() if line]
    return {
        "repo_root": str(repo_root),
        "pathspec": pathspec,
        "pattern": pattern,
        "files": files,
    }


def _parse_branch_line(line: str) -> dict[str, Any]:
    info = {
        "head": None,
        "upstream": None,
        "ahead": 0,
        "behind": 0,
        "detached": False,
        "no_commits": False,
    }

    text = line
    if text.startswith("No commits yet on "):
        info["no_commits"] = True
        text = text[len("No commits yet on ") :]

    tracking_text = None
    if " [" in text and text.endswith("]"):
        text, tracking_text = text[:-1].split(" [", 1)

    if text == "HEAD (no branch)":
        info["head"] = "HEAD"
        info["detached"] = True
    elif "..." in text:
        head, upstream = text.split("...", 1)
        info["head"] = head
        info["upstream"] = upstream or None
    else:
        info["head"] = text

    if tracking_text:
        for part in tracking_text.split(","):
            chunk = part.strip()
            if chunk.startswith("ahead "):
                info["ahead"] = int(chunk[len("ahead ") :])
            elif chunk.startswith("behind "):
                info["behind"] = int(chunk[len("behind ") :])

    return info


def _resolve_repo_target(
    path: str,
    *,
    require_file: bool = False,
) -> tuple[Path, str | None]:
    target = Path(path).expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(f"La ruta no existe: {target}")
    if require_file and not target.is_file():
        raise ValueError("La ruta debe apuntar a un archivo dentro de un repositorio Git.")

    discovery_dir = target.parent if target.is_file() else target
    repo_root = _discover_repo_root(discovery_dir)
    try:
        relative = target.relative_to(repo_root)
    except ValueError as exc:
        raise RuntimeError(
            f"La ruta '{target}' no pertenece al repositorio '{repo_root}'."
        ) from exc

    if relative == Path(".") or str(relative) == ".":
        return repo_root, None

    return repo_root, relative.as_posix()


def _discover_repo_root(start_dir: Path) -> Path:
    stdout = _run_git(
        ["rev-parse", "--show-toplevel"],
        cwd=start_dir,
        error_prefix="La ruta indicada no pertenece a un repositorio Git.",
    )
    return Path(stdout.strip()).resolve()


def _run_git(
    args: list[str],
    *,
    cwd: Path,
    error_prefix: str | None = None,
) -> str:
    command = ["git", "--no-pager", *args]
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env={
                **os.environ,
                "GIT_PAGER": "",
                "PAGER": "",
                "GIT_TERMINAL_PROMPT": "0",
            },
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Git no esta disponible en PATH.") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip() or "Git devolvio un error sin detalle."
        prefix = error_prefix or "No se pudo ejecutar el comando Git."
        raise RuntimeError(f"{prefix} {detail}")
    return completed.stdout


def _truncate_text(text: str, *, max_bytes: int) -> tuple[str, bool]:
    payload = text.encode("utf-8")
    if len(payload) <= max_bytes:
        return text, False

    clipped = payload[:max_bytes].decode("utf-8", errors="ignore")
    return f"{clipped}\n\n[truncated to {max_bytes} bytes]", True
