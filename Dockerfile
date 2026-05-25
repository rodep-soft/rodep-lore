# 共通Dockerfile


FROM astral/uv:python3.12-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Use a separate directory for the virtual environment to avoid conflicts with host mounts
ENV UV_PROJECT_ENVIRONMENT=/venv

RUN apt-get update && apt-get install -y --no-install-recommends \
    pulseaudio-utils \
    libasound2 \
    fontconfig \
    fonts-noto-cjk \
    iproute2 \
    network-manager \
    && rm -rf /var/lib/apt/lists/*


COPY pyproject.toml uv.lock ./


# DNS
#RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
#    uv sync --frozen

RUN uv sync --frozen


COPY . .

CMD ["bash"]
