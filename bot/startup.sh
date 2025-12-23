#!/bin/bash
set -e  # 何かエラーがあったらそこで止める

# 順番大事
# 1. PIOで書き込み
echo "Uploading firmware..."
docker compose run --rm pio

# 2. 書き込みが成功したら、Botを起動
echo "Starting bot..."
docker compose up -d bot
