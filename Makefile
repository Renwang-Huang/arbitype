.PHONY: test compile package metadata eval-check check release-check

test:
	python3 -m unittest discover -s tests -v

compile:
	python3 -m compileall -q .

package:
	python3 -m pip wheel --no-deps . --wheel-dir /tmp/arbitype-dist

metadata:
	python3 scripts/validate_registry_metadata.py

eval-check:
	python3 scripts/validate_eval_datasets.py
	python3 scripts/run_tool_selection_eval.py --dry-run

release-check:
	python3 scripts/release_readiness.py

check: test compile package metadata eval-check
