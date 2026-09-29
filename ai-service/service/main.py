"""
RepoPilot AI service (FastAPI).
Wraps the existing LangGraph agent in /app WITHOUT modifying it.
Only reachable from the Express backend (X-Internal-Key).
"""
import hmac
import json
import logging
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import agent_graph_ui as ui
from app import failure_analyzer, repair_proposer
from app.git_tools import (
    commit_changes, create_feature_branch, get_git_diff, get_git_status, get_last_commit_info,
    ignore_backup_files, push_branch, revert_last_commit, undo_last_commit,
)
from app.github_api import create_pull_request
from app.github_Tool import clone_repository, repository_name as repo_name_from_url
from app.scanner import scan_repository

from .config import INTERNAL_API_KEY, WORKSPACE_ROOT
from .gitenv import github_env
from .hybrid import hybrid_retrieve
from .incremental import drop_manifest, sync_index
from .security import GuardedLLM, is_blocked_path, review_guard

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("ai")

# ---- Phase 7E / 7K: patch the agent at runtime (no edits to /app files) ----
for _mod in (ui, failure_analyzer, repair_proposer):
    if hasattr(_mod, "get_llm"):
        _orig = _mod.get_llm
        _mod.get_llm = (lambda o: (lambda: GuardedLLM(o())))(_orig)
ui.retrieve_code = hybrid_retrieve

GITHUB_URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?(\.git)?/?$")
SEGMENT = re.compile(r"[^A-Za-z0-9_-]")


def require_key(x_internal_key: str = Header(default="")):
    if not INTERNAL_API_KEY or not hmac.compare_digest(x_internal_key, INTERNAL_API_KEY):
        raise HTTPException(401, "Invalid internal key")


def safe_repo_path(p: str) -> Path:
    path = Path(p).resolve()
    try:
        path.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise HTTPException(400, "Repository path is outside the workspace.")
    if not path.is_dir():
        raise HTTPException(404, "Repository not found on disk.")
    return path


app = FastAPI(title="RepoPilot AI", docs_url=None, redoc_url=None)
router = APIRouter(dependencies=[Depends(require_key)])


@app.middleware("http")
async def access_log(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    t0 = time.time()
    response = await call_next(request)
    log.info(json.dumps({"rid": rid, "path": request.url.path, "status": response.status_code,
                         "ms": int((time.time() - t0) * 1000)}))
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {str(exc)[:400]}"})


@app.get("/health")
def health():
    return {"ok": True}


# ------------------------------------------------------------ repositories
class CloneBody(BaseModel):
    github_url: str
    owner_key: str
    repository_key: str


@router.post("/repos/clone")
def clone(body: CloneBody, x_github_token: str = Header(default="")):
    if not GITHUB_URL.match(body.github_url):
        raise HTTPException(400, "Only https://github.com/<owner>/<repo> URLs are supported.")
    dest = WORKSPACE_ROOT / SEGMENT.sub("_", body.owner_key)
    dest.mkdir(parents=True, exist_ok=True)
    with github_env(x_github_token):
        repo_path = Path(clone_repository(body.github_url, dest)).resolve()
    repo_path.relative_to(WORKSPACE_ROOT)
    scan = scan_repository(repo_path)
    idx = sync_index(repo_path, body.repository_key, force=True)
    return jsonable_encoder({
        "repository_path": str(repo_path),
        "name": repo_name_from_url(body.github_url),
        "scan": scan,
        "chunks": idx["chunks"],
    })


class RepoBody(BaseModel):
    repository_path: str
    repository_name: str = ""
    force: bool = False


@router.post("/repos/reindex")
def reindex(body: RepoBody):
    path = safe_repo_path(body.repository_path)
    idx = sync_index(path, body.repository_name, force=body.force)
    return jsonable_encoder({"scan": scan_repository(path), **idx})


@router.post("/repos/delete")
def delete_repo(body: RepoBody):
    path = safe_repo_path(body.repository_path)
    if path.parent == WORKSPACE_ROOT or path == WORKSPACE_ROOT:
        raise HTTPException(400, "Refusing to delete a workspace root.")
    shutil.rmtree(path, ignore_errors=True)
    drop_manifest(body.repository_name)
    return {"ok": True}


# ------------------------------------------------------------------- tasks
class AnalyzeBody(BaseModel):
    user_request: str
    repository_path: str
    repository_name: str


@router.post("/tasks/analyze")
def analyze(body: AnalyzeBody):
    path = safe_repo_path(body.repository_path)
    sync_index(path, body.repository_name)  # cheap no-op when nothing changed
    result = ui.build_ui_agent_graph().invoke({
        "user_request": body.user_request,
        "repository_name": body.repository_name,
        "repository_path": str(path),
    })
    return jsonable_encoder(review_guard(result))


def _prepare_branch(state: dict) -> dict:
    path = safe_repo_path(state.get("repository_path", ""))
    branch = create_feature_branch(str(path), user_request=state.get("user_request", ""))
    if not branch.get("success"):
        raise HTTPException(409, f"Could not prepare a safe branch: {branch.get('error')}")
    return branch


class StateBody(BaseModel):
    state: dict


@router.post("/tasks/apply")
def apply_change(body: StateBody):
    state = dict(body.state)
    changes = state.get("proposed_changes") or []
    if not changes or is_blocked_path(changes[0].get("file_path", "")):
        raise HTTPException(400, "This change targets a protected path or is missing.")
    branch = _prepare_branch(state)
    state["change_approved"] = True
    out = ui.build_apply_graph().invoke(state)
    out["applied_on_branch"] = branch["branch"]
    if out.get("change_result", {}).get("status") == "modified":
        sync_index(state["repository_path"], state.get("repository_name", ""))
    return jsonable_encoder(out)


@router.post("/tasks/repair/prepare")
def repair_prepare(body: StateBody):
    safe_repo_path(body.state.get("repository_path", ""))
    out = ui.create_repair_diff(dict(body.state))
    fp = (out.get("repair_proposal") or {}).get("file_path", "")
    if fp and is_blocked_path(fp):
        out["repair_diff"] = ""
        out["repair_result"] = {"status": "failed", "message": f"Blocked: '{fp}' is a protected path."}
    return jsonable_encoder(out)


class RepairApplyBody(BaseModel):
    apply_state: dict
    repair_result: dict


@router.post("/tasks/repair/apply")
def repair_apply(body: RepairApplyBody):
    state = dict(body.apply_state)
    state.update(body.repair_result)
    fp = (state.get("repair_proposal") or {}).get("file_path", "")
    if not fp or is_blocked_path(fp):
        raise HTTPException(400, "Repair targets a protected path or is missing.")
    branch = _prepare_branch(state)
    state["repair_approved"] = True
    out = ui.build_repair_apply_graph().invoke(state)
    out["applied_on_branch"] = branch["branch"]
    if out.get("repair_result", {}).get("status") == "modified":
        sync_index(state["repository_path"], state.get("repository_name", ""))
    return jsonable_encoder(out)


# --------------------------------------------------------------------- git
class GitBody(BaseModel):
    repository_path: str
    file_path: Optional[str] = None
    files: Optional[list[str]] = None
    message: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None


@router.post("/git/{action}")
def git(action: str, b: GitBody, x_github_token: str = Header(default="")):
    path = str(safe_repo_path(b.repository_path))
    if action == "status":
        return jsonable_encoder(get_git_status(path))
    if action == "diff":
        return jsonable_encoder(get_git_diff(path, file_path=b.file_path) if b.file_path else get_git_diff(path))
    if action == "last-commit":
        return jsonable_encoder(get_last_commit_info(path))
    if action == "commit":
        files = [f for f in (b.files or []) if not is_blocked_path(f)]
        if not files or not (b.message or "").strip():
            raise HTTPException(400, "Files and a commit message are required.")
        return jsonable_encoder(commit_changes(path, files, b.message))
    if action == "push":
        with github_env(x_github_token):
            return jsonable_encoder(push_branch(path))
    if action == "undo":
        return jsonable_encoder(undo_last_commit(path))
    if action == "revert":
        return jsonable_encoder(revert_last_commit(path))
    if action == "ignore-backups":
        return jsonable_encoder(ignore_backup_files(path))
    if action == "pr":
        with github_env(x_github_token):
            return jsonable_encoder(create_pull_request(path, b.title or "", b.body or ""))
    raise HTTPException(404, "Unknown git action")


app.include_router(router)
