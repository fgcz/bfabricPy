# API Reference: Entity Types

Complete reference for all B-Fabric entity types.

```{eval-rst}
.. autoclass:: bfabric.entities.core.entity.Entity
    :members:
    :undoc-members:
    :show-inheritance:
```

```{eval-rst}
.. automodule:: bfabric.entities
    :members:
    :undoc-members:
    :show-inheritance:
```

## Quick Links

| Entity | Description | Special Features |
| ------------------------ | ------------------------ | -------------------------------------------------------- |
| **Project** | Top-level project entity | Container for samples and workunits |
| **Sample** | Sample within a project | Has container relationship (Project/Order) |
| **Workunit** | Workunit/job entity | Rich parameter access, output folder calculation |
| **Dataset** | Dataset entity | DataFrame conversion, export methods, column access |
| **Application** | Application definition | Technology folder name, storage/executable relationships |
| **Executable** | Executable binary/script | Base64 decoding, parameter definitions |
| **ExternalJob** | External job reference | Client entity resolution, workunit association |
| **Resource** | File resource | Path methods, storage/sample/workunit relationships |
| **Storage** | Storage location | Base path, SCP prefix |
| **Parameter** | Workunit parameter | Key-value access with special handling |
| **User** | User entity | Login-based lookup |
| **Order** | Order entity | Optional project relationship |
| **Workflow** | Workflow definition | Workflow steps, template association |
| **WorkflowStep** | Individual workflow step | Container relationship |
| **WorkflowTemplate** | Workflow template | Template steps definition |
| **WorkflowTemplateStep** | Template step | Template association |
| **Plate** | Plate entity | Basic entity |
| **Run** | Run entity | Basic entity |
| **Instrument** | Instrument entity | Basic entity |
| **MultiplexKit** | Multiplex kit | Filtered multiplex IDs |
| **MultiplexId** | Multiplex ID | Basic entity |

## See Also

- [Working with Entities](../../user_guides/working_with_entities/index.md) - Guide to using entities
- [EntityReader](../entity_reader/index.md) - EntityReader API reference
- [Relationships](../../user_guides/reading_data/entity_api) - Using entity relationships
