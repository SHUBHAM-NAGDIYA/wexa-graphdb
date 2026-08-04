"""
Downloads and prepares the SNAP email-Enron dataset:
https://snap.stanford.edu/data/email-Enron.html
~36,692 nodes, ~367,662 directed edges (fits the 100k-500k edge range
required by the assignment and comfortably fits every platform's free tier).

Run: python dataset/download_dataset.py
Produces: dataset/nodes.csv, dataset/edges.csv
"""
import csv
import gzip
import os
import urllib.request

SRC_URL = "https://snap.stanford.edu/data/email-Enron.txt.gz"
RAW_PATH = "dataset/email-Enron.txt.gz"
NODES_CSV = "dataset/nodes.csv"
EDGES_CSV = "dataset/edges.csv"


def download():
    if not os.path.exists(RAW_PATH):
        print(f"Downloading {SRC_URL} ...")
        urllib.request.urlretrieve(SRC_URL, RAW_PATH)
    else:
        print("Raw file already present, skipping download.")


def parse_and_write():
    node_ids = set()
    edges = []
    with gzip.open(RAW_PATH, "rt") as f:
        for line in f:
            if line.startswith("#"):
                continue
            src, dst = line.strip().split()
            src, dst = int(src), int(dst)
            node_ids.add(src)
            node_ids.add(dst)
            edges.append((src, dst))

    with open(NODES_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id"])
        for nid in sorted(node_ids):
            writer.writerow([nid])

    with open(EDGES_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["src", "dst"])
        for src, dst in edges:
            writer.writerow([src, dst])

    print(f"Wrote {len(node_ids)} nodes -> {NODES_CSV}")
    print(f"Wrote {len(edges)} edges -> {EDGES_CSV}")


if __name__ == "__main__":
    download()
    parse_and_write()
