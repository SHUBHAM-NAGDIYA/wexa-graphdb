"""
ArangoDB uses AQL, not Cypher, so its queries are written separately
inside workloads.py (see QUERY_SETS['aql']). Uses python-arango.
"""
from __future__ import annotations
import os
from typing import Iterable
from arango import ArangoClient
from .base import GraphDBAdapter


class ArangoDBAdapter(GraphDBAdapter):
    name = "arangodb"
    query_language = "aql"

    def __init__(self):
        self.url = os.environ["ARANGODB_URL"]
        self.user = os.environ["ARANGODB_USER"]
        self.password = os.environ["ARANGODB_PASSWORD"]
        self.db_name = os.environ.get("ARANGODB_DB", "benchmark")
        self._client = None
        self._db = None

    def connect(self) -> None:
        self._client = ArangoClient(hosts=self.url)
        sys_db = self._client.db("_system", username=self.user, password=self.password)
        if not sys_db.has_database(self.db_name):
            sys_db.create_database(self.db_name)
        self._db = self._client.db(self.db_name, username=self.user, password=self.password)
        if not self._db.has_collection("Person"):
            self._db.create_collection("Person")
        if not self._db.has_collection("KNOWS"):
            self._db.create_collection("KNOWS", edge=True)

    def close(self) -> None:
        pass

    def clear(self) -> None:
        self._db.collection("Person").truncate()
        self._db.collection("KNOWS").truncate()

    def ensure_indexes(self) -> None:
        self._db.collection("Person").add_persistent_index(fields=["id"], unique=True)
        self._db.collection("Person").add_persistent_index(fields=["bucket"], unique=False)

    def load_nodes_batch(self, nodes: Iterable[dict]) -> None:
        docs = [{"_key": str(n["id"]), "id": n["id"], "bucket": n["id"] % 50} for n in nodes]
        self._db.collection("Person").insert_many(docs, overwrite=True)

    def load_edges_batch(self, edges: Iterable[dict]) -> None:
        docs = [
            {"_from": f"Person/{e['src']}", "_to": f"Person/{e['dst']}"}
            for e in edges
        ]
        self._db.collection("KNOWS").insert_many(docs, overwrite=True)

    def run_query(self, query: str, params: dict | None = None) -> list[dict]:
        cursor = self._db.aql.execute(query, bind_vars=params or {})
        return list(cursor)

    def count_nodes(self) -> int:
        return self._db.collection("Person").count()

    def count_edges(self) -> int:
        return self._db.collection("KNOWS").count()
