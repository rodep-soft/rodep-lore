.PHONY: help build up down restart logs deploy flash up-pio setup-clock prune-network lint fmt test-up

help: ## コマンド一覧を表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

build: ## Dockerイメージのビルド
	docker compose build

up: ## 全Bot・サービスをバックグラウンド起動 (DBヘルスチェック連携)
	docker compose up -d

down: ## 全サービスを停止
	docker compose down

restart: ## 全サービスを再起動
	docker compose restart

logs: ## 全サービスのログをリアルタイム表示
	docker compose logs -f

deploy: flash up ## マイコン書き込みから全Bot起動までを一括実行

flash: ## マイコンにファームウェアを書き込み (PlatformIO)
	docker compose --profile pio up --build pio

up-pio: flash ## flashのエイリアス

setup-service: ## systemdサービス(OS起動時自動実行)を登録・有効化
	@echo "Installing systemd service for current directory..."
	@sed "s|CURRENT_WORKING_DIR|$(CURDIR)|g" rodep-lore.service | sudo tee /etc/systemd/system/rodep-lore.service > /dev/null
	@sudo systemctl daemon-reload
	@sudo systemctl enable rodep-lore.service
	@echo "✅ rodep-lore.service registered and enabled!"

setup-clock: ## 時計スクリプトのセットアップ
	bash scripts/clock/setup_clock.sh

prune-network: ## 未使用のDockerネットワークを全削除
	docker network prune -f

lint: ## Ruffでコードを静的解析
	uv run ruff check .

fmt: ## Ruffでコードを自動フォーマット
	uv run ruff format .

test-up: ## テスト用プロファイルで起動
	docker compose --profile test up -d --build
