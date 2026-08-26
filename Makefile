.PHONY: build up-pio up-sim setup-clock prune-network test-up

build:
	docker compose build

up-pio:
	docker compose up -d pio

up-sim:
	docker compose up -d simulator

setup-clock:
	bash scripts/clock/setup_clock.sh

# 未使用のネットワークを全削除
prune-network:
	docker network prune -f

test-up:
	docker compose --profile test up -d --build
