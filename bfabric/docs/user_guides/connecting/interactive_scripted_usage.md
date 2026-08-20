# Interactive and Scripted Usage

This guide covers how to connect a `Bfabric` client in interactive sessions and scripts, where you control the
configuration directly through config files or environment variables.

## Log In Once, Connect From Code

Log in with the CLI:

```bash
bfabric-cli login
```

On a first run this asks which instance you want and which permissions to request, and stores both in
`~/.bfabricpy.yml`. Afterwards your scripts just connect:

```python
from bfabric import Bfabric

client = Bfabric.connect()
```

`connect()` sees `auth_method: oauth` in the selected environment, picks up the cached token and refreshes it when it
nears expiry — nothing OAuth-specific appears in your code. When the login itself expires, run `bfabric-cli login` again
with no arguments; everything it needs was recorded the first time.

See [CLI Authentication](../bfabric-cli/authentication.md) for scopes, working with several instances, and logging out.

## Choosing an Environment

`~/.bfabricpy.yml` can hold several environments (a production and a test instance, or two logins on the same instance
with different permissions). By default `connect()` uses `BFABRICPY_CONFIG_ENV` if it is set, otherwise the config
file's default environment. You can also name one explicitly:

```python
# Use the PRODUCTION environment
client = Bfabric.connect(config_file_env="PRODUCTION")

# Use the TEST environment
client = Bfabric.connect(config_file_env="TEST")
```

The `config_file_env` parameter takes precedence over the `BFABRICPY_CONFIG_ENV` environment variable. See the
[Configuration Guide](../../getting_started/configuration.md#priority-order) for the full priority order.

If your config file is in a non-standard location:

```python
from pathlib import Path

custom_config_path = Path("/path/to/custom/config.yml")
client = Bfabric.connect(
    config_file_path=custom_config_path, config_file_env="PRODUCTION"
)
```

## Logging In From Python

If you would rather not depend on the CLI having been run, you can perform the login from Python. Both flows take an
explicit `client_id` and `scope`, and both accept a `token_cache_path` that the resulting client refreshes against.

On a local machine, `connect_pkce()` opens your browser and waits for the redirect:

```python
from bfabric import Bfabric

client = Bfabric.connect_pkce(
    "https://fgcz-bfabric.uzh.ch/bfabric",
    client_id="CLI",
    scope="api:read",
)
```

On a remote host — SSH, a container, a hosted notebook — use `connect_device_code()` instead. It prints a code to enter
in a browser anywhere and polls for the result:

```python
client = Bfabric.connect_device_code(
    "https://fgcz-bfabric.uzh.ch/bfabric",
    client_id="CLI",
    scope="api:read",
)
```

Each call runs the login again — neither skips it by reading the cache — so keep them out of code that reruns often.

```{note}
The browser flow finishes by redirecting to a port on the machine running Python. If the browser is on a different
machine, nothing is listening there and the login times out — which is why remote hosts need the device code flow. See
[OAuth Usage & Troubleshooting](../../design/oauth_usage_and_troubleshooting.md) for the details.
```

## Personal Access Tokens

For a non-interactive login without any OAuth flow, use a Personal Access Token issued by B-Fabric:

```python
client = Bfabric.connect_pat("https://fgcz-bfabric.uzh.ch/bfabric", pat="your_token")
```

PATs are not refreshed automatically; when one expires you need a new one. `bfabric-cli auth pat` stores a PAT in your
config file, so `Bfabric.connect()` picks it up like any other environment.

## Web Service Password

```{note}
Web service passwords are being phased out in favour of the OAuth login above. Prefer `bfabric-cli login` for new setups.
```

An environment can also hold a B-Fabric login and web service password directly:

```yaml
PRODUCTION:
  login: yourBfabricLogin
  password: yourBfabricWebServicePassword
  base_url: https://fgcz-bfabric.uzh.ch/bfabric/
```

`Bfabric.connect()` uses these the same way — the auth method is a property of the environment, not of the call.

## Temporarily Changing Authentication

The `with_auth()` context manager allows you to temporarily set authentication for a `Bfabric` client. This is useful when
authenticating multiple users to avoid accidental use of the wrong credentials:

```python
from bfabric import Bfabric
from bfabric.config import BfabricAuth

client = Bfabric.connect()

# Temporarily use different credentials
with client.with_auth(BfabricAuth(login="other_user", password="other_pass")):
    # All operations in this block use different authentication
    samples = client.read(endpoint="sample", obj={"name": "Test"})

# Authentication is restored after the block
samples = client.read(endpoint="sample", obj={"name": "Test"})

print(f"Current user: {client.auth.login}")  # Shows original user
```

On an OAuth client the automatic token refresh is suspended for the duration of the block, so the credentials you pass
are the ones that get used.

## Without Authentication

For certain use cases (e.g. tests, read-only operations on public endpoints), you may want to create a client without
authentication:

```python
# Disable authentication - useful for tests
client = Bfabric.connect(config_file_env=None, include_auth=False)
```

```{warning}
Without authentication, you won't be able to perform operations that require credentials, such as creating or updating
entities.
```

## Verification

Always verify you're using the correct environment:

```python
from bfabric import Bfabric

client = Bfabric.connect()
print(f"Connected to: {client.config.base_url}")
print(f"User: {client.auth.login}")
```

For an OAuth environment `client.auth.login` is the placeholder `__oauth__` rather than your username — use
`bfabric-cli auth status` to see who you are logged in as and when the token expires.
