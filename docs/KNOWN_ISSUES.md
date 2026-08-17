# Known issues

## HydraDB: manifest garbage collection fails permanently under `CLOUD_PROVIDER=local`

Upstream HydraDB bug, not a Backstory bug:
[hydra-db/hydradb#81](https://github.com/hydra-db/hydradb/issues/81).

**Status in this project: fixed in the deployed configuration** by moving
object storage off the local filesystem. Details below.

### What happens

`graph-node`'s manifest garbage collector requires a conditional write
(`put_opts` with `PutMode::Update`). The `LocalFileSystem` object store
backend does not implement it. Under `CLOUD_PROVIDER=local`, garbage
collection starts failing a few minutes into sustained write activity and
never recovers. The node keeps serving reads and `/readyz` stays green
the whole time, so nothing looks wrong from outside, and then at some
point every write starts failing with:

```
HydraDB query failed (500): {'error': {'code': 'internal', 'message': 'internal query execution error'}}
```

with the real cause visible only in the container logs:

```
object store error: Operation `put_opts` with mode `PutMode::Update` not
yet implemented by LocalFileSystem(file:///data/store).
```

We hit this three times locally and twice on the deployed instance,
matching the upstream report: a restart does not recover it, the store
has to be deleted and rebuilt.

### The fix: use an S3-compatible object store

S3-compatible stores do implement conditional puts, so the GC path works
and the failure does not occur. This is also the architecture HydraDB is
designed around, as its own README puts it: "Storage and compute are
fully disaggregated. S3-compatible object storage is the..." primary
backend. `CLOUD_PROVIDER=local` is a development convenience.

This is reachable from the published `ghcr.io/hydra-db/hydradb:latest`
image with no source build, though the README does not document it.
Tracing the call path:

- HydraDB's `object_store_from_env` (`src/engine.rs`) delegates to
  SlateDB's `load_object_store_from_env`
- HydraDB builds SlateDB with `features = ["aws"]` (`Cargo.toml`), so the
  `"aws"` arm is compiled into the shipped binary
- That arm calls `object_store`'s `AmazonS3Builder::from_env()`, which
  reads every `AWS_`-prefixed environment variable

The deployment therefore sets `CLOUD_PROVIDER=aws` and points it at
Tigris, Fly's S3-compatible storage (`fly storage create`). See
`fly.toml`.

Two details worth knowing, both verified against `object_store`'s source
rather than assumed:

- `AmazonS3Builder::from_env()` only reads variables starting with
  `AWS_` (`src/aws/builder.rs`, `from_env`). `fly storage create` sets
  the bucket as `BUCKET_NAME`, which is therefore ignored, so `fly.toml`
  sets `AWS_BUCKET` explicitly.
- `AWS_ENDPOINT_URL_S3` (which Fly does set) maps to a distinct
  `S3Endpoint` config key that takes precedence over `AWS_ENDPOINT` in
  `build()`, so Tigris's endpoint is picked up correctly.

**Verified after the switch**, not assumed: the full HydraDB capability
smoke test (10/10, including upserts, relationship creation, supersedes
lineage, and contradiction edges) passes against the deployed instance;
no files are written under the local `/data/store` path afterward; and
the Tigris bucket contains the live graph data, including the
`_writer_leases` and `compactions` keys that the failing GC path touches.

### Local development

`docker-compose.yml` still uses `CLOUD_PROVIDER=local`. That is fine for
the test suite, the smoke checks, and the demos, all of which are short
lived. If local writes start failing with the error above, recreate the
store:

```powershell
docker compose down
docker volume rm backstory_hydradb_store backstory_hydradb_cache
docker compose up -d
```

Also delete the SQLite sidecar (`runs/local/sidecar.sqlite`, or wherever
`BACKSTORY_DATA_DIR` points). It holds HydraDB vertex ids allocated
before the wipe, and without clearing it the next write fails with
`MATCH endpoint vertex ... does not exist`.

## LLM extraction and answers require an OpenAI-compatible key

Without `OPENAI_API_KEY`, Backstory uses the heuristic extractor and a
deterministic template answerer. Both work, and are what the automated
tests and the four demos are verified against, but answers read as
template text rather than natural prose and extraction only recognizes a
fixed set of phrasings. Any OpenAI-compatible endpoint works, not just
OpenAI: see `.env.example`.
