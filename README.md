# RODEP LORE

RODEPのDiscord Bot群および部室管理ファームウェアを統合管理するモノレポです。

※ ドキュメント（Wiki/知見）は [rodep-soft/docs](https://github.com/rodep-soft/docs) に移行しました。

## ディレクトリ構成

```text
.
├── bots/                  # Discord Bot群 (Python)
│   ├── attendance_bot/    # 出席管理 Bot
│   ├── door_bot/          # ドア解錠・音声通知 Bot
│   └── utils_bot/         # 画像転送等の便利機能 Bot
├── firmware/              # マイコン用ファームウェア (C++ / PlatformIO)
│   └── door_lock/         # ドア開閉検知・解錠用マイコンコード
├── scripts/               # 運用スクリプト (時計等)
├── compose.yaml           # Docker Compose 設定
├── Dockerfile             # 共通実行環境
├── pyproject.toml         # Python 依存関係 (uv / Ruff)
├── uv.lock
├── .env.example           # 共通環境変数テンプレート
└── Makefile               # 運用用コマンド集
```

## クイックスタート

### 1. 環境変数の設定

リポジトリルートの `.env.example` をコピーして `.env` を作成し、トークン等を設定します。

```bash
cp .env.example .env
```

### 2. コマンド操作 (Makefile)

`make help` で利用可能なコマンド一覧を確認できます。

```bash
# マイコン書き込みから全Bot起動まで一括実行 (本番デプロイ時)
$ make deploy

# 全サービス（Bot群 + DB + VOICEVOX）の起動 (DB準備完了後に自動起動)
$ make up

# ログの確認
$ make logs

# マイコンへのファームウェア書き込み単体 (PlatformIO)
$ make flash

# サービスの停止
$ make down

# コードの静的解析・フォーマット
$ make lint
$ make fmt
```

### 3. ローカル開発環境 (uv)

```bash
$ uv sync
```

#### Author
- Tatsuki Yano
