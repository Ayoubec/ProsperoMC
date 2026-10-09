SHELL := /bin/bash
.DEFAULT_GOAL := launcher

.PHONY: launcher native frontend-check backend-check check
launcher:
	bash scripts/build-launcher.sh
native:
	bash scripts/build-ps5.sh
frontend-check:
	bash tests/frontend/run.sh
backend-check:
	python3 -m unittest discover -s tests/launcher -p 'test_*.py' -v
check: frontend-check backend-check
