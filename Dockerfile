# 共通Dockerfile


FROM astral/uv:python3.12-bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    pulseaudio-utils \
    libasound2 \
    fontconfig \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*


COPY pyproject.toml uv.lock ./


# DNS
#RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
#    uv sync --frozen

RUN uv sync --frozen


COPY . .

CMD ["bash"]
