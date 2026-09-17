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

`auth list` shows each environment's scope and token expiry, which is what tells two logins on the
same instance apart. Both commands also say *why* an environment is the active one, because
`BFABRICPY_CONFIG_ENV` silently outranks the configured default:

```
prod-ro   oauth · api:read · present, expires in ~7h  (default)
prod-rw   oauth · api:write · present, expires in ~7h  (active via BFABRICPY_CONFIG_ENV)
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
recorded in the config and a later login replays it. Note that the server silently drops scopes the
client is not registered for, so what you asked for is not necessarily what you got.

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
`logout` removes *local* access only — it does not revoke the token server-side, so a token that was
already issued stays valid until it expires. On a shared machine, treat that as the security boundary
you actually have.
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

## Unattended scripts and cron jobs

A browser login is wrong for a script that nobody is watching: its token expires and there is no one
to re-login. A **service account** authenticates from a stored secret instead, so it never expires
and needs no browser.

Register the client once (as an employee, with the instance you are logged in to):

```bash
bfabric-cli auth register "sysadmin-cron" "https://sysadmin-cron.invalid/unused" \
    --service-user svc-admin --save-env CRON
```

`--service-user svc-admin` is what enables the `client_credentials` grant, and it is also *whose*
account the client acts as: tokens it obtains carry that service user's identity and permissions, so
give it a B-Fabric user with exactly the access the script needs.

`--save-env CRON` records the new client, its secret, and the credentials needed to edit it later.

The redirect URI is a positional argument of `auth register` because the command also registers
interactive clients, where it is the `authorization_code` callback. A `client_credentials` client
never redirects, so the value is unused — pass any placeholder.

From then on every command works unattended:

```bash
bfabric-cli api update user 12345 computerloginenabled true --config-env CRON
```

If the client was created for you in the B-Fabric UI instead, record it by hand:

```bash
bfabric-cli auth service-account https://fgcz-bfabric.uzh.ch/bfabric --client-id sysadmin-cron
# Client secret: ‹prompted›
```

The secret is stored in `~/.bfabricpy.yml` (mode `0600`). Passing it with `--client-secret` works but
is visible in `ps` and your shell history.

```{note}
The token acts as the service user the client was registered with — not as you. What the script can
reach is that account's access, so a permission it is missing has to be granted to the service user
in B-Fabric. See [OAuth Usage & Troubleshooting](../../design/oauth_usage_and_troubleshooting.md).
```

### Rotating the secret

When the secret is rotated in the B-Fabric UI, store the new one by re-running the same command:

```bash
bfabric-cli auth service-account https://fgcz-bfabric.uzh.ch/bfabric \
    --client-id sysadmin-cron --config-env CRON
# Client secret: ‹paste the new secret›
```

There is nothing else to clear — this grant keeps no cached token, so the next command fetches a
fresh one. The environment's other recorded values are kept.

### Several instances

Each environment holds its own client and secret, so a script can address either instance by name:

```bash
bfabric-cli auth service-account https://fgcz-bfabric.uzh.ch/bfabric --client-id prod-cron --config-env PROD
bfabric-cli auth service-account https://fgcz-bfabric-test.uzh.ch/bfabric --client-id test-cron --config-env TEST

bfabric-cli api update user 12345 computerloginenabled true --config-env PROD
```

## Fixing a misconfigured client

A client registered with the wrong redirect URI can be corrected in place, using the registration
credentials that `--save-env` recorded:

```bash
bfabric-cli auth client-show   --config-env CRON     # what the server has
bfabric-cli auth client-update --config-env CRON --redirect-uri https://correct.example.com/callback
```

`client-update` can also change `--client-name` and `--scope`. B-Fabric issues a new secret and a new
registration token on every such edit; both are saved automatically, so repeated edits keep working.

```{important}
This changes the OAuth client only. A webapp registered with `auth register-webapp` also has the URL
in its B-Fabric *application* record (`weburl`), which this does not touch — update that separately
with `bfabric-cli api update application <id> weburl <url>`.
```

A client that is no longer needed can be revoked outright:

```bash
bfabric-cli auth client-delete --config-env CRON
```

It stops being able to obtain tokens and cannot be restored, so this asks for confirmation first
(`--no-confirm` to skip, which a script needs). The environment stays configured, minus the
credentials that died with the client.

Only a client registered through `--save-env` can be managed this way; the registration token is
issued once, at registration, and is not recoverable afterwards.

## Personal access tokens

For a non-interactive login without an OAuth flow:

```bash
bfabric-cli auth pat https://fgcz-bfabric.uzh.ch/bfabric
```

The token is prompted for and stored in `~/.bfabricpy.yml` (mode `0600`). Passing it with `--pat`
works but is visible in `ps` and your shell history.

## Environment variables

Every `auth` command honours `BFABRICPY_CONFIG_ENV` and `BFABRICPY_CONFIG_OVERRIDE` (see
[Configuration](../../getting_started/configuration.md)). Because the override replaces the config
file entirely, commands that would write to that file refuse to run while it is set rather than
writing a change that has no effect.
