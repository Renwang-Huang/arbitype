# Supply-chain posture

Arbitype keeps its runtime dependency-free and hardens the release path around
that small surface.

## Current controls

- PyPI publication uses OIDC trusted publishing; no package token is stored in
  the repository.
- MCP Registry publication uses GitHub OIDC and a SHA-256-pinned
  `mcp-publisher` binary.
- GitHub Actions used by CI and release workflows are pinned to full commit
  SHAs with the upstream tag retained in a comment.
- PyPI distributions receive GitHub artifact provenance attestations before
  publication.
- CodeQL scans the Python codebase on pushes, pull requests, and a weekly
  schedule.
- OpenSSF Scorecard was evaluated, but its GitHub Action currently cannot run
  in this repository's runner environment: the upstream GCR action image is
  denied because billing is required. The failing workflow was not retained
  as a misleading release check; revisit Scorecard through a verified binary
  or supported runner path before making it required.
- Wheel checks reject bytecode and the package declares no runtime
  dependencies.

## Deliberately deferred

An SBOM generator is not yet part of the release gate. The current wheel has no
runtime dependencies, and adding a generator would require choosing a stable
SBOM format, retention policy, and publication location. This is a release
artifact policy decision rather than a reason to add a runtime dependency.
