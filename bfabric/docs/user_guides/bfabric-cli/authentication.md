# Authentication

`bfabric-cli auth` manages how the CLI logs in to B-Fabric and which instance it talks to.

## Logging in

```bash
bfabric-cli login
```

On a first run this asks which instance you want and which permissions to request, then stores the
result. The environment name is derived from the instance, so there is nothing to invent.

When the token expires, run the same command again — with no arguments:

```bash
bfabric-cli login
```

Everything the login needs (instance URL, client ID, scope) was recorded the first time, so there is
nothing to retype and nothing to answer. The scope being requested is printed, so a login is never
silently different from the one before it.

`bfabric-cli login` is a shortcut for `bfabric-cli auth login`; both do the same thing.

## Checking what you are logged in as

```bash
bfabric-cli auth status     # the active environment in detail
bfabric-cli auth list       # every environment, grouped by instance
```

`auth list` shows the account each cached token belongs to, its scope and expiry. That is what tells
two logins on the same instance apart — e.g. a read-only and a read-write environment on production.

Both commands also say *why* an environment is the active one. This matters because
`BFABRICPY_CONFIG_ENV` silently outranks the configured default:

```
prod-ro   oauth · someone · api:read · present, expires in ~7h  (default)
prod-rw   oauth · someone · api:write · present, expires in ~7h  (active via BFABRICPY_CONFIG_ENV)
```

## Scopes

A scope is the set of permissions the token carries. Pass a preset or a raw scope string:

| Preset | Scope | For |
| ------------ | --------------- | -------------------------------------------- |
| `read-only` | `api:read` | reading data |
| `read-write` | `api:write` | creating and updating (includes reading) |
| `upload` | `api:write tus` | uploading files (includes read and write) |

```bash
bfabric-cli auth login --scope upload
bfabric-cli auth login --scope "api:read containers"
```

There is no default scope: a non-interactive login must pass `--scope`. The requested scope is
recorded in the config, and a later login replays it.

The server drops scopes the client is not registered for, so what you asked for and what you got can
differ. `auth status` shows both when they do — the requested scope from the config, and the granted
scope from the token.

## Several instances or several logins

Name environments explicitly and switch between them:

```bash
bfabric-cli auth login https://fgcz-bfabric-test.uzh.ch/bfabric --config-env test-rw --scope read-write
bfabric-cli auth activate test-rw     # make it the default
bfabric-cli login --config-env test-rw
```

The CLI knows these instances, so a bare host expands to the full URL and the environment name is
suggested for you:

| Name | URL |
| ----------- | ------------------------------------------- |
| `fgcz-prod` | `https://fgcz-bfabric.uzh.ch/bfabric` |
| `fgcz-test` | `https://fgcz-bfabric-test.uzh.ch/bfabric` |
| `fgcz-demo` | `https://fgcz-bfabric-demo.uzh.ch/bfabric` |
| `trace` | `https://trace.fgcz.uzh.ch/bfabric` |

Any other URL works too — the list is a convenience, not a restriction.

Logging in with a URL that differs from the one an environment already has asks for confirmation
first, and refuses outright without a terminal. Repointing `PRODUCTION` at a test host is not
something to do by accident.

## Logging out vs removing

```bash
bfabric-cli auth logout            # drop credentials, keep the environment
bfabric-cli auth logout --all      # every environment
bfabric-cli auth remove test-rw    # delete the environment entirely
```

`logout` removes what is stored on this machine — the cached OAuth token, or an inline PAT or
password in `~/.bfabricpy.yml` — and keeps the environment configured. That leaves it ready for a
zero-argument `bfabric-cli login` later.

```{important}
B-Fabric has no token revocation endpoint, so `logout` removes *local* access only. A token that was
already issued stays valid server-side until it expires. On a shared machine, treat that as the
security boundary you actually have.
```

`remove` deletes the environment from the config as well. Use it for housekeeping, not for logging
out.

## Remote hosts and headless machines

The browser login finishes by redirecting to a local port, so the browser has to be on the *same
machine* as the CLI. Over SSH that cannot work, no matter which browser opens the URL. Use the device
code flow instead:

```bash
bfabric-cli auth device-code
```

It prints a code to enter in a browser anywhere, so nothing needs to reach back to the host. It is
zero-argument re-loginable in the same way as `auth login`.

Two smaller escape hatches for the browser flow:

- `bfabric-cli auth login --no-browser` prints the URL instead of trying to open one. Useful locally
  when no browser is configured — the redirect still reaches the CLI.
- `BROWSER=/bin/true bfabric-cli auth login` stops a *terminal* browser (`w3m`, `lynx`, …) from
  hijacking the login and rendering the page into your shell.

## Personal access tokens

For a non-interactive login without an OAuth flow:

```bash
bfabric-cli auth pat https://fgcz-bfabric.uzh.ch/bfabric
```

The token is prompted for and stored in `~/.bfabricpy.yml` (mode `0600`). Passing it with `--pat`
works but is visible in `ps` and your shell history.

## Environment variables

| Variable | Effect |
| --------------------------- | ---------------------------------------------------------------------- |
| `BFABRICPY_CONFIG_ENV` | Selects the environment, outranking the configured default |
| `BFABRICPY_CONFIG_OVERRIDE` | Supplies the whole config as JSON, ignoring the file |

Every `auth` command honours `BFABRICPY_CONFIG_ENV`. Because `BFABRICPY_CONFIG_OVERRIDE` replaces the
config file entirely, commands that would write to that file refuse to run while it is set rather
than writing a change that has no effect.
