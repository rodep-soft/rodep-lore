#!/bin/bash
# -e: エラーが出たら即終了（PIO失敗時にBotを動かさないため）
set -e

cd "$(dirname "$0")/.."

echo "=== Room Server Startup Sequence ==="

# 1. 既存の古いコンテナを一旦掃除（ポート競合回避）
echo "Cleaning up existing containers..."
docker compose stop bot pio || true

# 2. Arduinoへの書き込み (PIO)
# これが成功しない限り次へ進まない
echo "Step 1: Uploading Arduino firmware..."
docker compose run --rm pio

# 3. インターバル（OSのシリアルポート解放待ち）
echo "Waiting for serial port to stabilize..."
sleep 2

# 4. 常駐Botの起動
# systemdで管理する場合は run、バックグラウンドにするなら up -d
echo "Step 2: Starting Discord Monitoring Bot..."
#docker compose run -d --rm bot
docker compose --profile setup up -d --build bot simulator

# 5. シミュレーターとドキュメントサーバーの起動
# simulatorにはprofilesがないので、up -d でまとめて起動
echo "Step 3: Starting Streamlit Simulator..."
# docker compose up -d simulator

echo "=== All services are up! ==="

# ログを流す
docker compose logs -f bot
