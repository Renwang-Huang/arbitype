# MCP Registry migration

Arbitype uses the new canonical identity:

```text
io.github.Renwang-Huang/arbitype
```

The former identity remains a legacy entry:

```text
io.github.Renwang-Huang/typesafe-mcp
```

The release workflow publishes only the new identity. It does not overwrite,
delete, or mutate the legacy entry. This prevents a package rename from
silently breaking existing host configurations.

## Maintainer procedure

1. Publish `arbitype` to PyPI.
2. Create a release tag matching `arbitype._version.__version__`.
3. Let `Publish to MCP Registry` publish `server.json` under the new identity.
4. Verify the new entry at the official Registry and allow Glama to crawl the
   renamed repository.
5. If the current `mcp-publisher` release documents a supported deprecation
   operation, manually mark the legacy entry with:

   ```text
   TypeSafe MCP has been renamed to Arbitype. Use
   io.github.Renwang-Huang/arbitype for new installations.
   ```

   Do not run an undocumented delete, overwrite, or identity-mutation command.
   If deprecation is not supported, leave the legacy entry intact and keep the
   migration notice in the README and release notes.

The repository workflow deliberately automates only the safe new-identity
publication path.

For Python environments, uninstall the old `typesafe-mcp` distribution before
installing `arbitype`; both distributions contain the legacy module paths and
should not be installed side by side.
