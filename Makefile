.PHONY: build up-sphinx up-pio up-sim

build:
	docker compose build

up-sphinx:
	docker compose up -d sphinx

up-pio:
	docker compose up -d pio

up-sim:
	docker compose up -d simulator

# 未使用のネットワークを全削除
prune-network:
	docker network prune -f

