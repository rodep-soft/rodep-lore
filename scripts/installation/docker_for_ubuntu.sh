#!/usr/bin/env bash

set -e  # エラーが発生したら中断

echo "--- 1. 旧バージョンのDockerを削除中... ---"
# 既存の古いパッケージをまとめて削除
sudo apt-get remove -y docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc || true

echo "--- 2. リポジトリのセットアップ中... ---"
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# GPGキーの登録
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# アーキテクチャとOSバージョンを取得してリポジトリを追加
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$UBUNTU_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "--- 3. Docker Engine & Compose をインストール中... ---"
sudo apt-get update
# docker-compose-plugin を入れることで 'docker compose' (ハイフンなし) が使えます
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "--- 4. ユーザー権限の設定中 (rodep)... ---"
# sudoなしでdockerを使えるようにグループに追加
sudo usermod -aG docker $USER
# シリアルポート（Arduino）へのアクセス権限も同時付与
sudo usermod -aG dialout $USER

echo "--- インストール完了！ ---"
echo "設定を反映させるため、一度ログアウトして再ログインするか、以下のコマンドを打ってください："
echo "newgrp docker"
echo ""
echo "確認コマンド: docker compose version"
