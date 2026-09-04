# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Require `starlette>=1.0.1,<2` (was `>=0.50.0,<1`) to keep starlette above the advisory floor ([#505](https://github.com/fgcz/bfabricPy/issues/505)).
- The README's secret key example uses `secrets.token_urlsafe(64)` and warns about generating random keys ([#434](https://github.com/fgcz/bfabricPy/issues/434)).
- `SessionData.bfabric_instance` is canonicalised to a `bfabric.BaseUrl` on construction, so `BfabricUser.instance` and `BfabricUser.get_bfabric_client().config.base_url` no longer end with a trailing slash and compare equal to a configured instance spelled either way.

### Fixed

- A token naming a non-http B-Fabric instance is reported as a failed validation instead of escaping `create_bfabric_validator` as an unhandled `ValueError`.
- Redirect URL scheme handling: protocol-relative URLs (`//example.com`) and absolute URLs with the wrong scheme are corrected from the `X-Forwarded-Proto` header.
- `scope["root_path"]` is honoured when the app is mounted behind a reverse-proxy sub-path: landing/logout matching strips a leading `root_path` from `scope["path"]`, and root-relative redirect targets (e.g. `authenticated_path="/"`) are prefixed with `root_path` so the browser lands at the correct public URL.

## [0.0.1] - 2026-01-06

### Added

- Initial implementation of bfabric_asgi_auth.
