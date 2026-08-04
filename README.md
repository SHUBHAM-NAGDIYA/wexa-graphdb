# CognoDB Cloud vs. Managed Graph Databases: A Reproducible Benchmark

This repo benchmarks [CognoDB Cloud](https://console.cognodb.com) against four other
managed graph database platforms — **Neo4j AuraDB Free**, **Memgraph Cloud**,
**FalkorDB Cloud**, and **ArangoDB Oasis** — on identical hardware tiers, an identical
dataset, and identical query workloads.

> Disclosure: this benchmark was produced as part of a take-home assignment for a role
> at Wexa AI, the company that builds CognoDB. The methodology, code, and results here
> are ours; readers should weigh that context accordingly.

## TL;DR

*(2–3 sentences on the headline finding, written after `python src/stats.py` has real
numbers to summarize — see §3.)*

## 1. Methodology

### 1.1 Fairness / resource parity

Every platform is run on its smallest ("free" or entry) tier, sized as close as
possible to CognoDB's free instance:

| Platform | Tier | vCPU | RAM | Storage | Notes |
|---|---|---|---|---|---|
| CognoDB Cloud | c0 (free) | 0.5 (burstable) | 256 MB | 1 GB | |
| Neo4j AuraDB | Free | shared | 1 GB* | ~10 GB* | *Aura Free doesn't publish exact vCPU; recorded as-is, flagged as a fairness caveat |
| Memgraph Cloud | Free/entry | *(record from console at signup)* | | | |
| FalkorDB Cloud | Free | *(record from console at signup)* | | | |
| ArangoDB Oasis | Trial | *(record from console at signup)* | | | |

**Caveat:** not every platform's free tier publishes identical vCPU/RAM numbers to
CognoDB's. Where a platform's smallest tier is meaningfully larger than CognoDB's
0.5vCPU/256MB, that is called out explicitly next to its results rather than hidden —
per the assignment's fairness requirement, this is a methodology limitation, not
something to paper over.

### 1.2 Dataset

[SNAP `email-Enron`](https://snap.stanford.edu/data/email-Enron.html): 36,692 nodes,
367,662 directed edges. Same dataset, same node/edge schema (`Person` nodes with
`id` and `bucket` properties, `KNOWS` edges), loaded identically into every platform.
Loaded via each platform's native driver (Bolt/Cypher `UNWIND` batches for
CognoDB/Neo4j/Memgraph/FalkorDB, `insert_many` for ArangoDB) in batches of 1,000 rows
— no bulk-import tool was used, so ingest numbers reflect driver-level batched writes,
not platform-specific bulk loaders. That's a deliberate simplification, noted here
rather than hidden. `bucket = id % 50` is assigned at load time purely so the
"indexed/filtered lookup" workload has a non-primary-key property to filter on.

### 1.3 Workloads

All six required workload categories are implemented once per query language (Cypher
in `src/workloads.py:CYPHER_QUERIES`, AQL in `AQL_QUERIES`) so the same *logical* query
runs on every platform:

| Workload | What it measures | Distinct from... |
|---|---|---|
| `point_lookup` | Single node fetch by primary key `id` | — |
| `indexed_lookup` | Filtered fetch by a *different* indexed property (`bucket`), returning up to 50 matches | Not the same query as point_lookup — it exercises a range/equality filter on a secondary index rather than a primary-key hit |
| `traverse_1hop` / `2hop` / `3hop` | Outbound `KNOWS` traversal, `LIMIT 50` | — |
| `aggregation` | Out-degree count + top-20 sort | — |
| Mixed read/write | 80% point-lookup reads, 20% create+delete writes, swept at 1/10/40 concurrent clients | Writes are cleaned up (create *and* delete) each iteration so the dataset size stays constant across a 20s run — important on a 1GB free-tier disk |

100 iterations per read workload after a 10-iteration warm-up, reporting p50/p95.
Mixed workload swept at 1 / 10 / 40 concurrent clients, 20s per concurrency level.

Indexes created before loading (see each adapter's `ensure_indexes()`): `Person.id`
and `Person.bucket` on every platform.

### 1.4 What "not observable" means

Stored data size and memory usage are not exposed identically across all five
consoles. Where a platform's dashboard doesn't surface this, the results record
`"not observable"` rather than guessing.

## 2. Reproducing this benchmark

```bash
git clone <this-repo-url>
cd wexa-graphdb-benchmark
pip install -r requirements.txt
cp .env.example .env   # fill in your own free-tier credentials for all 5 platforms

python dataset/download_dataset.py

cd src
python run_benchmark.py cognodb
python run_benchmark.py neo4j_aura
python run_benchmark.py memgraph
python run_benchmark.py falkordb
python run_benchmark.py arangodb

python stats.py   # prints markdown tables + writes results/charts/*.png
```

Each `run_benchmark.py <platform>` call loads the dataset fresh (clearing any prior
data), runs every read workload, then runs the mixed-workload concurrency sweep, and
writes `results/<platform>.json`. Runs are independent and can be re-run individually.
`stats.py` reads whatever `results/*.json` files exist, so you don't have to run all
five before checking output for the ones you've done.

**Setup notes for each platform:**
- **CognoDB**: signup at console.cognodb.com, create a free `c0` instance, copy the
  `bolt+s://` URI and generated password into `.env` (`COGNODB_URI`, `COGNODB_USER=cognodb`,
  `COGNODB_PASSWORD`) — see assignment §3.
- **Neo4j AuraDB Free**: console.neo4j.io → New Instance → Free. Same Bolt driver, so it
  reuses `adapters/bolt_cypher.py`.
- **Memgraph Cloud**: also Bolt-compatible, reuses the same adapter.
- **FalkorDB Cloud**: connects over the Redis protocol (`falkordb` package), not Bolt —
  needs `FALKORDB_HOST`/`PORT`/`PASSWORD` in `.env`.
- **ArangoDB Oasis**: free trial instance; uses AQL via `python-arango`, needs
  `ARANGODB_URL`/`USER`/`PASSWORD`.

## 3. Results

*(Generated by `python src/stats.py` after all five platforms have been run — paste
the markdown tables here, and reference the PNGs written to `results/charts/`.)*

### Data loading

| Platform | Nodes/sec | Rels/sec | Total wall-clock (s) |
|---|---|---|---|
| cognodb | – | – | – |
| neo4j_aura | – | – | – |
| memgraph | – | – | – |
| falkordb | – | – | – |
| arangodb | – | – | – |

### Traversals, lookups, aggregation

*(one table per workload, p50/p95 — see `src/stats.py` output;
`results/charts/traversal_latency.png` visualizes hop depth vs. latency)*

### Mixed read/write throughput

| Platform | Concurrency | Throughput (qps) |
|---|---|---|
| ... | 1 / 10 / 40 | ... |

See `results/charts/mixed_throughput.png` for the concurrency sweep.

### Footprint

*(stored size / memory per platform, from each console, or "not observable")*

## 4. Analysis

*(Fill in after real numbers are in: where CognoDB is faster/slower and a hypothesis
why — e.g. differences in traversal execution (index-free adjacency vs. index
lookups), driver overhead, network hop to the region chosen, or free-tier
throttling/noisy-neighbor effects.)*

## 5. Caveats and honesty notes

- Free-tier instances are subject to provider-side throttling/noisy-neighbor effects
  that this benchmark cannot fully control for; multiple repeated runs are recommended
  before treating any single number as authoritative.
- Network latency to each platform's region will differ unless all five happen to offer
  a matching region to the client machine — record the client region and each
  platform's region here once known.
- AuraDB Free and other platforms may not expose vCPU/RAM identically to CognoDB's
  stated specs (see §1.1) — this is a resource-parity limitation, not a hidden one.
- Query workloads are logically equivalent across Cypher and AQL but are not
  byte-identical strings, since the query languages differ.
- `indexed_lookup` filters on a synthetic `bucket = id % 50` property rather than a
  real-world attribute, since the SNAP email-Enron dataset has no natural secondary
  field — noted so nobody mistakes it for a realistic filter workload.
- Ingest is measured via driver-level batched writes (1,000 rows/batch), not each
  platform's dedicated bulk-import tool, so these numbers should not be read as each
  platform's best-case ingest performance.
- *(Add any failed runs, timeouts, or anomalies observed during actual execution.)*

## 6. Public write-up

Full write-up with charts: **[link to LinkedIn/Twitter/blog post here]**

See `post/blog_post.md` for the full draft, ready to publish once §3's numbers are filled in.
