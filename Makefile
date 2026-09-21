.PHONY: test compile package check

test:
	python3 -m unittest discover -s tests -v

compile:
	python3 -m compileall -q .

package:
	python3 -m pip wheel --no-deps . --wheel-dir /tmp/typesafe-codex-mcp-dist

check: test compile package
