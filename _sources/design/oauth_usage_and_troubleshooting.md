# OAuth Usage & Troubleshooting

> **⚠️ EXPERIMENTAL / NOT OFFICIALLY SHIPPED.** The `bfabric._oauth` module and the
> `connect_pkce` / `connect_device_code` / `connect_oauth` factory methods are under active
> development (the asgi-auth OAuth migration is still in flight). APIs, defaults, and server-side
> scope enforcement may change. Do not treat this as stable public API yet.

A task-oriented companion to [OAuth Integration](oauth_integration.md): how to obtain a working
token from a `Bfabric` client via OAuth, and the non-obvious failure modes observed on
`fgcz-bfabric-demo`. For the architecture and module layout, see the integration doc.

---

## 1. Which token do I actually have?

An OAuth-connected client exposes its **access token** (a JWT) through the `auth` property.
Every read runs the credential provider, which refreshes first if the access token is near expiry:

```python
jwt = client.auth.password.get_secret_value()  # the OAuth access token, always fresh
```

- `client.auth` → `OAuthCredentialProvider.get_auth()` → `BfabricAuth(login="__oauth__", password=<jwt>)`.
- `.password` is a `SecretStr`; `.get_secret_value()` unwraps it.
- **Do not cache the string** — read it at point of use so you benefit from auto-refresh.

### access_token vs id_token — do not confuse them

Both are JWTs in the OIDC token response, but they are for different audiences:

| | access_token | id_token |
|---|---|---|
| `aud` | `bfabric-api` (the resource server) | `<client_id>`, e.g. `bfabric-cli` |
| purpose | authorize API / resource-server calls | tell *your app* who the user is |
| send to a resource server (API, file/download)? | **yes** | **no — it will be rejected** |
| tell-tale claims | `scope`, `jti`, `containers` | `at_hash`, `name`, `email`, `given_name` |

**`client.auth.password` gives you the access token — that is the one to send to servers.**
The id_token is *never* the right thing to hand to the file/download server; its `aud` is the
client, so the resource server refuses it.

---

## 2. Discovery: find endpoints and supported scopes per instance

Every B-Fabric instance publishes an OpenID Connect discovery document:

```
{base_url}/.well-known/openid-configuration
```

e.g. `https://fgcz-bfabric-demo.uzh.ch/bfabric/.well-known/openid-configuration`

It lists `token_endpoint`, `authorization_endpoint`, `jwks_uri`, `introspection_endpoint`,
`grant_types_supported`, and — crucially — **`scopes_supported`**. On the demo instance that is:

```
openid, profile, email, api:read, api:write, tus, download, groups, containers, employee
```

Use this to see which scopes an instance offers before requesting them. `token_endpoint` is
`{base_url}/rest/oauth/token`.

---

## 3. Choosing a connect method

| Method | Grant | Identity | When |
|--------|-------|----------|------|
| `Bfabric.connect_oauth(client_id, client_secret, base_url, scope=…)` | client_credentials | **service** (no user `sub`) | background jobs, servers |
| `Bfabric.connect_pkce(base_url, client_id=…, scope=…, port=…)` | authorization_code + PKCE | **user** | interactive, local machine |
| `Bfabric.connect_device_code(base_url, client_id=…, scope=…)` | device_code | **user** | headless / remote / notebooks |

Key identity difference: **client_credentials tokens carry no user `sub` and no user-scoped claims
like `containers`.** If a resource server authorizes by *your* container membership, a service
token won't do — you need a user flow (PKCE or device code).

The core `Bfabric` OAuth methods take `client_id` and `scope` as **required** arguments — there is
no baked-in default. The `bfabric-cli` login commands (`auth login` / `auth device-code`) likewise
**require** an explicit `--scope`: pick a named preset — `read-only` (`api:read`), `read-write`
(`api:write`, which implies `api:read`), or `upload` (`api:write tus`) — or pass any scope string.
These login presets are **minimal API scopes** — they do **not** include `groups` (the employee
file-access path, see below) or the OIDC scopes, so request those explicitly when you need them.
Client/webapp registration (`auth register` / `auth register-webapp`) keeps the broader
OIDC-inclusive default.

---

## 4. Scopes and claims that gate resource access

Resource servers gate on *claims*, and claims come from *scopes the client is authorized for*.
File/download access is authorized by **container membership**, which a token can convey two ways:

- the **`containers` claim** — an explicit list of container IDs, e.g. `["22", "300", "403"]`; or
- the **`groups` claim** — group membership. **For an employee, the `groups` claim (which includes
  the `employee` group) grants file access** without needing per-container IDs.

> **Employees: request the `groups` scope — this is the practical PKCE path.**
> The **`containers` scope cannot be requested via PKCE** (it is restricted; the server silently
> drops it — which is exactly why requesting `containers` in an interactive flow yields a token
> *without* the claim and no error). **`groups`, however, is requestable.** It is **not** part of
> the CLI's login presets (those are minimal API scopes), so pass it explicitly to get file access
> from a normal user flow:
>
> ```python
> client = Bfabric.connect_pkce(
>     "https://fgcz-bfabric-demo.uzh.ch/bfabric",
>     client_id="CLI",
>     scope="openid profile email api:read api:write groups",
> )
> ```
>
> This works with the default `bfabric-cli` client — no dedicated client needed.

Other notes:

- **A server only grants scopes the client is registered for; others are silently dropped** with no
  error. `bfabric-cli` is authorized for `groups` but **not** for `containers`.
- Non-employees who need specific containers rely on the **`containers` claim**, which (since it's
  not PKCE-requestable) must be supplied another way — e.g. a client configured with **"Always
  Include Claims → containers"**, which injects it regardless of requested scope. This is why a
  working token can carry `containers` even though its `scope` string doesn't list it.
- The `download` scope exists but was **not** required for file access in testing — the
  discriminator was container membership (`groups` for employees, else `containers`), not `download`.

### Diagnostic: decode a token locally

Do **not** paste live tokens into jwt.io. Decode locally:

```python
import base64, json


def claims(jwt):
    p = jwt.split(".")[1]
    p += "=" * (-len(p) % 4)
    return json.loads(base64.urlsafe_b64decode(p))


c = claims(client.auth.password.get_secret_value())
print(c.get("aud"), c.get("scope"), c.get("containers"))
```

Compare a working token against a failing one — the differing claim (`aud`, `scope`, `containers`)
is the cause.

---

## 5. PKCE mechanics and gotchas

`connect_pkce` → `pkce_login`:

1. Binds a local HTTP server on `127.0.0.1:{port}` (`port=0` ⇒ OS picks a random free port).
2. Opens the browser to `{base_url}/rest/oauth/authorize`.
3. **Blocks** (`server_thread.join(timeout)`, default 120 s) until the browser redirects back.
4. Catches `?code=…` on the callback, then POSTs to the token endpoint to exchange it.

### It is blocking, but can feel instant
The call blocks until the redirect arrives. If your browser already has an active B-Fabric session
(and the client has consent skipped), `/authorize` redirects back immediately with no login/consent
UI, so the whole thing completes in a fraction of a second and *looks* non-blocking. Logged out,
you'd see the cell hang on the login page.

### Redirect URI must match exactly — `127.0.0.1`, not `localhost`, and the right port
`pkce_login` builds its redirect as `http://127.0.0.1:{port}/callback`. If you register a fixed
redirect URI on the OAuth client, it must be **`http://127.0.0.1:8000/callback`** (127.0.0.1, not
`localhost`) and you must call `connect_pkce(..., port=8000)` so the port matches. With `port=0` the
port is random and cannot match a fixed registration.

### Loopback redirect fails on remote/hosted notebooks
The callback server listens on the *notebook host's* `127.0.0.1`. If the browser runs on a different
machine (a remote/hosted marimo, Jupyter on a server, SSH), the redirect to `127.0.0.1` hits the
*user's* machine where nothing is listening, so the code is never caught and PKCE times out.
**On remote hosts use `connect_device_code` instead** — it needs no callback server (you get a URL +
code and the process polls the token endpoint). On a truly local notebook, PKCE works.

### `connect_pkce` only supports **public** clients (tentative on the 401 cause)
`_exchange_code` sends only `client_id` + PKCE `code_verifier` at the token endpoint — **no
`client_secret`**. So it works with *public* clients (like `bfabric-cli`) but not with a
**confidential** client that has a secret and requires client authentication.

> **Observed but not fully root-caused:** a freshly UI-created (confidential) client failed the
> code→token exchange with **HTTP 401** at `/rest/oauth/token`, *after* the browser/redirect half
> succeeded. A 401 there is consistent with `invalid_client` (confidential client needs a secret,
> which `connect_pkce` never sends) — but it is also consistent with `unauthorized_client` (the
> client isn't allowed the `authorization_code` grant). The discriminator is the OAuth `error` field
> in the 401 body, which bfabricPy does not currently log. To capture it, temporarily print the
> token-endpoint response instead of calling `raise_for_status()`.

### Reactive-notebook caveat
`connect_pkce` runs the full browser round-trip on **every** call — it does not load-and-skip from a
cache (the `token_cache_path` cache is only used for *refresh after* login). In a reactive notebook
(marimo), re-running that cell re-triggers auth. Silent/fast when the session is warm, but it is a
real round-trip. Isolate that cell or cache the token yourself if it becomes annoying.

---

## 6. Refreshing tokens manually (rarely needed)

The provider auto-refreshes the **access token** based on the access token's own expiry. If you need
a fresh token out of band (e.g. an id_token whose expiry the provider does *not* track), drive the
refresh grant directly:

```python
provider = client._credential_provider
with provider._lock:
    session = provider._session
    fresh = session.refresh_token(
        provider._token_url, refresh_token=session.token["refresh_token"]
    )
    provider._persist()
```

If `"id_token" not in fresh` the server didn't re-issue one; if you get `invalid_grant` the refresh
token expired — either way, re-run the interactive login. `_credential_provider` / `_session` are
private and may change.

---

## 7. Quick decision tree

- **Need a token for the SOAP/REST API only?** Any flow works; `client.auth.password.get_secret_value()`.
- **Need to download files / hit a resource server as an employee?** Use a user flow
  (`connect_pkce`/`connect_device_code`) and request the **`groups` scope** — works with the default
  `bfabric-cli` client. (`containers` is *not* PKCE-requestable; `groups` is, and employee group
  membership grants file access.)
- **Need specific containers as a non-employee?** You need the **`containers` claim**, which isn't
  PKCE-requestable — it must come from a client with "Always Include Claims: containers".
- **On a remote host / notebook?** `connect_device_code`, not `connect_pkce`.
- **Getting HTTP 401 at `/rest/oauth/token` after login?** Check the client's grant types
  (`authorization_code` + `refresh_token` enabled?) and whether it's confidential (has a secret →
  `connect_pkce` can't authenticate it). Capture the OAuth `error` body to be sure.
- **Token works for API but not files?** Decode it — no container access (missing `groups` for an
  employee, else missing `containers`), or you're sending the id_token (`aud != bfabric-api`).
