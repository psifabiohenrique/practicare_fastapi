FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm


WORKDIR /app

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"

# # cria grupo e usuário
# RUN groupadd -r appuser && useradd -r -g appuser appuser

# # define permissões (ajuste se necessário)
# RUN chown -R appuser:appuser /app

# # muda o usuário padrão
# USER appuser

CMD ["fastapi", "run", "src/main.py", "--port", "8000", "--host", "0.0.0.0"]
