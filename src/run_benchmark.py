"""
Runs the full benchmark suite (load + all workloads) against ONE platform
and writes results/<platform>.json. Run once per platform.

Usage:
    python src/run_benchmark.py cognodb
    python src/run_benchmark.py cognodb --skip-load
    python src/run_benchmark.py neo4j_aura
    python src/run_benchmark.py memgraph
    python src/run_benchmark.py falkordb
    python src/run_benchmark.py arangodb
"""
import sys
import json
import os
import time
from dotenv import load_dotenv

from load import load_dataset
from workloads import run_read_workload, run_mixed_workload

load_dotenv()

PLATFORM_FACTORIES = {
    "cognodb": lambda: __import__("adapters.bolt_cypher", fromlist=["BoltCypherAdapter"]).BoltCypherAdapter("cognodb"),
    "neo4j_aura": lambda: __import__("adapters.bolt_cypher", fromlist=["BoltCypherAdapter"]).BoltCypherAdapter("neo4j_aura"),
    "memgraph": lambda: __import__("adapters.bolt_cypher", fromlist=["BoltCypherAdapter"]).BoltCypherAdapter("memgraph"),
    "falkordb": lambda: __import__("adapters.falkordb_adapter", fromlist=["FalkorDBAdapter"]).FalkorDBAdapter(),
    "arangodb": lambda: __import__("adapters.arangodb_adapter", fromlist=["ArangoDBAdapter"]).ArangoDBAdapter(),
}

READ_WORKLOADS = [
    "point_lookup",
    "indexed_lookup",
    "traverse_1hop",
    "traverse_2hop",
    "traverse_3hop",
    "aggregation",
]


def main(platform: str, skip_load: bool = False):
    if platform not in PLATFORM_FACTORIES:
        print(f"Unknown platform '{platform}'. Choose from: {', '.join(PLATFORM_FACTORIES)}")
        sys.exit(1)

    factory = PLATFORM_FACTORIES[platform]
    os.makedirs("results", exist_ok=True)
    out_path = f"results/{platform}.json"

    # Resume from any existing partial results file, if present
    if os.path.exists(out_path):
        with open(out_path) as f:
            results = json.load(f)
    else:
        results = {"platform": platform}

    def _save_partial():
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)

    print(f"[{platform}] connecting + loading dataset ...")
    adapter = factory()
    adapter.connect()
    try:
        if skip_load:
            print(f"[{platform}] --skip-load set, using existing data in database")
            results["ingest"] = {"note": "skipped — reused data from previous run"}
        else:
            results["ingest"] = load_dataset(adapter, "dataset/nodes.csv", "dataset/edges.csv")
        _save_partial()

        results["footprint"] = {
            "node_count_after_load": adapter.count_nodes(),
            "edge_count_after_load": adapter.count_edges(),
            "note": "Stored size/memory: record manually from platform console if exposed, else 'not observable'.",
        }
        _save_partial()

        results["read_workloads"] = []
        for wl in READ_WORKLOADS:
            print(f"[{platform}] running {wl} (100 iterations after warm-up)...")
            results["read_workloads"].append(run_read_workload(adapter, wl))
            _save_partial()  # save after each workload too
    finally:
        adapter.close()

    print(f"[{platform}] running mixed read/write workload sweep (1/10/40 clients)...")
    results["mixed_workload_sweep"] = []
    for concurrency in (1, 10, 40):
        results["mixed_workload_sweep"].append(
            run_mixed_workload(factory, concurrency=concurrency, duration_seconds=20)
        )
        _save_partial()

    print(f"[{platform}] done -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/run_benchmark.py <platform> [--skip-load]")
        sys.exit(1)
    skip = "--skip-load" in sys.argv
    main(sys.argv[1], skip_load=skip)