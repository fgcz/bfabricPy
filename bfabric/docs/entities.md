## High-level `bfabric.entities` API

The `bfabric.entities` module offers a high-level, **read-only** API for retrieval of entities in the B-Fabric system.

This API is designed to simplify entity access by providing lazy-loading capabilities for associated entities. Entities within this module can maintain a reference to a B-Fabric client instance, enabling seamless integration and data retrieval.

### Key Features

- **Read-Only Access**: This module is strictly for read-only operations. None of the classes or methods should be used to modify the database.
- **Lazy-Loading**: Entities are initialized with basic data as returned by a .read operation on its endpoint. However, associated entities are not loaded until explicitly requested, enhancing performance and reducing unnecessary data processing.
- **Modular Design**: Only include generic functionality within this module. Avoid adding highly specific logic to ensure the module remains maintainable over time.
- **No Circular Imports**: Ensure there are no circular dependencies between entities by deferring imports of other entities inside modules until all relevant modules are processed.

### Entity

Each entity has to provide the name of its B-Fabric entity classname as `ENDPOINT`.
An entity is defined uniquely by its `classname` and `id`.

Entities are initialized with the full result structure obtained from a `read` operation on its particular endpoint.
A `return_id_only` result is generally not supposed to be used to initialize an entity instance and behavior is undefined as of now.
In cases where it makes sense to operate on the ids, it's better to directly call the `Bfabric` client methods.

Entities can be retrieved with the methods `Entity.find`, `Entity.find_all` and `Entity.find_by`.
When loading multiple entities of the same type, `Entity.find_all` and `Entity.find_by` should be preferred.
These two methods return a dictionary mapping entity ID to instance and this often helps avoid redundant API calls when expanding relationships over multiple entities.

### Relationships

Custom descriptors are available which are used to represent relationships and enable lazy-loading of data.
Currently the following descriptors are available:

- `HasOne`: Defines a one-to-one relationship between entities.
- `HasMany`: Defines a one-to-many relationship between entities.

Both support setting an additional argument `optional=True` which will ensure `None` (in the case of `HasOne`) and an empty collection (in the case of `HasMany`) are returned when there is no field at all in the result returned by the API.
