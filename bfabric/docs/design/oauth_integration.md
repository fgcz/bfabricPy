# OAuth Integration

## Overview

Adds OAuth 2.0 support to bfabricPy. The library can now authenticate via PKCE, device code, client credentials, URL tokens, and personal access tokens — in addition to the existing password-based SOAP auth. All OAuth flows are transparent to downstream code: the SOAP engine receives `BfabricAuth(login="__oauth__", password=<jwt>)` automatically.

> For task-oriented usage and troubleshooting (obtaining a working token, access_token vs id_token, the `containers` claim for file/download access, PKCE gotchas), see [OAuth Usage & Troubleshooting](oauth_usage_and_troubleshooting.md).

---

## New: `bfabric.oauth` module

Package under `bfabric/src/bfabric/oauth/` implementing all OAuth primitives.

The package root is the entire public surface: every submodule is underscore-prefixed, so the only supported import is `from bfabric.oauth import ...`. `__init__` exports `OAuthCredentialProvider`, `pkce_login`, `device_code_login`, `register_client`, `register_webapp`, `TokenCache`, `compute_token_cache_path`, `UrlTokenContext` and `WebappClient` — enough that nothing outside the package, including `bfabric_scripts`, ever names a module. Those names are provisional while the asgi-auth OAuth migration is in flight and may change without a deprecation cycle.

`bfabric.py` is the one place that names the private submodules, and only because `__init__` re-exports `WebappClient`, whose module imports `Bfabric` — routing `connect_*` through the root makes that a static import cycle. It is an intra-package import, not a consumer reaching in.

Separately, those `connect_*` imports are *function-local*: the OAuth code pulls `authlib` and `joserfc`, and `import bfabric` must stay free of both. Note that targeting a submodule does not by itself avoid this — importing `bfabric.oauth.<anything>` executes `__init__` first — so laziness, not module choice, is what keeps the base import clean.

| File | Purpose |
|------|---------|
| `_credential_provider.py` | `OAuthCredentialProvider` — thread-safe token management with automatic refresh and disk caching. Supports both `client_credentials` and `refresh_token` grant types. |
| `_pkce.py` | `pkce_login()` — browser-based PKCE flow. Starts a local HTTP server, opens the browser, exchanges the authorization code for tokens. |
| `_device_code.py` | `device_code_login()` — RFC 8628 device authorization flow for headless environments. |
| `_registration.py` | `register_client()` — RFC 7591 dynamic client registration via HTTP POST. |
| `_token_cache.py` | `TokenCache` — JSON file cache at `~/.bfabric/tokens/{hash}.json` with 0o600 permissions. `compute_token_cache_path()` derives a unique path from `(base_url, client_id, env_name)`. |
| `_url_token.py` | `UrlTokenContext` + `parse_url_token()` — extracts entity context (entity_id, application_id, etc.) from B-Fabric URL token JWTs. |
| `_webapp_client.py` | `WebappClient` — dual-identity client bundling a `user` (from URL token) and `service` (from client credentials) `Bfabric` instance. |

The core `oauth` API requires explicit `client_id` and `scope` arguments on all OAuth entry points. The library does not bake in a default client ID or scope. Tools like the CLI specify these values explicitly.

---

## New: Factory methods on `Bfabric`

| Method | Grant type | Use case |
|--------|-----------|----------|
| `Bfabric.connect()` | auto-detect | Unchanged API. Now auto-detects `auth_method: "oauth"` in config and loads cached tokens. |
| `Bfabric.connect_oauth(client_id, client_secret, base_url)` | client_credentials | Service accounts / background jobs. |
| `Bfabric.connect_pkce(base_url, client_id)` | authorization_code + PKCE | Interactive browser login (programmatic). |
| `Bfabric.connect_device_code(base_url, client_id)` | device_code | Headless interactive login (programmatic). |
| `WebappClient.create(base_url, launch_token, ..., client_id, client_secret)` | URL token + client_credentials | Dual-identity webapp client for apps launched from B-Fabric. |

---

## New: CLI commands (`bfabric-cli auth`)

All commands registered under `bfabric-cli auth` via cyclopts.

| Command | File | Description |
|---------|------|-------------|
| `auth login [base_url]` | `cli/login/oauth_login.py` | Browser-based OAuth login. Caches tokens + writes config. Also registered top-level as `bfabric-cli login`. |
| `auth device-code [base_url]` | `cli/login/oauth_login.py` | Headless OAuth login. |
| `auth pat <base_url>` | `cli/login/pat.py` | Personal Access Token login. |
| `auth register <client_name> <redirect_uri>` | `cli/login/register.py` | RFC 7591 dynamic client registration. Outputs JSON. |
| `auth register-webapp <client_name> <redirect_uri>` | `cli/login/register_webapp.py` | Registration preset for webapps (OIDC-inclusive scope). |
| `auth status` | `cli/login/manage.py` | Show auth status for an environment. |
| `auth list` | `cli/login/manage.py` | List environments grouped by instance, with scope / expiry / why-active. |
| `auth activate [env]` | `cli/login/manage.py` | Make an environment the config default. |
| `auth logout [env]` | `cli/login/manage.py` | Remove stored credentials for this machine, keeping the environment. `--all` for every environment. |
| `auth remove [env]` | `cli/login/manage.py` | Delete an environment: config entry plus cached tokens. |

See [the CLI authentication guide](../user_guides/bfabric-cli/authentication.md) for the user-facing
view; this section covers only what is not visible from the outside.

All auth commands resolve the environment as `--config-env` > `BFABRICPY_CONFIG_ENV` >
`GENERAL.default_config`, matching `ConfigFile.get_selected_config_env`, and `base_url` is optional
for the login commands because it is read back from that environment. Commands that write to the
config refuse to run while `BFABRICPY_CONFIG_OVERRIDE` is set, since the file would not be the config
in effect.

`auth logout` removes credentials per auth method — the token cache for `oauth`, the inline `pat` or
`login`/`password` keys for the others (via `clear_environment_credentials`). It deliberately does not
revoke server-side. Instances *do* advertise `revocation_endpoint` in their discovery document (trace:
`{base_url}/rest/oauth/token` → `/rest/oauth/revoke`), but whether it is implemented is unverified, so
logout promises only what it delivers: local credentials gone, an issued token valid until it expires.

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
  scope: "api:write tus"      # NEW — the scope *requested* at login
```

`scope` is what makes a login replayable from disk, and it is deliberately the **requested** value
rather than the granted one: the server drops scopes the client isn't registered for, so replaying the
granted scope would bake that drop in permanently. Only the CLI reads the key — it is excluded from
`BfabricClientConfig` and not plumbed through `ConfigData` / `export_config_data`.

A re-login **merges** into an existing environment section rather than replacing it, so hand-written
keys (`application_ids`, `engine`, `job_notification_emails`, …) survive. The auth-owned keys
(`login`, `password`, `pat`, `auth_method`, `client_id`, `scope`) are replaced wholesale, so a stale
`pat` cannot outlive the auth method that wrote it and be resurrected by `gather_auth`.

For PAT (Personal Access Token) logins the token is stored inline under `pat` (with
`auth_method: pat`), never as `login: __oauth__` / `password: <token>`:

```yaml
PRODUCTION:
  base_url: "https://bfabric.example.com/bfabric"
  auth_method: "pat"
  pat: "<token>"
```

**Backward-compatibility contract.** A PAT is not 32 characters, and a ≤1.19.0 client
validates *every* environment eagerly while enforcing an exactly-32-character password — so an
inline `login: __oauth__` / `password: <PAT>` environment would poison the whole shared
`~/.bfabricpy.yml` for those clients. Storing the token under `pat` (no `login`/`password`)
means old clients silently ignore it and keep reading the rest of the file; no fleet-wide
upgrade is required. The reader still accepts the legacy `login: __oauth__` shape written by
`1.20.0rc1`.

### New: `config_writer.py`

`write_environment_to_config()` — creates or updates a YAML environment section with atomic writes (0o600 permissions). Used by all login commands.

### `ConfigData` / `EnvironmentConfig`

Both models gained `auth_method` (`"password"` | `"oauth"` | `"pat"`) and `client_id` fields. `Bfabric.connect()` checks `auth_method == "oauth"` to route to `_connect_oauth_from_config()` (token loaded from the disk cache); `"pat"` and `"password"` environments carry their credential in the config and use the normal auth path.

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
