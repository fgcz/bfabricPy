#!/usr/bin/env python3
# This is an informal, argparse-driven demo script (not library code), so the strict-only checks that
# fire on that shape -- Any-typed argparse Namespace attributes, unused print()/write() results, and a
# closure-mutation false-positive for "unreachable" -- are quieted here rather than line by line.
# pyright: reportAny=false, reportUnusedCallResult=false, reportUnreachable=false
"""Prove tus resumability against a real B-Fabric environment.

This is a LIVE demo, not a unit test (the unit test in
``tests/bfabric/transfer/generic/test_tus_mover.py`` fakes the uploader, so it can
only prove the *client* seeds the offset correctly -- not that the real server
retains a partial upload). This script drives the public transfer API end to end
against a real server:

  1. starts an upload and ABORTS a few chunks in (simulating a dropped
     connection), capturing the server-side upload URL via ``on_url``;
  2. waits, then RESUMES from that URL by calling ``send_to_sink`` again with
     ``resume_url=``;
  3. asserts the resume picked up at the server-retained offset instead of
     restarting, and finished at the full file size.

It exercises the same path ``bfabric.operations.workunit.upload_files`` uses:
``UploadRestClient`` (create-resources + initiate) -> ``tus_sink_for_resource`` ->
``send_to_sink``.

Prerequisites: an OAuth-backed config env with the ``tus`` scope. Authenticate once
with::

    bfabric-cli auth login --scope "api:write tus"

then run like the equivalent CLI upload::

    python -m bfabric.examples.prove_tus_resume \\
        --config-env DEMO --container-id 403 --application-id 435

The file uploaded is a generated temp file (default 12 MiB) so that the abort
leaves a genuine partial upload spanning several chunks -- a tiny file would fit in
one chunk and there would be nothing to resume.
"""

from __future__ import annotations

import argparse
import os
import tempfile
import time
from pathlib import Path

from bfabric import Bfabric
from bfabric.entities import Workunit
from bfabric.transfer import (
    Credentials,
    UploadRestClient,
    check_upload_scope,
    compute_file_info,
    send_to_sink,
    tus_sink_for_resource,
)

# The mover uploads at DEFAULT_CHUNK_SIZE (4 MiB) and send_to_sink exposes no chunk_size override, so
# the abort threshold must be expressed in real chunks: mirror that size here. The default 12 MiB file
# is 3 chunks, so aborting after the first leaves a meaningful, resumable remainder.
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MiB — matches the mover's DEFAULT_CHUNK_SIZE
CHUNKS_BEFORE_ABORT = 1
WAIT_SECONDS = 10


class _SimulatedOutage(Exception):
    """Raised from the progress callback to abort the transfer mid-flight."""


def _make_test_file(size_bytes: int) -> Path:
    """Create a temp file of deterministic, non-trivial content."""
    fd, name = tempfile.mkstemp(prefix="tus_resume_", suffix=".bin")
    with os.fdopen(fd, "wb") as f:
        block = bytes(range(256)) * 4096  # 1 MiB, repeating so the md5 is stable per size
        written = 0
        while written < size_bytes:
            to_write = min(len(block), size_bytes - written)
            f.write(block[:to_write])
            written += to_write
    return Path(name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config-env", default="DEMO", help="B-Fabric config environment")
    parser.add_argument("--container-id", type=int, default=403)
    parser.add_argument("--application-id", type=int, default=435)
    parser.add_argument("--size-mib", type=int, default=12, help="Size of the generated test file (MiB)")
    args = parser.parse_args()

    client = Bfabric.connect(config_file_env=args.config_env)
    rest = UploadRestClient(client)
    check_upload_scope(client)  # fail fast with a re-auth hint if the token lacks the 'tus' scope

    test_file = _make_test_file(args.size_mib * 1024 * 1024)
    try:
        file_info = compute_file_info(test_file)
        print(f"Test file: {test_file} ({file_info.size} bytes)")

        # --- Real B-Fabric upload setup ---
        print("Creating workunit...")
        wu_result = client.save(
            "workunit",
            {
                "containerid": args.container_id,
                "applicationid": args.application_id,
                "name": "tus-resume-demo",
                "status": "processing",
            },
        )
        workunit_id = Workunit(wu_result[0], client=None, bfabric_instance=client.config.base_url).id
        print(f"  Workunit ID: {workunit_id}")

        print("Creating resource + upload token...")
        resources = rest.create_resources(workunit_id, [file_info])
        resource = resources[0]
        import_resource_ids = [r.import_resource_id for r in resources if r.import_resource_id is not None]
        token_result = rest.get_upload_token(workunit_id, [resource.id], import_resource_ids)
        sink = tus_sink_for_resource(resource, token_result, workunit_id=workunit_id, container_id=args.container_id)
        creds = Credentials()  # the tus leg authenticates with the sink's own token

        # --- Phase 1: upload a few chunks, then ABORT ---
        print(f"Phase 1: uploading {CHUNKS_BEFORE_ABORT} chunk(s) then aborting...")
        saved_url: str | None = None
        abort_offset = 0
        abort_threshold = CHUNKS_BEFORE_ABORT * CHUNK_SIZE

        def _capture_url(url: str) -> None:
            nonlocal saved_url
            saved_url = url

        def _abort_after_threshold(done: int, _total: int) -> None:
            nonlocal abort_offset
            if done >= abort_threshold:
                abort_offset = done
                raise _SimulatedOutage

        try:
            send_to_sink(sink, test_file, creds, on_url=_capture_url, on_progress=_abort_after_threshold)
        except _SimulatedOutage:
            pass

        print(f"  Aborted at offset: {abort_offset} bytes")
        print(f"  Saved upload URL:  {saved_url}")
        assert saved_url is not None, "no upload URL captured before abort"
        assert 0 < abort_offset < file_info.size, "aborted too late -- file already complete"

        # --- Simulated outage ---
        print(f"Waiting {WAIT_SECONDS}s (simulated outage)...")
        time.sleep(WAIT_SECONDS)

        # --- Phase 2: resume from the saved URL ---
        print("Phase 2: resuming from saved URL...")
        resume_offsets: list[int] = []
        outcome = send_to_sink(
            sink, test_file, creds, resume_url=saved_url, on_progress=lambda done, _total: resume_offsets.append(done)
        )

        # send_to_sink reports the server-retained offset as its first progress callback on resume.
        server_offset = resume_offsets[0] if resume_offsets else outcome.final_offset
        print(f"  Server resumed at offset: {server_offset} bytes")

        assert (
            server_offset == abort_offset
        ), f"RESUME FAILED: server resumed at {server_offset} != abort offset {abort_offset} (server lost progress)"
        assert outcome.final_offset == file_info.size, "upload did not reach full size"

        print()
        print("TUS RESUMABILITY PROVEN")
        print(f"  Aborted at:   {abort_offset} bytes")
        print(f"  Resumed from: {server_offset} bytes (server-confirmed)")
        print(f"  Completed at: {outcome.final_offset} / {file_info.size} bytes")
    finally:
        test_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
