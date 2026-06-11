# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## \[Unreleased\]

### ⚠ Breaking Changes

- **SOAP token-validation path removed.** `create_bfabric_validator`, `create_mock_validator`,
  `BfabricUser`, and `SessionData` are deleted. OAuth 2.0 is now the only built-in authentication flow.
- **`BfabricAuthMiddleware` requires `client_id` and `client_secret`** as explicit keyword arguments
  (used to rebuild the user client on every request).
- **`AuthHooks.on_success` payload changed:** the second argument is now `context: UrlTokenContext`
  (OAuth entity claims) instead of `token_data: TokenData` (SOAP credentials).
- **Eviction (`on_evict`) is no longer invoked.** The eviction block (triggered when a different user
  re-lands in the same browser) is deferred to a follow-up change. Behavior change: app-set session keys
  from a prior user persist until explicit logout; `bfabric_session` itself is always overwritten on
  landing, so the authenticated identity is never stale.
- **Session shape changed.** The `bfabric_session` cookie key now contains
  `{base_url, token, context}` (OAuth) instead of `{bfabric_instance, bfabric_auth_login, …}` (SOAP).

### Added

- `create_mock_oauth_validator` — deterministic mock validator returning `OAuthExchangeSuccess` with a
  synthetic `UrlTokenContext`; `job_id` is stable across runs via `zlib.crc32`.
- `BfabricOAuthUser` — authenticated user object backed by an OAuth refresh-token session.
  Exposes `subject`, `base_url`, `entity_id`, `entity_class`, `application_id`, `job_id`, `display_name`,
  `identity`, and `get_bfabric_client()`.
- `OAuthSessionData` — minimal pydantic session model: `{base_url, token, context}`.
- `OAuthExchangeSuccess` — validation result carrying the full token dict and `UrlTokenContext`.
- Token refresh write-back: when the Bfabric client refreshes the access token during a request, the
  updated token is persisted to the encrypted session cookie before `http.response.start`.
- Re-exports `WebappOAuthSettings` / `OAuthClientCredentials` from `bfabric.experimental` for
  convenience.

### Changed

- Improved secret key example in README to use `secrets.token_urlsafe(64)` with a warning when generating random keys ([#434](https://github.com/fgcz/bfabricPy/issues/434))
- Fixed redirect URL scheme handling: protocol-relative URLs (//example.com) and absolute URLs with wrong scheme are now corrected based on X-Forwarded-Proto headers
- Honor `scope["root_path"]` when the app is mounted behind a reverse-proxy sub-path: landing/logout matching strips a leading `root_path` from `scope["path"]`, and root-relative redirect targets (e.g. `authenticated_path="/"`) are prefixed with `root_path` so the browser lands at the correct public URL

### Removed

- `create_bfabric_validator` / `bfabric_strategy.py` — SOAP token validation
- `create_mock_validator` / SOAP `mock_strategy.py` — SOAP mock validator
- `BfabricUser` — SOAP user class
- `SessionData` — SOAP session model
- `TokenValidationSuccess` — SOAP validation result
- `session_factory` / `user_factory` params from `BfabricAuthMiddleware.__init__`

## \[0.0.1\] - 2026-01-06

### Added

- Initial implementation of bfabric_asgi_auth.
