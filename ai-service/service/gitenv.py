"""Phase 7D - per-request GitHub token injection (never stored on disk, never logged)."""
import os
import stat
import tempfile
import threading
from contextlib import contextmanager

_LOCK = threading.RLock()
_ASKPASS = os.path.join(tempfile.gettempdir(), "rp_askpass.sh")


def _ensure_askpass():
    if not os.path.exists(_ASKPASS):
        with open(_ASKPASS, "w") as f:
            f.write('#!/bin/sh\ncase "$1" in\n  Username*) echo "x-access-token" ;;\n  *) echo "$GITHUB_TOKEN" ;;\nesac\n')
        os.chmod(_ASKPASS, stat.S_IRWXU)


@contextmanager
def github_env(token: str):
    if not token:
        yield
        return
    with _LOCK:
        _ensure_askpass()
        keys = ["GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS", "GIT_TERMINAL_PROMPT"]
        saved = {k: os.environ.get(k) for k in keys}
        os.environ.update({"GITHUB_TOKEN": token, "GH_TOKEN": token, "GIT_ASKPASS": _ASKPASS, "GIT_TERMINAL_PROMPT": "0"})
        try:
            yield
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
