FROM python:3.12-slim

# git for repo operations, node/npm so the validator can run `npm run build` on JS repos
RUN apt-get update && apt-get install -y --no-install-recommends git nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    # your validator calls "npm.cmd" (Windows); this shim makes it work on Linux unchanged
    && ln -s "$(command -v npm)" /usr/local/bin/npm.cmd

RUN useradd -m -u 10001 rp
WORKDIR /srv

COPY requirements.txt requirements-extra.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 10 --timeout 120 chromadb==1.5.9 onnxruntime==1.30.0 numpy==2.5.3 grpcio==1.84.0

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 10 --timeout 120 -r requirements.txt -r requirements-extra.txt

COPY app ./app
COPY service ./service

RUN mkdir -p /srv/workspace /srv/chroma_db /srv/data \
    && chown -R rp:rp /srv \
    && git config --system user.name "RepoPilot" \
    && git config --system user.email "repopilot@users.noreply.github.com" \
    && git config --system --add safe.directory '*'

USER rp
ENV PYTHONUNBUFFERED=1 WORKSPACE_ROOT=/srv/workspace DATA_DIR=/srv/data
EXPOSE 8000
# ONE worker: Chroma + the GitHub-token env lock are process-local
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
