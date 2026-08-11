# PEARL-Neuro PSWT research pipeline — inference-only image.
# Build context must be the repo root (data/, pearl/): `docker build -f pearl/Dockerfile .`
FROM python:3.11-slim

WORKDIR /app

COPY pearl/pyproject.toml pearl/README.md /app/
COPY pearl/src /app/src
COPY pearl/config /app/config

RUN pip install --no-cache-dir -e .

# Real data (pearl/data/) is intentionally NOT baked into the image (too
# large) — mount it at runtime. Scoring a subject needs data/raw/<subject>
# (input), data/derivatives/preproc (Phase 1 output, needs write access),
# and data/derivatives/models (the shipped model + provenance.json). See
# RUNBOOK.md.
VOLUME ["/app/data"]

ENTRYPOINT ["pearl-models"]
CMD ["--help"]
