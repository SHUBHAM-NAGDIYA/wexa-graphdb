"""
Loads dataset/nodes.csv and dataset/edges.csv into a given adapter in
batches, and measures ingest throughput as required by section 5.2.
"""
import csv
import time
from adapters.base import GraphDBAdapter

BATCH_SIZE = 25


def _batched(iterable, n):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == n:
            yield batch
            batch = []
    if batch:
        yield batch


def load_dataset(adapter: GraphDBAdapter, nodes_csv: str, edges_csv: str) -> dict:
    adapter.clear()
    adapter.ensure_indexes()

    with open(nodes_csv) as f:
        reader = csv.DictReader(f)
        nodes = [{"id": int(row["id"])} for row in reader]

    with open(edges_csv) as f:
        reader = csv.DictReader(f)
        edges = [{"src": int(row["src"]), "dst": int(row["dst"])} for row in reader]

    t0 = time.perf_counter()
    for batch in _batched(nodes, BATCH_SIZE):
        adapter.load_nodes_batch(batch)
    t_nodes = time.perf_counter() - t0

    t1 = time.perf_counter()
    for batch in _batched(edges, BATCH_SIZE):
        adapter.load_edges_batch(batch)
    t_edges = time.perf_counter() - t1

    total_wall = t_nodes + t_edges
    return {
        "platform": adapter.name,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_load_seconds": round(t_nodes, 3),
        "edge_load_seconds": round(t_edges, 3),
        "total_wall_clock_seconds": round(total_wall, 3),
        "nodes_per_second": round(len(nodes) / t_nodes, 1) if t_nodes > 0 else None,
        "relationships_per_second": round(len(edges) / t_edges, 1) if t_edges > 0 else None,
    }
