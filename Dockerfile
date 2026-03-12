# Multi-stage: deps cached, then app
FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY app ./app
RUN uv sync --no-dev --frozen

# Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY app ./app
COPY pyproject.toml uv.lock ./

EXPOSE 8000

ENTRYPOINT ["uvicorn", "app.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
