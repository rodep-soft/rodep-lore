# 共通Dockerfile


FROM astral/uv:python3.12-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Use a separate directory for the virtual environment
ENV UV_PROJECT_ENVIRONMENT=/venv
ENV PATH="/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    pulseaudio-utils \
    libasound2 \
    fontconfig \
    fonts-noto-cjk \
    iproute2 \
    network-manager \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

COPY . .

CMD ["bash"]
