# I benchmarked CognoDB against 4 managed graph databases — here's what happened

Most graph database benchmarks you'll find online aren't apples-to-apples: different
hardware tiers, different datasets, different definitions of "fast." So when I got the
chance to benchmark CognoDB — a new managed graph database — against the platforms
people already reach for, I set one rule before writing any code: **same free tier,
same dataset, same queries, everywhere.** If a database looks better here, it has to
win on equal footing.

## Setup

Five platforms, all on their smallest free/entry tier: **CognoDB Cloud** (0.5 vCPU /
256 MB RAM / 1 GB disk — the tightest of the five, and the tier everything else was
sized against), **Neo4j AuraDB Free**, **Memgraph Cloud**, **FalkorDB Cloud**, and
**ArangoDB Oasis**.

Dataset: the [SNAP `email-Enron` graph](https://snap.stanford.edu/data/email-Enron.html)
— 36,692 nodes, 367,662 directed edges, loaded identically into all five via each
platform's own driver. Six workload categories, each run 100 times after warm-up:
ingest throughput, 1/2/3-hop traversal, point lookup, indexed lookup, aggregation, and
a mixed read/write sweep at 1/10/40 concurrent clients.

Full code, harness, and raw results: **[link to GitHub repo]**. If you don't take my
word for any of this, clone it and run it yourself against your own free-tier
accounts — that's the point.

## The numbers

**Ingest throughput** (relationships/sec, batched driver writes):

*[chart: results/charts/ingest_throughput.png — replace with real numbers once
`src/stats.py` has run against all five platforms]*

**Traversal latency by hop depth** (p50/p95, ms):

*[chart: results/charts/traversal_latency.png]*

**Mixed read/write throughput at 1 / 10 / 40 concurrent clients**:

*[chart: results/charts/mixed_throughput.png]*

*(Tables for every metric — point lookup, indexed lookup, aggregation, footprint — are
in the [repo's README](link).)*

## What the numbers show — and where I could be wrong

*[Fill in after real numbers are in. This is the section that actually matters: name
where CognoDB was faster, where it wasn't, and your best guess at* why *— e.g.
index-free adjacency vs. index-based traversal, driver/network overhead, or something
about how each engine handles the free-tier resource ceiling. If CognoDB lost on a
metric, say so plainly here — burying it undermines the whole piece.]*

## Caveats, in the open

- Free tiers get throttled and share hardware with other tenants — noisy-neighbor
  effects are real and I can't fully control for them. Treat single-run numbers as
  indicative, not definitive.
- Not every platform's free tier is *exactly* CognoDB's 0.5 vCPU / 256 MB — where a
  competitor's free tier is meaningfully bigger, that's called out next to its numbers
  in the README, not hidden.
- Cypher and AQL queries are logically equivalent, not byte-identical — ArangoDB's
  query language is different by design.
- Ingest numbers reflect driver-level batched writes (1,000 rows/batch), not each
  platform's dedicated bulk-import tool — so don't read these as best-case ingest
  numbers for any platform.
- *[Add any failed runs, timeouts, or platform-specific surprises encountered during
  the actual runs.]*

## Try it yourself

The harness is one script per platform plus a stats/chart generator — clone the repo,
drop in your own free-tier credentials, and `python src/run_benchmark.py <platform>`
for whichever platforms you want to check. If your numbers come out differently, I'd
genuinely like to know why — open an issue or reply here.

**Repo:** [link] · **Full results & methodology:** see the README
