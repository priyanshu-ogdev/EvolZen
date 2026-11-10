# Base dev image — CPU-only, matches the project's supported Python range.
# See docs/adr/0002-dependency-stack-and-optional-extras.md for why the range is conservative.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx

WORKDIR /workspace
