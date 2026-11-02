# Dependency stage: runs natively on the build host and installs wheels for the target arch.
FROM --platform=$BUILDPLATFORM ghcr.io/astral-sh/uv:0.9.30-python3.12-bookworm-slim AS build
ARG TARGETARCH
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-hashes --no-emit-project -o requirements.txt \
 && case "$TARGETARCH" in arm64) plat=aarch64-manylinux_2_28 ;; *) plat=x86_64-manylinux_2_28 ;; esac \
 && uv pip install --no-cache --target /deps --python-version 3.12 --python-platform "$plat" --only-binary :all: -r requirements.txt

# Runtime stage: copies the installed dependencies and the bot, no build tools.
FROM ghcr.io/astral-sh/uv:0.9.30-python3.12-bookworm-slim AS production
ENV PYTHONPATH=/deps PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=build /deps /deps
COPY main.py handlers.py /app/
WORKDIR /app
USER 10001:10001
ENTRYPOINT ["python", "/app/main.py"]
