# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## \[Unreleased\]

### Changed

- Improved secret key example in README to use `secrets.token_urlsafe(64)` with a warning when generating random keys ([#434](https://github.com/fgcz/bfabricPy/issues/434))
- Fixed redirect URL scheme handling: protocol-relative URLs (//example.com) and absolute URLs with wrong scheme are now corrected based on X-Forwarded-Proto headers
- Honor `scope["root_path"]` when the app is mounted behind a reverse-proxy sub-path: landing/logout matching strips a leading `root_path` from `scope["path"]`, and root-relative redirect targets (e.g. `authenticated_path="/"`) are prefixed with `root_path` so the browser lands at the correct public URL

## \[0.0.1\] - 2026-01-06

### Added

- Initial implementation of bfabric_asgi_auth.
