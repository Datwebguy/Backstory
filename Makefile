.PHONY: hydra hydra-s3 smoke persist test demo eval eval-official api

hydra:
	docker compose up -d

# Sustained write load. Requires AWS_* in .env. See hydra-db/hydradb#81.
hydra-s3:
	docker compose -f docker-compose.yml -f docker-compose.s3.yml up -d

smoke:
	python -m backstory.tools.smoke_hydradb

persist:
	python -m backstory.tools.smoke_hydradb --persist-only

test:
	pytest -q

demo:
	python -m backstory.demo.load_demo

eval:
	python -m backstory.eval.run_smoke_eval

eval-official:
	python -m backstory.eval.run_official --dataset data/lme/oracle_strat12.json --limit 0 --out-dir runs/lme/strat12

api:
	python -m backstory.api.app
