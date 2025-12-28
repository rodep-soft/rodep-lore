FROM astral/uv:python3.12-bookworm-slim

WORKDIR /app


COPY pyproject.toml uv.lock ./


#RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
#    uv sync --frozen

RUN uv sync --frozen


COPY . .

CMD ["bash"]
