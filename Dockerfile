# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

LABEL org.opencontainers.image.title="Falsification Engine"
LABEL org.opencontainers.image.description="Pre-registration and CI for AI-agent claims"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/<USER>/falsify-hackathon"

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /falsify

# Copy only what's needed for pip install first (better layer caching).
COPY pyproject.toml falsify.py README.md LICENSE ./

RUN pip install --no-cache-dir -e .

# Copy the rest of the source.
COPY . .

# Initialize git inside the image so commit-msg hooks can be tested.
RUN git init -q \
 && git add . \
 && git -c user.email=demo@falsify.local -c user.name=demo commit -q -m "initial" \
 || true

# Build-time sanity check — fails the build if the CLI is broken.
RUN falsify --version && falsify doctor --specs-only

# Default command: the auto-narrated end-to-end demo.
ENV DEMO_AUTO=1
CMD ["./demo.sh"]
