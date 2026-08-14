.PHONY: hydra smoke persist test demo eval api

hydra:
	docker compose up -d

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

api:
	python -m backstory.api.app
