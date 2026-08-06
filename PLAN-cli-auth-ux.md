# `bfabric-cli auth` — UX redesign and implementation plan

> **Temporary file.** This document is committed so the design can be reviewed before any code is
> written. It is removed by the time this PR is ready to merge: part 1 and part 2 (the problem and the
> decisions) are folded into `bfabric/docs/design/cli_auth_ux.md`, and part 3 becomes the commits.

**Scope:** one PR touching `bfabric` and `bfabric_scripts`.
**Status:** design agreed, ready to implement. Review feedback on #573 folded in (§2.2 no back-compat
scaffolding, §2.9 no server-side revocation).

This document is self-contained: part 1 is the problem and the decisions with their justification,
part 2 is the implementation, part 3 is how to verify it. All file references are relative to the
bfabricPy repo root.

---

# Part 1 — Why

## 1.1 The complaint

`bfabric-cli auth` shipped in `bfabric_scripts 1.16.0` (2026-08-03) and is still marked EXPERIMENTAL
in `bfabric/docs/design/oauth_usage_and_troubleshooting.md`. The practical annoyance is simple:

> when a token expires you must re-run the login with the base URL and the scope typed out again

— exactly as in the pre-OAuth world, which OAuth was meant to improve on.

## 1.2 The structural issue underneath it

The CLI serves **two modes of operation** that were never distinguished:

| | Mode A — default user | Mode B — power user |
|---|---|---|
| instances | one | several |
| logins per instance | one | several (different scopes / accounts) |
| wants | never to think about env names | to name, list, and switch deliberately |

Today's CLI is **parameterised** like Mode B — every login takes `base_url`, `--config-env`,
`--scope`, `--client-id` — but **falls back** like Mode A: omitting `--config-env` silently targets
whatever env is currently the default. That combination is why both modes feel wrong. Mode A users
are asked for things they have no mental model for; Mode B users get silent, un-prompted writes to
the wrong environment.

## 1.3 Root cause of the retype

A config env is the unit of identity, but it stores only **half a login**:

| a login needs | stored in the env today? |
|---|---|
| `base_url` | yes |
| `client_id` | yes |
| `auth_method` | yes |
| **`scope`** | **no — written nowhere durable** |
| **flow (pkce / device-code)** | **no** |

`bfabric_scripts/src/bfabric_scripts/cli/login/oauth_login.py:52` writes only
`{"base_url", "auth_method", "client_id"}`. A login therefore cannot be replayed from disk, and
`cmd_auth_login` compensates by demanding the missing pieces every time. Three independent causes:

1. **`base_url` is a required positional with zero fallback.** Nothing in `cmd_auth_login` or
   `_resolve_params` reads the target env's recorded `base_url`, even though `--config-env` names an
   env where it already sits. Contrast `cmd_login_register` (`register.py:94-98`), which *does* infer it.
2. **`scope` has no fallback.** `resolve_scope` (`_common.py:55-78`) expands presets or prompts, and
   returns `None` non-interactively. Yet the cached token carries the authoritative *granted* scope,
   and `auth status` already prints it (`manage.py:195`). The data is on disk and unused.
3. **Re-login is env-agnostic by default.** Omitting `--config-env` non-interactively resolves to the
   current default (else the literal `"PRODUCTION"`, `_common.py:22,40-43`), so a re-login can land in
   a different env — and therefore a different token-cache key — than the one that expired.

## 1.4 Two landmines found while tracing this

Both are pre-existing, and both get **more** dangerous under a design that encourages frequent
zero-argument re-login. They are prerequisites, not nice-to-haves.

- **A re-login can silently repoint an environment.** `auth login <url>` with no `--config-env`
  overwrites the current default env *including its `base_url`*. This is currently pinned by a test
  (`tests/bfabric_scripts/cli/login/test_cmd_auth_login.py:93-109`). A power user can point
  `PRODUCTION` at a test host without being asked.
- **A re-login silently drops hand-written env keys.** `write_environment_to_config` replaces the env
  wholesale (`config_writer.py:90`: `existing[env_name] = dict(env_data)`), and the CLI supplies only
  three keys. Logging into an env that had `application_ids`, `job_notification_emails`, or `engine`
  **destroys them**.

---

# Part 2 — Decisions

Each decision below is settled. The reasoning is recorded because several of them look
counter-intuitive without it.

## 2.1 The env records the *requested* scope; login becomes zero-argument

```yaml
fgcz-prod:
  base_url: https://fgcz-bfabric.uzh.ch/bfabric
  auth_method: oauth
  client_id: CLI
  scope: api:write tus        # new — the scope that was *requested*
```

`bfabric-cli login` with no arguments then resolves everything from the target env and prompts for
nothing.

**Safe for old clients.** `EnvironmentConfig.gather_config` (`config_file.py:36-40`) sweeps unknown
keys into `BfabricClientConfig`, which uses pydantic's default `extra="ignore"`. A ≤1.20 client
ignores the new key. This is *not* the PAT hazard (`pat.py:44-46`), where the poison was a **value**
failing the 32-char password rule, not an unknown key.

**Is the YAML key necessary, or could scope be inferred?** It *can* be inferred from the local token
cache, in descending reliability: the cache's own `scope` key (present in 3 of 5 caches on the dev
machine), then the JWT access token's `scope` claim (present in all 3 that carry a JWT), absent
entirely in the other 2 (opaque, non-JWT access tokens). So the key is a deliberate choice. Three
reasons it is the right one:

- **Requested ≠ granted, and only the requested value is intent.** The server silently drops scopes
  the client isn't registered for. The cache records the *granted* scope, so replaying it bakes the
  drop in permanently — if the `CLI` client later gets registered for `groups`, a cache-derived
  re-login would never ask for it again. Storing the requested scope keeps intent separate from
  outcome, and having both is what makes the scope-drift check (§2.8) possible at all.
- **Durability.** `~/.bfabric/tokens` is a cache; the YAML is configuration. Clearing the cache would
  otherwise lose the login recipe.
- **Coverage.** 2 of 5 local caches carry no scope in any form.

**Envs written by 1.16.0** have no `scope` key, so the first re-login prompts once and records the
answer. No cached-scope fallback: it would contradict the first bullet above (replaying the granted
scope bakes in a silent server drop), and per §2.2 a 3-day-old feature does not get an upgrade shim
for a one-time prompt. The cached granted scope is still read — but only to *display* the drift
(§2.8), never to seed the request.

## 2.2 `auth default` → `auth activate`

"default" names config state; "activate" names the action. Straight rename, **no deprecated alias** —
`auth` is 3 days old and marked EXPERIMENTAL, so there is no install base to carry (review, #573).

This is a general rule for this PR, not a one-off: **no back-compat scaffolding for a feature this
young.** It also removes the cached-scope upgrade path (§2.1) and, for a different reason, the
revocation branch (§2.9). The one thing that *is* kept is tolerance for data already written to
users' disks by 1.16.0 — envs with no `scope` key, non-JWT tokens in the cache — because that is not
a compatibility shim, it is input that genuinely exists.

## 2.3 Top-level `login` only

`bfabric-cli login` as an alias of `auth login`. Everything else stays under `auth` — no second
spelling of a destructive command, no duplicated group.

## 2.4 Ship a known-instance list

Four hosts, **advisory not restrictive** (any URL is still accepted). Used for the first-login picker,
for canonicalising a bare host, and for suggesting an env name.

| name | base_url |
|---|---|
| `fgcz-prod` | `https://fgcz-bfabric.uzh.ch/bfabric` |
| `fgcz-test` | `https://fgcz-bfabric-test.uzh.ch/bfabric` |
| `fgcz-demo` | `https://fgcz-bfabric-demo.uzh.ch/bfabric` |
| `trace` | `https://trace.fgcz.uzh.ch/bfabric` |

Lives in `bfabric_scripts/.../cli/login/_instances.py`, next to `DEFAULT_CLIENT_ID` — this is CLI
policy, not core-library policy.

## 2.5 Identity display needs no scope change

Checked empirically against the local token cache: every access token is a JWT carrying `sub`, `iss`,
`aud`, `client_id`, `exp`, `scope` — *including* a cache whose scope is exactly `api:read` with no
`openid` and no `id_token`. That same cache is the control case proving the server does **not**
auto-grant `openid`: request `api:read`, get `api:read`.

So `auth list` / `auth status` should **decode the access-token payload locally** (display only, no
signature verification) rather than adding `openid` to the scope presets.

`sub` is a login name (e.g. `leonardoschwarz`), not an opaque numeric id, so it displays directly with
no API lookup. Bonus: `iss` carries the instance URL and `client_id` the client, so a cache can be
cross-checked against the env that claims it — useful, because the cache filename is an opaque hash
and nothing verifies the pairing today.

Caveat: two caches on the dev machine hold non-JWT access tokens (older server?), so the display must
degrade to "unknown" rather than raise.

## 2.6 Sanitise `base_url` *before* any network call

Today the only validation is a round-trip check at **write** time (`config_writer.py:39-49`) — i.e.
after the whole browser flow has already run. Worse, an `httpx.InvalidURL` from `_exchange_code` is
not a `RuntimeError`, so it escapes the `except RuntimeError` at `oauth_login.py:80`.

Instead: normalise deterministically (strip whitespace, default the scheme to `https://`, lowercase
the host, strip the trailing slash, reject non-http(s)), canonicalise against the instance list,
validate through `EnvironmentConfig` up front, then **pre-flight**
`GET {base_url}/.well-known/openid-configuration`, retrying once with `/bfabric` appended on 404.

The discovery endpoint is documented but used by no code. It is the only cheap check that catches the
likeliest typo — a host without the `/bfabric` path segment — and turns a two-minute browser dead end
into instant feedback.

## 2.7 One env resolver for all auth commands, and make the "why" visible

Today only `auth status` honours `BFABRICPY_CONFIG_ENV` (`manage.py:176`); `login`, `pat`, `default`,
`list`, and `logout` ignore it entirely, and none of them look at `BFABRICPY_CONFIG_OVERRIDE`.

- Every auth command resolves `--config-env` > `BFABRICPY_CONFIG_ENV` > `GENERAL.default_config`,
  matching `ConfigFile.get_selected_config_env` (`config_file.py:96-113`) and `Bfabric.connect()`.
- `BFABRICPY_CONFIG_OVERRIDE` set → mutating commands refuse with a clear message; `list` / `status`
  report that the config is pinned by it.
- `auth list` / `status` annotate *why* an env is active: `(default)` vs
  `(active via BFABRICPY_CONFIG_ENV)`. This kills the "I ran `auth activate X` and nothing changed"
  class of confusion, which is currently invisible.
- Fix a related dead end: an OAuth `BFABRICPY_CONFIG_OVERRIDE` without `env_name` computes its token
  cache key from the literal `"default"` (`bfabric.py:136`) — a name the config layer explicitly
  forbids (`config_file.py:87-94`), so it can never match a CLI-written cache. Error clearly instead.

## 2.8 Refuse to silently repoint; merge instead of replace

If an explicit `base_url` differs from the target env's recorded one, require confirmation or a new
env name. And make `write_environment_to_config` **merge** so unrelated keys survive a re-login.

Also print the scope being reused on every re-login. A user who once picked `read-only` must be able
to notice; and when the env's recorded (requested) scope and the cached token's granted scope
disagree, say so — that is the "server silently dropped a scope" case, detectable only *because* we
now store the requested value separately from the granted one.

## 2.9 Split `logout` from `remove`

Current behaviour: `auth logout` **deletes the whole environment** — config entry plus cached tokens
(`manage.py:213`).

Logging out on a shared machine is a **security affordance**, not a convenience, and those are judged
by discoverability rather than frequency. A rarely-used safety command needs to be *more* guessable,
not less, because nobody has it in muscle memory. If `logout` were renamed away, a user leaving a
shared machine would type `bfabric-cli auth logout`, get "unknown command", and plausibly just not log
out. So:

- **`auth logout [env]`** — remove credentials for this machine, keep the environment. Leaves a
  "configured but logged out" state, which is exactly what makes the zero-argument `login` work
  afterwards. Plus `auth logout --all`, since the point is to leave nothing behind without having to
  enumerate environments first.
- **`auth remove [env]`** — delete the environment entry as well. Housekeeping, Mode B.

**"Credentials" does not mean the same thing for every auth method** — this is the part that is easy
to get wrong:

| `auth_method` | secret location | what `logout` must do |
|---|---|---|
| `oauth` | `~/.bfabric/tokens/<hash>.json` | clear the token cache; the env keeps only non-secret `base_url` / `client_id` / `scope` |
| `pat` | **inline in the YAML** under `pat` (`pat.py:47-52`) | strip the `pat` key — there is no cache, so clearing one would be a silent no-op |
| `password` | **inline in the YAML** (`login` / `password`) | strip those keys |

A cache-only implementation would leave a PAT sitting in plaintext while reporting success.

**The teeth problem.** There is **no revocation support anywhere** in the codebase today — no RFC 7009
revoke endpoint, no `end_session`; only `authorize`, `token`, `device_authorization`, and `register`
are built. The client side is not the gap: **the B-Fabric server has no logout/revocation endpoint
either, and none is planned** — confirmed by Caushi on #573 ("i havent implemented the logout endpoint,
didnt seem so useful, if it is we can add it later in bfabric"). So deleting local state is *not*
revocation: the refresh token stays valid server-side until it expires.

Therefore `logout` states that unconditionally **in its own output**, not just in the docs: local
credentials removed, the token remains valid until expiry. Silence is the failure mode, because the
user has done the responsible thing and reasonably believes they are covered.

No `revoke_token` helper and no discovery lookup in `logout` — with no endpoint on either side that
is dead code guarding a branch that cannot be taken, and it would cost a network round-trip on every
logout to learn nothing. If B-Fabric later grows the endpoint, the change is small and local: swap the
unconditional message for a call plus a fallback. Getting revocation server-side is worth asking for
separately (it is the only thing that makes `logout` mean what users assume on a shared account), but
it is not this PR's dependency.

Note that the `0o600` file modes (`config_writer.py:31`, `token_cache.py`) protect against *other*
Unix users and are no help at all when "shared machine" means a shared account — a common reading at
FGCZ, and precisely the case where `logout` is the only control available.

## 2.10 Flow selection: hint, don't autodetect

The flow (pkce vs device-code) is the one thing that genuinely **cannot** be inferred from anything on
disk: both produce an identical token response, and the access-token claim set carries no `grant_type`
(verified: `aud, client_id, exp, iat, iss, jti, scope, sub`). So a zero-arg re-login on a headless box
needs *some* answer.

Storing `auth_flow` in the env was the first instinct and is wrong: **the flow is a property of where
you are running, not of the environment.** The same env is legitimately used from a laptop (pkce) and
over SSH (device-code), so a recorded flow would be wrong half the time for exactly the users who need
it.

The right question is not "is a browser available" but **"is the browser on the same host as the
loopback listener"** — PKCE requires them co-located.

`pkce.py:224-229` today detects `webbrowser.open` returning `False` and falls back to printing the
authorize URL. That is correct when the user is *local* without a browser (the loopback still works),
and a **trap** when they are remote: the URL prints, the user opens it on their laptop, and the
redirect to `127.0.0.1:{port}` cannot reach the listener on the remote host.

### Measured: `webbrowser.open()`'s return value is not a usable signal

Tested in Linux containers (`python:3.13-slim`) plus a macOS host:

| Environment | `webbrowser.get()` | `open()` | Correct? |
|---|---|---|---|
| Linux, no browser, no `DISPLAY` | raises | `False` | yes |
| Linux, `BROWSER=/nonexistent` | `GenericBrowser` | `False` | yes |
| Linux, GUI `firefox` + `DISPLAY=:0` | `Mozilla` | `True` | yes |
| **Linux, `w3m` installed, `TERM` set, no `DISPLAY`** | `GenericBrowser www-browser` | **`True`** | **no** |
| Linux, `w3m` installed, `TERM` unset | raises | `False` | yes |
| **macOS** | `MacOSXOSAScript` | `True` | **no** |

Two hard failures:

1. **Text browsers defeat it, loudly.** On headless Debian with a text browser installed and `TERM`
   set, `open()` returns `True` *and renders the page into the terminal* — the test run printed
   example.com's body into the shell. Mid-login that would fight the CLI's own prompts. This is gated
   on `TERM`, which is set in every interactive SSH session, so it is the realistic case.
2. **On macOS the return value is decoupled from whether a browser appeared.** `MacOSXOSAScript.open`
   pipes an `open location` AppleScript to `osascript` and returns true whenever `osascript` exits 0 —
   which it does even when the script silently opens nothing. So it cannot distinguish a local desktop
   session from SSH.

It is also **destructive to probe**: you only learn the answer by actually opening something.

Not theoretical — [cli/cli#13445](https://github.com/cli/cli/issues/13445) is the same bug in
`gh auth login`, naming `lynx` and `www-browser` specifically; the reporter's workaround was
`GH_BROWSER=/bin/true`. The loopback-on-remote failure more broadly is one of the most-reported auth
bugs in this class ([gemini-cli#27300](https://github.com/google-gemini/gemini-cli/issues/27300),
[codex#2798](https://github.com/openai/codex/issues/2798)).

### Decision

**Don't autodetect and don't change routing** — surface the information and let the user decide. This
is strictly smaller than a predicate and, unusually, also more robust: the measurements above are the
*justification for not building it* rather than a spec for it.

**One constraint that is easy to get wrong:** the hint must **not** be gated on the detection result.
In the w3m case `webbrowser.open` returns `True`, so anything hung off `if not browser_opened:` never
fires — and that is precisely the nastiest case. The hint has to be unconditional, or attached to the
timeout. Four small changes, none requiring detection:

1. Amend the fallback message (`pkce.py:229`), currently `"Open this URL to log in:"` with no caveat.
   Say the redirect goes to `127.0.0.1:{port}` on *this* machine.
2. Amend the timeout error (`pkce.py:238`), currently bare. This is where a stuck user actually looks,
   it fires for the w3m case too, and it costs nothing in the happy path.
3. Expose `--no-browser` on `auth login` — `open_browser` already exists through `pkce_login`
   (`pkce.py:185`) and `Bfabric.connect_pkce` (`bfabric.py:277`) and is tested; it is simply not wired
   to the CLI. Pure passthrough.
4. Document `BROWSER=/bin/true` as the ad-hoc escape hatch — stdlib `webbrowser` honours it, so this
   already works with zero code.

**Rejected alternative** (recorded as the fallback position if hints prove insufficient): a detection
predicate following gcloud's `ShouldLaunchBrowser` — probe non-destructively with `webbrowser.get()`,
reject blocklisted handler names, and on Linux require a compositor variable. It is well-grounded, and
the blocklist is even derivable rather than guessed (CPython registers exactly `www-browser`, `links`,
`elinks`, `lynx`, `w3m` behind an `if os.environ.get("TERM"):` branch). It was rejected because **it
cannot be finished**: macOS over SSH is not covered and gcloud has the same hole; SSH port forwarding
makes PKCE work remotely, so a confident predicate would sometimes force device-code on a user whose
setup worked; and the blocklist tracks CPython internals.

Note `is_interactive()` (`interactive.py:16-18`) is not a substitute in any variant — it is a
stdin/stdout TTY check and is `True` over SSH, so it says nothing about browsers.

## 2.11 The config env stays the unit of identity

Considered and rejected: normalising instances and logins into separate config sections (cleaner, but
the env concept must stay anyway for `BFABRICPY_CONFIG_ENV` compatibility, so it ends up as two
concepts where one worked); and fully implicit auto-named envs (ideal for Mode A, but Mode B loses
meaningful names like `prod-ro` vs `prod-rw`).

Resolution: **env = (instance, identity, scope) as today, with auto-derived names as the default
behaviour** — a Mode A user never invents an env name, while Mode B users still name things
deliberately. `auth list` groups by host so several envs on one instance read sensibly.

## 2.12 Resulting surface

Mode A, whole lifecycle:
```
bfabric-cli login          # first run: pick instance from list, pick scope, done
bfabric-cli login          # expired: zero arguments, zero prompts
bfabric-cli auth status
```

Mode B:
```
bfabric-cli auth login https://fgcz-bfabric-test.uzh.ch/bfabric --config-env test-rw --scope read-write
bfabric-cli auth list      # grouped by host: account (sub), scope, expiry, why-active
bfabric-cli auth activate test-rw
bfabric-cli login --config-env test-rw
```

---

# Part 3 — Implementation

Bottom-up: core `bfabric` primitives first (they are what the CLI is missing), then the CLI surface,
then docs. TDD per repo convention — failing test first.

## 3.1 Core — `bfabric`

### `config/config_file.py` — persist the requested scope (§2.1)

Add `scope: str | None = None` to `EnvironmentConfig` (beside `client_id`, ~`:27`), and add `"scope"`
to the `gather_config` exclusion list (`:39`) so it does not leak into `BfabricClientConfig`. Mirror
the existing pin at `tests/bfabric/config/test_config_file.py:247`.

Do **not** plumb `scope` through `ConfigData` / `export_config_data`. Only the CLI reads it, and it
reads the YAML directly via `ConfigFile`; adding it to the override JSON is unused surface.

### `config/config_writer.py` — merge instead of replace (§2.8)

Line 90 (`existing[env_name] = dict(env_data)`) becomes a merge that preserves unrelated keys but does
not leave stale credentials behind:

```python
_AUTH_OWNED_KEYS = frozenset(
    {"login", "password", "pat", "auth_method", "client_id", "scope"}
)
```

Merge = previous env minus `_AUTH_OWNED_KEYS`, then `dict(env_data)` on top. Dropping the auth-owned
set is load-bearing: a plain `dict | dict` merge would leave a stale `pat:` in an env re-logged-in via
OAuth, and `gather_auth` (`config_file.py:49`) would resurrect it despite `auth_method: oauth`.

Move `_validate_round_trip` to run on the **merged** mapping (still before any filesystem write, so a
rejected write leaves the file untouched). Pre-merge validation cannot see a combination the merge
itself creates.

### `config/config_writer.py` — credential-only removal (§2.9)

```python
def clear_environment_credentials(config_path: Path, env_name: str) -> tuple[str, ...]:
    """Strip inline secrets (``login`` / ``password`` / ``pat``) from an env, keeping it configured.

    Returns the keys that were removed, so the caller can report accurately.
    """
```

Read-modify-write in the style of the existing `remove_environment_from_config` (`:131`). Heed the
comment at `:115-117`: `ConfigFile`'s before-validators mutate their input, so validate on a deep copy
and write from the pristine dict.

### `_oauth/discovery.py` — new (§2.6)

```text
DISCOVERY_PATH = ".well-known/openid-configuration"

def fetch_discovery_document(base_url: str, *, timeout: float = 10.0) -> dict[str, object] | None
def resolve_base_url(base_url: str, *, timeout: float = 10.0) -> str
```

- `fetch_discovery_document` returns `None` on any transport error / non-200 / non-JSON. **Never
  raises** — a pre-flight that fails closed would make the CLI unusable behind a flaky network.
- `resolve_base_url` tries `base_url`, retries once with `/bfabric` appended on 404, returns whichever
  worked, else raises `BfabricOAuthError` naming both attempts.

Two functions only: the module is justified by the base_url pre-flight alone, and per §2.9 there is no
`revoke_token` to write.

Export from `_oauth/__init__.py`.

### `_oauth/pkce.py` — remote-host hints (§2.10)

- `:229` fallback message — keep the literal prefix `"Open this URL to log in:"` (two tests pin it:
  `tests/bfabric/oauth/test_pkce.py:295`, `:314`) and append that the redirect targets
  `{server.redirect_uri}` **on this machine**, so a browser elsewhere cannot complete it.
- `:238` timeout error — name the likely cause and the fix (`auth device-code` on a remote host). The
  existing test matches only `"timed out"`, so appending is safe.

No core change needed for `open_browser`; it already exists and only needs CLI wiring.

### `bfabric.py:136` — cache-key dead end (§2.7)

Replace `env_name = config_data.env_name or "default"` with a clear error naming
`BFABRICPY_CONFIG_OVERRIDE` and the missing `env_name`. Also fix the stale docstring at `:124` — it
says "keyed on `base_url` + `client_id`", but the key is `(base_url, client_id, env_name)`.

### Core tests

- `test_config_file.py` — `scope` binds; `scope` absent from `config`.
- `test_config_writer.py` — **revisit `test_overwrites_existing_env` (`:65`) deliberately**; it
  currently encodes replace. Add: unrelated keys (`application_ids`, `engine`) survive a re-login; a
  `pat` env re-logged-in as OAuth has no `pat` key left; `clear_environment_credentials` strips `pat`
  and leaves `base_url` / `client_id` / `scope`.
- `tests/bfabric/oauth/test_discovery.py` (new) — 200; 404-then-`/bfabric`; both-404 raises; transport
  error returns `None`.
- `test_pkce.py` — assert both new hints, and close the weak spot at `:298`, where
  `test_open_browser_false_prints_url` never asserts `webbrowser.open` was skipped.

## 3.2 CLI — `bfabric_scripts`

All paths below are under `bfabric_scripts/src/bfabric_scripts/cli/`.

### `login/_instances.py` — new (§2.4)

The four instances above, plus `match_instance(base_url) -> Instance | None` and
`suggest_env_name(base_url) -> str`.

### `login/_identity.py` — new (§2.5)

```text
def decode_jwt_payload(token: str) -> dict[str, object] | None   # base64url, no signature check
def describe_identity(cached: dict[str, object] | None) -> str   # "leonardoschwarz" | "unknown"
```

Display only — explicitly **not** verification; `verify_jwt` in `_oauth/url_token.py` remains the only
place that validates. Both functions degrade to `None` / `"unknown"` on an opaque token rather than
raising.

### `login/_common.py` — shared resolution (§2.6, §2.7)

- **`resolve_config_env`** — insert `BFABRICPY_CONFIG_ENV` between explicit and
  `GENERAL.default_config`.
- **`normalize_base_url(raw) -> str`** (new) — deterministic and offline, then canonicalised against
  `KNOWN_INSTANCES`.
- **`resolve_base_url(explicit, env, ...)`** (new) — explicit > the env's recorded `base_url` >
  first-login instance picker.
- **`resolve_scope`** — becomes the fallback chain explicit → env-recorded → prompt (§2.1: no
  cached-granted step). Keep returning `None` non-interactively when nothing resolves;
  `test_login_common.py:73-76` pins that there is no baked-in default, and that stays true.
- **`require_mutable_config()`** (new) — mutating commands refuse when `BFABRICPY_CONFIG_OVERRIDE` is
  set, with a message naming the variable.
- **`describe_active_reason(...)`** (new) — `(default)` / `(active via BFABRICPY_CONFIG_ENV)` /
  `(config pinned by BFABRICPY_CONFIG_OVERRIDE)`.

### `login/oauth_login.py` — zero-argument login (§2.1, §2.6, §2.8, §2.10)

- `base_url` becomes `str | None = None` (still positional).
- `_resolve_params` order: env → base_url → scope → set_default. Pre-flight the resolved base_url
  through `discovery.resolve_base_url` **before** starting the browser flow.
- Refuse to silently repoint: if an explicit `base_url` differs from the env's recorded one, require
  confirmation or a different `--config-env`; refuse non-interactively. This deliberately changes the
  behaviour pinned by `test_cmd_auth_login.py:93-109`.
- `_persist` (`:42-55`) gains `scope` and writes `"scope": scope`.
- Print the scope being reused, and flag requested-vs-granted disagreement.
- Add `--no-browser`, pure passthrough to `pkce_login(open_browser=...)`.
- `cmd_login_device_code` shares `_resolve_params`, so it inherits all of the above.

### `login/manage.py` — logout/remove split, activate rename, display (§2.2, §2.5, §2.7, §2.9)

- `cmd_auth_default` → `cmd_auth_activate` (rename, no alias left behind).
- `auth logout` — credential removal per auth method (table in §2.9), `--all`, and the unconditional
  "the token stays valid server-side until it expires" statement.
- `auth remove` — today's destructive behaviour, renamed from `cmd_login_logout`.
- `auth list` / `auth status` — account (`sub`), scope, expiry, why-active; `list` grouped by host.
- Fix the hardcoded `'bfabric-cli auth default <env>'` string at `:267`.
- Naming cleanup, vestigial from the `auth pkce` → `auth login` rename (#561): six of nine handlers
  are `cmd_login_*` and two are `cmd_auth_*`, so grepping for either word finds only part of the
  surface. Normalise to `cmd_auth_*`. Module filenames stay — renaming those is churn without payoff.

### `cli_auth.py`, `__main__.py` — wiring (§2.2, §2.3)

```python
_ = cmd_auth.command(cmd_auth_activate, name="activate")
_ = cmd_auth.command(cmd_auth_remove, name="remove")
...
_ = app.command(cmd_auth_login, name="login")  # __main__.py — top-level alias
```

`default` is simply gone (§2.2), so nothing here needs cyclopts' `show=False` and the repo keeps having
no hidden-alias precedent. One thing to note while wiring: **no test exercises `cli_auth.py`'s command
wiring at all**. Add a smoke test that every registered name resolves — and that `default` no longer
does.

### CLI tests

New: `test_login_instances.py`, `test_login_identity.py` (JWT and opaque paths),
`test_cmd_auth_logout.py`, plus the wiring smoke test.
Renamed: `test_cmd_login_logout.py` → `test_cmd_auth_remove.py`; `test_cmd_auth_default.py` →
`test_cmd_auth_activate.py`.

Characterisation tests for the headline fix:

1. Write an env with `base_url` + `scope`, delete the token cache, run `login` with no arguments —
   assert both recorded values reach `pkce_login` and nothing is prompted.
2. A 1.16.0-era env with **no** `scope` key — assert it prompts (and does *not* silently reuse the
   cached granted scope), and that the answer is written to the env so run 3 is prompt-free.
3. `logout` per auth method. The `pat` case is load-bearing: assert the `pat` key is gone from the
   YAML. A cache-only implementation would pass a naive "logout succeeded" test while leaving the
   token in plaintext. Also assert an OAuth `logout` *keeps* `base_url` / `client_id` / `scope`, so a
   following zero-arg `login` still works.

Existing pins to revisit **deliberately, not silence**: `test_cmd_auth_login.py:93-109`,
`test_login_common.py:73-76`, `test_login_constants.py:11-15` (presets are unchanged — should keep
passing), `test_cmd_login_pat.py:17-29` (old-client PAT format — must keep passing).

## 3.3 Docs

Docs are a real gap independent of the code: `auth` appears in **no** user guide.
`bfabric/docs/user_guides/bfabric-cli/index.md` omits it from both the command table and the toctree,
and `getting_started/configuration.md` never mentions `auth_method` / `oauth` / `pat` / `client_id`.

- **New** `bfabric/docs/user_guides/bfabric-cli/authentication.md` — the Mode A / Mode B lifecycles,
  the instance list, scope presets, `logout` vs `remove` — stating plainly that B-Fabric has no
  revocation endpoint, so `logout` clears local credentials only and the token stays valid until it
  expires (the shared-account case is where this matters) — and the
  remote-host guidance (`--no-browser`, `auth device-code`, `BROWSER=/bin/true`). Register it in the
  index table and toctree.
- `bfabric/docs/design/oauth_integration.md:42-70` — the CLI table is stale twice over: it points
  `auth status` and `auth logout` at `cli/login/status.py` and `cli/login/logout.py`, neither of which
  exists (both live in `manage.py`); it omits `default` / `list` / `register-webapp`; and its `logout`
  row describes the *old* token-only behaviour that this change is now actually implementing. Rewrite
  it, plus the config-file section for the new `scope` key.
- `bfabric/docs/design/oauth_usage_and_troubleshooting.md`, its "PKCE mechanics and gotchas" section —
  document `open_browser` / `--no-browser` and sharpen "loopback redirect fails on remote hosts", which
  the docs state today and no code acts on.
- `bfabric/docs/user_guides/bfabric-cli/workunits.md:150` — the only user-facing `auth` snippet in the
  repo is `bfabric-cli auth login --scope "api:write tus"`, which **fails today** because it omits the
  required base_url. The zero-arg redesign incidentally makes it correct; switch it to the `upload`
  preset.
- Changelogs — both `[Unreleased]` sections are currently empty. `bfabric/docs/changelog.md`: `scope`
  config key, writer merge, `clear_environment_credentials`, discovery module, PKCE hints.
  `bfabric_scripts/docs/changelog.md`: the command-surface changes, flagging the `logout` semantic
  change and `default` → `activate` as breaking — no deprecation window and no alias, justified by the
  EXPERIMENTAL marker and the 3-day-old release (§2.2).

---

# Part 4 — Verification

```bash
nox -s test_bfabric
nox -s test_bfabric_scripts
nox -s basedpyright\(bfabric\)
nox -s basedpyright\(bfabric_scripts\)
nox -s code_style
nox -s docs
```

Run each package's suite in a **separate** pytest invocation — tests have no `__init__.py`, so passing
multiple package trees to one invocation fails at collection with a basename clash. Per the repo rule:
fix code or add a targeted `# pyright: ignore[...]`, never edit `.basedpyright/baseline.*.json`.

Manual end-to-end against `fgcz-bfabric-demo.uzh.ch` (a fresh login is a browser flow, so this is a
human step):

1. `bfabric-cli login` from scratch — instance picker, scope picker, no env name invented.
2. Delete the token cache, then `bfabric-cli login` with **zero arguments** — no prompts, and the
   reused scope is printed.
3. `bfabric-cli auth list` with two envs on the same host — the account column disambiguates them.
4. `bfabric-cli auth logout`, then `bfabric-cli login` — the zero-arg re-login still works.
5. `bfabric-cli auth login fgcz-bfabric-demo.uzh.ch` (no scheme, no `/bfabric`) — normalisation and
   the discovery pre-flight correct it *before* the browser opens.

Flow selection (§2.10) needs no environment testing now that it is hint-only: assert the timeout error
and the fallback message carry the remote-host guidance, and that `--no-browser` reaches
`pkce_login(open_browser=False)`. The measurement table is justification for the decision, not a spec
to test against — its value is that skipping detection is an evidence-based choice rather than an
untested guess in either direction.

## Deliverable

One PR against `main`. Push with an explicit remote ref, e.g.
`git push -u origin HEAD:feature/cli-auth-ux`.
