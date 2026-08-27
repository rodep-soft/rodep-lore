# RODEP LORE

RODEPのDiscord Bot群および部室管理ファームウェアを管理するモノレポ。

## ディレクトリ構成

```text
├── bots/                  # Discord Bot群 (Python)
│   ├── attendance_bot/    # 出席管理 Bot
│   ├── door_bot/          # ドア解錠・音声通知 Bot
│   └── utils_bot/         # 画像自動転送等の便利 Bot
├── firmware/              # マイコン用ファームウェア (PlatformIO / C++)
│   └── door_lock/         # ドア開閉検知・解錠コード
└── scripts/               # 運用スクリプト (時計等)
```

## クイックスタート

```bash
# 1. 環境変数の作成
$ cp .env.example .env

# 2. 起動 (マイコン書き込み + 全Bot起動)
$ make deploy

# 3. ログ確認
$ make logs
```

### 主なコマンド

```bash
$ make up             # 全サービス起動 (DB・VOICEVOX・Bot群)
$ make down           # 全停止
$ make flash          # マイコンへの書き込み単体
$ make setup-service  # OS起動時の自動デプロイ(systemd)を登録
$ make fmt            # コード自動整形 (Ruff)
$ make lint           # 静的解析 (Ruff)
$ make help           # コマンド一覧
```
