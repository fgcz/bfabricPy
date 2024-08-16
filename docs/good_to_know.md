# Good to Know

## Updating workunits with many associated resources

!!! note "Summary: Updating workunits and its associated resources"
    1. Set workunit state to `"processing"`.
    2. Update workunit and associated resources, as much as you need to.
    3. Set workunit state to `"available"`.

When updating large workunits, it's crucial to prevent state recomputation in B-Fabric by setting the workunit state to `"processing"` before making any changes.
Failing to do so can lead to significant performance issues and complications, especially during iterative updates.

After all entities have been saved, you can set the workunit state to `"available"`.
However, be aware that B-Fabric will still perform a state recomputation at this stage, which might result in a different inferred state, such as `"failed"`.
The `"processing"` state is the only one that ensures state recomputation is bypassed during the saving process.
