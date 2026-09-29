"""Phase 7I - incremental indexing: content-hash manifest so unchanged repos are never re-embedded."""
import hashlib
import json
import os
from pathlib import Path

from .config import DATA_DIR

SUPPORTED = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".cs",
             ".rb", ".php", ".html", ".css", ".json", ".md", ".yml", ".yaml", ".sh"}
IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", "coverage"}


def _manifest_path(key: str) -> Path:
    return DATA_DIR / "manifests" / f"{key}.json"


def fingerprint(repo_path: Path) -> dict:
    out = {}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if ".bak" in f or ".backup" in f or Path(f).suffix.lower() not in SUPPORTED:
                continue
            p = Path(root) / f
            try:
                if p.stat().st_size > 1_500_000:
                    continue
                out[str(p.relative_to(repo_path)).replace("\\", "/")] = hashlib.sha1(p.read_bytes()).hexdigest()
            except OSError:
                continue
    return out


def sync_index(repo_path, repo_key: str, force: bool = False) -> dict:
    from app.agent_graph_ui import ingest_repository_files

    repo_path = Path(repo_path)
    current = fingerprint(repo_path)
    mp = _manifest_path(repo_key)
    previous = json.loads(mp.read_text()) if mp.exists() else None

    if previous and not force and previous.get("files") == current:
        return {"status": "unchanged", "chunks": previous.get("chunks", 0), "files": len(current), "changed": 0}

    prev_files = (previous or {}).get("files", {})
    changed = [f for f, h in current.items() if prev_files.get(f) != h] + [f for f in prev_files if f not in current]
    chunks = ingest_repository_files(str(repo_path), repo_key)
    mp.write_text(json.dumps({"files": current, "chunks": chunks}))
    return {"status": "indexed", "chunks": chunks, "files": len(current), "changed": len(changed)}


def drop_manifest(repo_key: str):
    _manifest_path(repo_key).unlink(missing_ok=True)
