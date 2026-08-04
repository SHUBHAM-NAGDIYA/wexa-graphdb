"""
FalkorDB speaks Cypher, but over the Redis protocol (GRAPH.QUERY), not Bolt.
Uses the official `falkordb` python client.
"""
from __future__ import annotations
import os
from typing import Iterable
from falkordb import FalkorDB
from .base import GraphDBAdapter


class FalkorDBAdapter(GraphDBAdapter):
    name = "falkordb"
    query_language = "cypher"

    def __init__(self):
        self.host = os.environ["FALKORDB_HOST"]
        self.port = int(os.environ.get("FALKORDB_PORT", 6379))
        self.password = os.environ.get("FALKORDB_PASSWORD")
        self.graph_name = os.environ.get("FALKORDB_GRAPH", "benchmark")
        self._db = None
        self._graph = None

    def connect(self) -> None:
        self._db = FalkorDB(host=self.host, port=self.port, password=self.password)
        self._graph = self._db.select_graph(self.graph_name)

    def close(self) -> None:
        pass  # falkordb client manages its own connection pool

    def clear(self) -> None:
        try:
            self._graph.delete()
        except Exception:
            pass  # nothing to delete yet
        self._graph = self._db.select_graph(self.graph_name)

    def ensure_indexes(self) -> None:
        self._graph.query("CREATE INDEX IF NOT EXISTS FOR (n:Person) ON (n.id)")
        self._graph.query("CREATE INDEX IF NOT EXISTS FOR (n:Person) ON (n.bucket)")

    def load_nodes_batch(self, nodes: Iterable[dict]) -> None:
        self._graph.query(
            "UNWIND $rows AS row CREATE (n:Person {id: row.id, bucket: row.id % 50})",
            {"rows": list(nodes)},
        )

    def load_edges_batch(self, edges: Iterable[dict]) -> None:
        self._graph.query(
            """
            UNWIND $rows AS row
            MATCH (a:Person {id: row.src}), (b:Person {id: row.dst})
            CREATE (a)-[:KNOWS]->(b)
            """,
            {"rows": list(edges)},
        )

    def run_query(self, query: str, params: dict | None = None) -> list[dict]:
        result = self._graph.query(query, params or {})
        header = [h[1] for h in result.header] if result.header else []
        return [dict(zip(header, row)) for row in result.result_set]

    def count_nodes(self) -> int:
        return self.run_query("MATCH (n) RETURN count(n) AS c")[0]["c"]

    def count_edges(self) -> int:
        return self.run_query("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
