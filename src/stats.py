"""
Reads every results/<platform>.json and prints markdown tables ready to
paste into README.md's Results section.

Usage: python src/stats.py
"""
import json
import glob
import os

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def load_all():
    runs = {}
    for path in glob.glob("results/*.json"):
        with open(path) as f:
            data = json.load(f)
            runs[data["platform"]] = data
    return runs


def print_ingest_table(runs):
    print("\n### Data loading\n")
    print("| Platform | Nodes/sec | Rels/sec | Total wall-clock (s) |")
    print("|---|---|---|---|")
    for platform, data in runs.items():
        ing = data["ingest"]
        print(f"| {platform} | {ing['nodes_per_second']} | {ing['relationships_per_second']} | {ing['total_wall_clock_seconds']} |")


def print_read_tables(runs):
    workload_names = set()
    for data in runs.values():
        for wl in data["read_workloads"]:
            workload_names.add(wl["workload"])

    for wl_name in sorted(workload_names):
        print(f"\n### {wl_name}\n")
        print("| Platform | p50 (ms) | p95 (ms) |")
        print("|---|---|---|")
        for platform, data in runs.items():
            match = next((w for w in data["read_workloads"] if w["workload"] == wl_name), None)
            if match:
                print(f"| {platform} | {match['p50_ms']} | {match['p95_ms']} |")


def print_mixed_table(runs):
    print("\n### Mixed read/write throughput\n")
    print("| Platform | Concurrency | Throughput (qps) |")
    print("|---|---|---|")
    for platform, data in runs.items():
        for row in data["mixed_workload_sweep"]:
            print(f"| {platform} | {row['concurrency']} | {row['throughput_qps']} |")


def make_charts(runs, out_dir="results/charts"):
    if not HAS_MPL:
        print("\n(matplotlib not installed — skipping charts. `pip install matplotlib` to enable.)")
        return
    os.makedirs(out_dir, exist_ok=True)
    platforms = sorted(runs.keys())

    # Ingest throughput
    fig, ax = plt.subplots()
    ax.bar(platforms, [runs[p]["ingest"]["relationships_per_second"] or 0 for p in platforms])
    ax.set_ylabel("relationships/sec")
    ax.set_title("Ingest throughput")
    fig.autofmt_xdate(rotation=30)
    fig.savefig(f"{out_dir}/ingest_throughput.png", bbox_inches="tight")
    plt.close(fig)

    # Traversal p50/p95 by hop depth
    hop_workloads = ["traverse_1hop", "traverse_2hop", "traverse_3hop"]
    fig, ax = plt.subplots()
    width = 0.35
    x = range(len(platforms))
    for i, metric in enumerate(["p50_ms", "p95_ms"]):
        vals = []
        for p in platforms:
            wl = {w["workload"]: w for w in runs[p]["read_workloads"]}
            vals.append(sum(wl[h][metric] for h in hop_workloads if h in wl))
        ax.bar([xi + i * width for xi in x], vals, width, label=metric)
    ax.set_xticks([xi + width / 2 for xi in x])
    ax.set_xticklabels(platforms, rotation=30, ha="right")
    ax.set_ylabel("summed latency across 1/2/3-hop (ms)")
    ax.set_title("Traversal latency")
    ax.legend()
    fig.savefig(f"{out_dir}/traversal_latency.png", bbox_inches="tight")
    plt.close(fig)

    # Mixed workload throughput at each concurrency level
    fig, ax = plt.subplots()
    for p in platforms:
        sweep = runs[p]["mixed_workload_sweep"]
        ax.plot([r["concurrency"] for r in sweep], [r["throughput_qps"] for r in sweep], marker="o", label=p)
    ax.set_xlabel("concurrent clients")
    ax.set_ylabel("throughput (qps)")
    ax.set_title("Mixed read/write throughput")
    ax.legend()
    fig.savefig(f"{out_dir}/mixed_throughput.png", bbox_inches="tight")
    plt.close(fig)

    print(f"\nCharts written to {out_dir}/")


if __name__ == "__main__":
    runs = load_all()
    if not runs:
        print("No results/*.json found yet. Run src/run_benchmark.py for each platform first.")
    else:
        print_ingest_table(runs)
        print_read_tables(runs)
        print_mixed_table(runs)
        make_charts(runs)
