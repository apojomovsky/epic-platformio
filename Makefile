.PHONY: docs-gen sync-shared-includes

docs-gen: ## Regenerate docs/reference/boards.md, README.md and registry-README.md
	python3 scripts/gen_docs.py

# Refresh docs/snippets/ways-to-use-epic8.md from apojomovsky/epic-docs at REF (a
# commit sha). Needs the network; docs-gen only checks locally.
sync-shared-includes:
	python3 scripts/shared_includes.py sync --ref "$(REF)"
