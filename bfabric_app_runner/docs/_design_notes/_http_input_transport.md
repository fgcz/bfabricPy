# HTTP input transport

Opt-in HTTP transport for staging B-Fabric **resource** inputs, as an alternative to the SSH/rsync
default. Selected per-input via `BfabricResourceSpec.access: "ssh" | "http"` (default `ssh`).
Portable (works anywhere with web access, no SSH/NFS), but slower — an add-on, not a replacement.

## How it fits the pipeline

The existing **resolve → prepare** split is the seam. A new `FileSourceHttp` source type joins
`FileSourceSsh` / `FileSourceLocal` and flows through both phases (same source-type abstraction).

- **Resolve** (`inputs/resolve/_common.py:get_http_file_source`) builds the download URL. It is
  non-secret, so it is stored in `FileSourceHttp` and is safe to serialize into resolved inputs.
- **Prepare** (`inputs/prepare/prepare_resolved_file.py:_operation_copy_http`) streams the URL via
  httpx, checksum-verifies, and writes atomically (temp `.part` + rename).

To add another source type later: widen the source unions (`FileSpec.source`, `ResolvedFile.source`,
and — only if the transport supports directory staging — `ResolvedDirectory.source`), add a resolve
producer, and add a prepare op. `ResolvedDirectory.source` deliberately omits `FileSourceHttp` today
(directory-over-HTTP is unimplemented; archive specs resolve to SSH), so re-add it there together with
an end-to-end test when that lands. The `assert_never` guards in the prepare `match` statements make
the type-checker enumerate every site you must touch.

## How B-Fabric HTTP resource access works

This is the first use of the `access` endpoint in the codebase.

- `client.read("access", {"storageid": <storage id>, "type": "HTTP"})` returns access records with
  `protocol`, `host`, `basepath`.
- URL = `{protocol}://{host}{basepath}{relativepath}`, normalized to exactly one slash at the
  `basepath`/`relativepath` boundary (B-Fabric stores `relativepath` with a leading slash — mirror
  `Resource.storage_relative_path`, which `lstrip`s it for the SSH path).
- A storage may have no HTTP access record → resolve raises.
- The `access` field names follow the working reference notebook (`leo-scratch/20260702_01_demo.py`);
  they are **unverified against production** — confirm on the first live run.

## The token (deferred — the crux of finishing this)

- HTTP download needs an OAuth **access token** (not the id token), and that token must carry the
  **`containers` scope/claim**. The default `bfabric-cli` client scope does **not** include
  `containers`, so `Bfabric.connect_pkce(base_url)` with defaults yields a token that `403`s on the
  download. Request `containers` explicitly in the scope.
- The token only exists on an OAuth-backed client (`connect_pkce` / `connect_oauth`), where
  `client.auth.login == "__oauth__"` and `client.auth.password` is the JWT. A config-file
  (login+password) client has no JWT.
- Production input-prep runs as its own process on the compute node with a config-file client, so
  there is **no token there**. `access: http` is therefore inert in production until a token-delivery
  mechanism exists; it fails loud rather than mis-authenticating.
- PKCE is a public-client + loopback-redirect flow only.

## Trust boundary (security)

- The OAuth token is sent **only** to storage-derived URLs. `auth` on `FileSourceHttp` gates
  token-sending; it is set `"bfabric"` only by `get_http_file_source` (trusted) and rejected outright
  for user-authored `file` specs by `FileSpec.validate_no_user_supplied_auth`, which runs on every
  `FileSpec` construction — so an `auth` hand-written in an `inputs.yml` fails validation instead of
  being silently dropped, and can never reach a resolver, let alone send the token to an arbitrary
  host. It is an enum (not a bool) so future credential schemes slot in without a wire-format change.
- Invariant: the 32-char web-service password is never sent as a bearer (only send when
  `login == "__oauth__"`).
- httpx strips `Authorization` on cross-origin redirects (defense in depth), covered by
  `test_operation_copy_http_strips_auth_on_cross_origin_redirect`.

## Follow-ups (not implemented)

- Deliver a `containers`-scoped token to compute-node runs (env var / external-job token / OAuth on
  the node). Until then `access: http` needs an interactive/OAuth session.
- The token is resolved once per prepare and reused; a long multi-file batch could hit token expiry
  mid-run — upgrade to a token-provider callable if that becomes real.
- HTTP is wired for `bfabric_resource` only; `bfabric_resource_archive` / `bfabric_resource_dataset`
  still resolve to SSH.

## Dev-environment gotchas (bfabricPy)

- The workspace venv may resolve to Python 3.14, where `pandera` breaks unrelated `dispatch` tests.
  Run app_runner tests with `--python 3.13` (or via `nox`) to avoid false failures.
- Run `basedpyright` via its `nox` session (isolated env), not the workspace venv.
- The `HasOne` relationship descriptor (`bfabric/entities/core/has_one.py`) has a `__get__` typing
  quirk that makes any `resource.storage` access a (baselined) `reportAttributeAccessIssue`; a new
  access needs a `cast(...)` plus a targeted `# pyright: ignore[reportAttributeAccessIssue]`.
