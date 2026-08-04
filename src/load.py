"""
Loads dataset/nodes.csv and dataset/edges.csv into a given adapter in
batches, and measures ingest throughput as required by section 5.2.
"""
import csv
import os
import time
from neo4j.exceptions import TransientError, ServiceUnavailable
from adapters.base import GraphDBAdapter

NODE_BATCH_SIZE = 500
EDGE_LOAD_LIMIT = int(os.environ.get("EDGE_LOAD_LIMIT", "0"))


def _batched(iterable, n):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == n:
            yield batch
            batch = []
    if batch:
        yield batch


def _load_edges_adaptive(adapter, edges, start_batch_size=200, min_batch_size=10):
    i = 0
    total = len(edges)
    loaded = 0
    batch_size = start_batch_size
    idx = 0

    while idx < total:
        chunk = edges[idx: idx + batch_size]
        b0 = time.perf_counter()
        try:
            adapter.load_edges_batch(chunk)
            b1 = time.perf_counter()
            idx += len(chunk)
            loaded += len(chunk)
            i += 1
            print(f"[{adapter.name}] batch {i}: loaded {len(chunk)} (size={batch_size}) "
                  f"— {loaded}/{total} — {b1 - b0:.2f}s")
            if batch_size < start_batch_size:
                batch_size = min(batch_size * 2, start_batch_size)
        except TransientError:
            if batch_size <= min_batch_size:
                raise RuntimeError(f"edge batch failed even at minimum size {min_batch_size}")
            batch_size = max(batch_size // 2, min_batch_size)
            print(f"[{adapter.name}] timeout — shrinking batch size to {batch_size} and retrying...")
        except ServiceUnavailable:
            print(f"[{adapter.name}] connection dropped — reconnecting in 5s and retrying this chunk...")
            time.sleep(5)
            try:
                adapter.close()
            except Exception:
                pass
            adapter.connect()
    return loaded


def load_dataset(adapter: GraphDBAdapter, nodes_csv: str, edges_csv: str) -> dict:
    adapter.clear()
    adapter.ensure_indexes()

    with open(nodes_csv) as f:
        reader = csv.DictReader(f)
        nodes = [{"id": int(row["id"])} for row in reader]

    with open(edges_csv) as f:
        reader = csv.DictReader(f)
        edges = [{"src": int(row["src"]), "dst": int(row["dst"])} for row in reader]

    full_edge_count = len(edges)
    limited = False
    if EDGE_LOAD_LIMIT and EDGE_LOAD_LIMIT < full_edge_count:
        edges = edges[:EDGE_LOAD_LIMIT]
        limited = True
        print(f"[{adapter.name}] EDGE_LOAD_LIMIT set — loading {len(edges)} / {full_edge_count} edges only")

    t0 = time.perf_counter()
    for i, batch in enumerate(_batched(nodes, NODE_BATCH_SIZE), 1):
        adapter.load_nodes_batch(batch)
        print(f"[{adapter.name}] loaded node batch {i} ({i * NODE_BATCH_SIZE} / {len(nodes)})")
    t_nodes = time.perf_counter() - t0

    t1 = time.perf_counter()
    _load_edges_adaptive(adapter, edges, start_batch_size=200, min_batch_size=10)
    t_edges = time.perf_counter() - t1

    total_wall = t_nodes + t_edges
    return {
        "platform": adapter.name,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "full_dataset_edge_count": full_edge_count,
        "edge_load_was_limited": limited,
        "node_load_seconds": round(t_nodes, 3),
        "edge_load_seconds": round(t_edges, 3),
        "total_wall_clock_seconds": round(total_wall, 3),
        "nodes_per_second": round(len(nodes) / t_nodes, 1) if t_nodes > 0 else None,
        "relationships_per_second": round(len(edges) / t_edges, 1) if t_edges > 0 else None,
    }