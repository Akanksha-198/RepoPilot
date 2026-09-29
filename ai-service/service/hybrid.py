"""Phase 7K - hybrid retrieval: semantic candidates + lexical (BM25-lite) + filename/metadata boost, fused with RRF."""
import math
import re
from collections import Counter

from app.retriever import retrieve_code as _semantic

_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "it", "this", "that", "with",
    "please", "check", "fix", "make", "add", "remove", "change", "update", "file", "code", "error",
}
_FILE_RE = re.compile(r"[\w./\\-]+\.[A-Za-z0-9]{1,5}\b")


def _tokens(text: str):
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")
    return [t for t in re.findall(r"[A-Za-z0-9]+", text.lower()) if len(t) > 1 and t not in _STOP]


def _key(s):
    m = s.get("metadata", {}) or {}
    return (m.get("file_path"), m.get("start_line"))


def hybrid_retrieve(query, repository_name=None, n_results=3, **kwargs):
    pool_n = max(n_results * 5, 15)

    def sem(q, n):
        try:
            return _semantic(q, repository_name=repository_name, n_results=n, **kwargs) or []
        except Exception:
            return _semantic(q, repository_name=repository_name, n_results=n_results, **kwargs) or []

    pool = sem(query, pool_n)
    mentioned = [re.sub(r"^(\./|/)+", "", m.replace("\\", "/")) for m in _FILE_RE.findall(query or "")]

    seen = {_key(s) for s in pool}
    for name in mentioned:  # metadata-aware candidate expansion
        for s in sem(name, n_results):
            if _key(s) not in seen:
                pool.append(s)
                seen.add(_key(s))

    if not pool:
        return []

    docs = [_tokens(s.get("content", "") + " " + str((s.get("metadata") or {}).get("file_path", ""))) for s in pool]
    qt = set(_tokens(query))
    n = len(docs)
    df = {t: sum(1 for d in docs if t in d) for t in qt}

    def lex(d):
        tf = Counter(d)
        return sum((tf[t] / (tf[t] + 1.2)) * math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in qt if tf[t])

    lex_scores = [lex(d) for d in docs]
    lex_rank = {i: r for r, i in enumerate(sorted(range(n), key=lambda i: -lex_scores[i]))}

    fused = []
    for i, s in enumerate(pool):
        fp = str((s.get("metadata") or {}).get("file_path", "")).replace("\\", "/")
        boost = 0.05 if any(fp.endswith(m) for m in mentioned) else 0.0
        fused.append((1 / (60 + i) + 1 / (60 + lex_rank[i]) + boost, i))
    fused.sort(reverse=True)
    return [pool[i] for _, i in fused[:n_results]]
