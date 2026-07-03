# OAuth Integration

## Overview

Adds OAuth 2.0 support to bfabricPy. The library can now authenticate via PKCE, device code, client credentials, URL tokens, and personal access tokens — in addition to the existing password-based SOAP auth. All OAuth flows are transparent to downstream code: the SOAP engine receives `BfabricAuth(login="__oauth__", password=<jwt>)` automatically.

---

## New: `bfabric._oauth` module

Private module under `bfabric/src/bfabric/_oauth/` implementing all OAuth primitives.

| File | Purpose |
|------|---------|
| `_constants.py` | `DEFAULT_CLIENT_ID = "CLI"`, `DEFAULT_OAUTH_SCOPE = "api:read api:write"` |
| `credential_provider.py` | `OAuthCredentialProvider` — thread-safe token management with automatic refresh and disk caching. Supports both `client_credentials` and `refresh_token` grant types. |
| `pkce.py` | `pkce_login()` — browser-based PKCE flow. Starts a local HTTP server, opens the browser, exchanges the authorization code for tokens. |
| `device_code.py` | `device_code_login()` — RFC 8628 device authorization flow for headless environments. |
| `registration.py` | `register_client()` — RFC 7591 dynamic client registration via HTTP POST. |
| `token_cache.py` | `TokenCache` — JSON file cache at `~/.bfabric/tokens/{hash}.json` with 0o600 permissions. `compute_token_cache_path()` derives a unique path from `(base_url, client_id, env_name)`. |
| `url_token.py` | `UrlTokenContext` + `parse_url_token()` — extracts entity context (entity_id, application_id, etc.) from B-Fabric URL token JWTs. |
| `webapp_client.py` | `WebappClient` — dual-identity client bundling a `user` (from URL token) and `service` (from client credentials) `Bfabric` instance. |

---

## New: Factory methods on `Bfabric`

| Method | Grant type | Use case |
|--------|-----------|----------|
| `Bfabric.connect()` | auto-detect | Unchanged API. Now auto-detects `auth_method: "oauth"` in config and loads cached tokens. |
| `Bfabric.connect_oauth(client_id, client_secret, base_url)` | client_credentials | Service accounts / background jobs. |
| `Bfabric.connect_pkce(base_url, client_id)` | authorization_code + PKCE | Interactive browser login (programmatic). |
| `Bfabric.connect_device_code(base_url, client_id)` | device_code | Headless interactive login (programmatic). |
| `Bfabric.from_url_token(base_url, jwt, refresh_token)` | URL token | Webapps launched from B-Fabric. Returns `(Bfabric, UrlTokenContext)`. |
| `WebappClient.create(base_url, jwt, ..., client_id, client_secret)` | URL token + client_credentials | Dual-identity webapp client. |

---

## New: CLI commands (`bfabric-cli auth`)

All commands registered under `bfabric-cli auth` via cyclopts.

| Command | File | Description |
|---------|------|-------------|
| `auth pkce <base_url>` | `cli/login/pkce.py` | Browser-based OAuth login. Caches tokens + writes config. |
| `auth device-code <base_url>` | `cli/login/device_code.py` | Headless OAuth login. |
| `auth pat <base_url>` | `cli/login/pat.py` | Personal Access Token login. |
| `auth register <client_name> <redirect_uri>` | `cli/login/register.py` | RFC 7591 dynamic client registration. Outputs JSON. |
| `auth status` | `cli/login/status.py` | Show current auth status for an environment. |
| `auth logout` | `cli/login/logout.py` | Clear cached OAuth tokens. |

All auth commands use `--config-env` (consistent with API commands via `@use_client`).

### `auth register` enhancements

- `--config-env` reuses a cached OAuth token from an existing environment (no manual bearer token needed)
- `--config-file` specifies the config file path
- `base_url` is optional when `--config-env` is provided (inferred from config)
- Token resolution: explicit `--token` > cached OAuth token via `--config-env` > interactive prompt

---

## Config file changes

### New fields in environment config

```yaml
PRODUCTION:
  base_url: "https://bfabric.example.com/bfabric"
  auth_method: "oauth"        # NEW — triggers OAuth flow in Bfabric.connect()
  client_id: "CLI"    # NEW — optional, defaults to "CLI"
```

### New: `config_writer.py`

`write_environment_to_config()` — creates or updates a YAML environment section with atomic writes (0o600 permissions). Used by all login commands.

### `ConfigData` / `EnvironmentConfig`

Both models gained `auth_method` and `client_id` fields. `Bfabric.connect()` checks `auth_method == "oauth"` to route to `_connect_oauth_from_config()`.

---

## CLI error handling improvements

- `@use_client` decorator now catches `ValueError` / `RuntimeError` from `Bfabric.connect()` and from the wrapped function, printing clean error messages to stderr and exiting with code 1.
- Removed `@logger.catch(reraise=True)` from all API commands (create, read, update, delete, inspect) — error handling is now centralized in `@use_client`.
- `ResultContainer.assert_success()` now formats errors inline (`"Query was not successful: Insufficient scope..."`) instead of passing a tuple.

---

## Dependencies

- `authlib` — new dependency (added to `bfabric/pyproject.toml`)
- `httpx` — used by `registration.py` for RFC 7591 HTTP calls

---

## Test coverage

~1800 lines of new tests across 15 test files covering:

- All OAuth flows (PKCE, device code, client credentials, URL token)
- Credential provider (token refresh, thread safety, disk caching, cache priority)
- Token cache (save/load/clear, path computation, permissions)
- Client registration
- Webapp client
- All 6 CLI auth commands
- Config file parsing with new OAuth fields
- Config writer

---

## Scope enforcement (server-side)

B-Fabric now enforces OAuth scopes at the API level:
- `api:read` required for SOAP read operations
- `api:write` required for SOAP write operations
- Additional scopes (e.g. `tus`, `download`) can be requested and are enforced by their respective endpoints

The `CLI` default client is pre-registered with: `openid, profile, email, api:read, api:write, tus, download, offline_access`.

---

## How to install from this branch

```bash
# As a library dependency
pip install "bfabric @ git+https://github.com/fgcz/bfabricPy.git@oauth-integration#subdirectory=bfabric"

# As a CLI tool (both packages from branch)
uv tool install \
  "bfabric-scripts @ git+https://github.com/fgcz/bfabricPy.git@oauth-integration#subdirectory=bfabric_scripts" \
  --with "bfabric @ git+https://github.com/fgcz/bfabricPy.git@oauth-integration#subdirectory=bfabric" \
  --reinstall
```
