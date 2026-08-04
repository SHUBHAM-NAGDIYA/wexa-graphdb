"""
Defines the read/write workloads from assignment section 5.2 and a
percentile-latency timing harness. Two query sets are provided because
ArangoDB uses AQL while everything else uses Cypher.
"""
import random
import time
import statistics
import concurrent.futures as cf
from adapters.base import GraphDBAdapter

ITERATIONS = 100
WARMUP_ITERATIONS = 10

CYPHER_QUERIES = {
    "point_lookup": "MATCH (n:Person {id: $id}) RETURN n",
    # Filters on a *different* indexed property (bucket, not the primary id),
    # and returns a set of matches rather than a single node, so this is
    # actually a distinct workload from point_lookup rather than a duplicate.
    "indexed_lookup": "MATCH (n:Person) WHERE n.bucket = $bucket RETURN n.id LIMIT 50",
    "traverse_1hop": "MATCH (n:Person {id: $id})-[:KNOWS]->(m) RETURN m.id LIMIT 50",
    "traverse_2hop": "MATCH (n:Person {id: $id})-[:KNOWS*2]->(m) RETURN DISTINCT m.id LIMIT 50",
    "traverse_3hop": "MATCH (n:Person {id: $id})-[:KNOWS*3]->(m) RETURN DISTINCT m.id LIMIT 50",
    "aggregation": "MATCH (n:Person)-[r:KNOWS]->() RETURN n.id AS id, count(r) AS out_degree ORDER BY out_degree DESC LIMIT 20",
}

AQL_QUERIES = {
    "point_lookup": "FOR n IN Person FILTER n.id == @id RETURN n",
    "indexed_lookup": "FOR n IN Person FILTER n.bucket == @bucket LIMIT 50 RETURN n.id",
    "traverse_1hop": "FOR v IN 1..1 OUTBOUND CONCAT('Person/', @id) KNOWS LIMIT 50 RETURN v.id",
    "traverse_2hop": "FOR v IN 2..2 OUTBOUND CONCAT('Person/', @id) KNOWS LIMIT 50 RETURN v.id",
    "traverse_3hop": "FOR v IN 3..3 OUTBOUND CONCAT('Person/', @id) KNOWS LIMIT 50 RETURN v.id",
    "aggregation": """
        FOR n IN Person
            LET out_degree = LENGTH(FOR v, e IN 1..1 OUTBOUND n KNOWS RETURN 1)
            SORT out_degree DESC
            LIMIT 20
            RETURN {id: n.id, out_degree: out_degree}
    """,
}

NUM_BUCKETS = 50  # nodes are assigned id % NUM_BUCKETS at load time (see load.py)


def query_set_for(adapter: GraphDBAdapter) -> dict:
    return AQL_QUERIES if adapter.query_language == "aql" else CYPHER_QUERIES


def percentiles(latencies_ms: list[float]) -> dict:
    s = sorted(latencies_ms)
    return {
        "p50_ms": round(statistics.median(s), 2),
        "p95_ms": round(s[int(len(s) * 0.95) - 1], 2),
        "min_ms": round(s[0], 2),
        "max_ms": round(s[-1], 2),
        "n": len(s),
    }


def _sample_ids(adapter: GraphDBAdapter, k: int) -> list[int]:
    rows = adapter.run_query(
        "MATCH (n:Person) RETURN n.id AS id LIMIT 5000"
        if adapter.query_language != "aql"
        else "FOR n IN Person LIMIT 5000 RETURN n.id"
    )
    ids = [r["id"] for r in rows]
    return random.sample(ids, min(k, len(ids)))


def _params_for(workload_name: str, sample_id: int) -> dict:
    if workload_name == "indexed_lookup":
        return {"bucket": sample_id % NUM_BUCKETS}
    return {"id": sample_id}


def run_read_workload(adapter: GraphDBAdapter, workload_name: str) -> dict:
    query = query_set_for(adapter)[workload_name]
    sample_ids = _sample_ids(adapter, ITERATIONS + WARMUP_ITERATIONS)

    # warm-up (not measured)
    for i in range(WARMUP_ITERATIONS):
        adapter.run_query(query, _params_for(workload_name, sample_ids[i]))

    latencies = []
    for i in range(WARMUP_ITERATIONS, WARMUP_ITERATIONS + ITERATIONS):
        start = time.perf_counter()
        adapter.run_query(query, _params_for(workload_name, sample_ids[i]))
        latencies.append((time.perf_counter() - start) * 1000)

    return {"workload": workload_name, **percentiles(latencies)}


def run_mixed_workload(adapter_factory, concurrency: int = 10, duration_seconds: int = 20) -> dict:
    """
    adapter_factory: zero-arg callable that returns a *connected* adapter,
    so each thread gets its own connection (drivers aren't always thread-safe).
    Mix: 80% reads (point lookup), 20% writes (create + delete a throwaway node).
    """
    stop_at = time.perf_counter() + duration_seconds
    completed = []

    def worker():
        adapter = adapter_factory()
        adapter.connect()
        local_count = 0
        rng = random.Random()
        sample_ids = _sample_ids(adapter, 200)
        query = query_set_for(adapter)["point_lookup"]
        while time.perf_counter() < stop_at:
            if rng.random() < 0.8:
                adapter.run_query(query, {"id": rng.choice(sample_ids)})
            else:
                # Create-then-delete a throwaway node so the write side of the
                # mix is exercised without permanently growing the dataset —
                # important on free tiers with ~1GB storage caps.
                throwaway_id = rng.randint(10_000_000, 20_000_000)
                if adapter.query_language == "aql":
                    adapter.run_query(
                        "INSERT {id: @id, bucket: @id % 50} INTO Person",
                        {"id": throwaway_id},
                    )
                    adapter.run_query(
                        "FOR n IN Person FILTER n.id == @id REMOVE n IN Person",
                        {"id": throwaway_id},
                    )
                else:
                    adapter.run_query(
                        "CREATE (:Person {id: $id, bucket: $id % 50})",
                        {"id": throwaway_id},
                    )
                    adapter.run_query(
                        "MATCH (n:Person {id: $id}) DELETE n", {"id": throwaway_id}
                    )
            local_count += 1
        adapter.close()
        return local_count

    with cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(worker) for _ in range(concurrency)]
        for fut in cf.as_completed(futures):
            completed.append(fut.result())

    total_ops = sum(completed)
    return {
        "workload": "mixed_read_write",
        "concurrency": concurrency,
        "duration_seconds": duration_seconds,
        "total_ops": total_ops,
        "throughput_qps": round(total_ops / duration_seconds, 1),
        "read_write_mix": "80/20",
    }
