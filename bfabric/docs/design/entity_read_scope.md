# Entities and `ReadScope`

## The problem

Historically every `Entity` stored the live `Bfabric` client it was read with. That coupling was a
known design mistake:

- It tied immutable data objects to a stateful, authenticated connection, so an entity dragged
  credentials into every pickle / YAML round-trip.
- It blocked a single process from serving **multiple B-Fabric instances** — and, more pressingly,
  multiple **users** on the same instance — because each entity was pinned to one client.
- It was the root of two hard cross-instance guards in `EntityReader` that raised `ValueError`
  whenever an entity's `bfabric_instance` differed from the client's `base_url`.

## The design

Entities are now **pure data**: a `data_dict` plus a required `bfabric_instance` string, nothing
else. The connection lives in a **`ReadScope`** — an ambient, read-only hub that:

1. **Routes reads by instance.** A read scope holds one internal `EntityReader` per registered
   client. `read_uris` groups its URIs by instance and dispatches each group to the matching
   reader, so one read scope can read from several instances at once. `query` (which targets a single
   SOAP endpoint) is routed to the reader for the named instance.
2. **Owns the entity cache.** The cache stack is a member of the read scope, so its lifetime is bounded
   by the read scope — a cache can never outlive the connection/authority scope, which closes a
   cross-user cache-leak hole (pure-data entities are otherwise freely shareable).
3. **Is the ambient context for lazy navigation.** `workunit.application`, `created_by`,
   `ExternalJob.client_entity`, and unloaded `refs` resolve the connection via `get_read_scope()`.

`client.reader` returns a single-client `ReadScope`; `ReadScope([client_a, client_b])`
builds a multi-instance one.

### Explicit-only, read-only

- **Explicit-only.** There is no implicit auto-registration. Navigation works only inside an active
  read scope (`with client.reader:` / `with ReadScope([...]):`); outside one, `get_read_scope()`
  raises a self-explaining `LookupError`. This is deliberate: the resolver key is an instance *URL*,
  which names a *server*, not an *authority*. Auto-registering "the last reader that ran" would let a
  user's lazy navigation silently execute with, e.g., a privileged feeder client on the same
  instance. Making the caller name the read scope's client keeps "whose credentials does navigation
  use" a visible decision.
- **Read-only.** The read scope exposes no `save`/`delete`. Writes always go through an explicit
  `Bfabric` client, so a write can never accidentally run under the ambient (possibly wrong) identity.

### Nesting merges by instance

`with` nesting merges by instance: an inner read scope resolves its own instances first and falls back
to the enclosing read scope for others. This is what lets code establish a read scope for its own client
(e.g. `Resolver.resolve` does `with self._client.reader:`) whether or not a caller already opened one.

## Where read scopes are established

- **CLI + app-runner:** the `@use_client` decorator wraps each command body in `with client.reader:`,
  so commands (and any entity navigation inside them) need no change.
- **Library / notebook use:** wrap navigation in `with client.reader:` (explicit reads via
  `client.reader.read_*` work without it; only lazy navigation needs the ambient read scope).
- **Web servers (recommended pattern):** open the read scope per request, bound to the *user's* client,
  inside the request task — e.g. a FastAPI dependency:

  ```python
  def resolver_scope(user_client: BfabricUserClientDep):
      with user_client.reader:  # navigation in this request runs with the user's authority
          yield
  ```

  Push the read scope inside the per-request task (not at app construction) so it rides the request's
  `contextvars` context; never register a privileged/service client as the request's ambient read scope.

## Alternatives considered

- **Inject a reader into the entity at construction** — zero ambient state and keeps
  `entity.application`, but the entity carries a connection again (heavier, credential-bearing
  pickles), only partially addressing the original problem; offline/YAML entities would still need a
  fallback resolver, so you end up needing both mechanisms.
- **Explicit reader passing** (`reader.get(entity.some_ref)`) — fully pure and magic-free, but it
  destroys the `HasOne`/`HasMany` attribute-navigation API the whole library depends on, and every
  consumer changes.

The `ContextVar`-based ambient read scope was chosen because it keeps *both* pure-data entities and the
attribute-navigation ergonomics, at the cost of a single visible boundary — and it mirrors the
existing cache-stack `ContextVar` precedent in `entities/cache/`.
