## Open questions

- Inter-chunk dependencies (assuming some chunks are different from others)
    - Should chunks be standardized somehow
- How to transfer a chunk (which is a folder) reasonably across different scheduler systems? -> tar or shared folder (needs config...)
- Ideally: first version allows relatively flexible slurm configuration

## Future possibilities

- The initial version is concerned about submitting one job to a (SLURM) scheduler. However, at a later time multi-node
    jobs could be introduced by this job submitting then further jobs to the scheduler. Ideally, it could reuse the same
    scheduling interface code as is used for the single-node jobs.
    - Internally, we could prepare by making the app runner code that executes the individual chunks more generic.
- Parallel execution of chunks could be introduced. This is actually very similar to the previous point.
