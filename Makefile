.PHONY: docs-gen

docs-gen: ## Regenerate docs/reference/boards.md, README.md and registry-README.md
	python3 scripts/gen_docs.py
