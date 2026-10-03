.PHONY: up down logs test bench sip-up sip-logs

up:
	docker compose up -d --build

sip-up:
	docker compose --profile sip up -d --build

down:
	docker compose down

logs:
	docker compose logs -f agent

sip-logs:
	docker compose logs -f sip

test:
	cd agent && uv run pytest

bench:
	python3 scripts/summarize.py

