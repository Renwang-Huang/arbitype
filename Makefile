.PHONY: test compile package metadata check release-check

test:
	python3 -m unittest discover -s tests -v

compile:
	python3 -m compileall -q .

package:
	python3 -m pip wheel --no-deps . --wheel-dir /tmp/arbitype-dist

metadata:
	python3 scripts/validate_registry_metadata.py

release-check:
	python3 scripts/release_readiness.py

check: test compile package metadata
