from __future__ import annotations

import os
import time
from typing import Iterable

from neo4j import GraphDatabase
from neo4j.exceptions import (
    ServiceUnavailable,
    SessionExpired,
    TransientError,
    DatabaseError,
)

from .base import GraphDBAdapter


class BoltCypherAdapter(GraphDBAdapter):
    query_language = "cypher"

    def __init__(self, platform_key: str):
        self.name = platform_key
        env_prefix = platform_key.upper()

        self.uri = os.environ[f"{env_prefix}_URI"]
        self.user = os.environ[f"{env_prefix}_USER"]
        self.password = os.environ[f"{env_prefix}_PASSWORD"]

        self._driver = None

    def connect(self) -> None:
        """
        Connect to Neo4j-compatible databases:
        - Neo4j Aura
        - Memgraph Cloud
        - CognoDB
        """

        self._driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            max_connection_lifetime=120,
            connection_timeout=15,
            max_transaction_retry_time=30,
            keep_alive=True,
        )

        self._driver.verify_connectivity()

        print(f"[{self.name}] connected successfully")

    def close(self) -> None:
        if self._driver:
            self._driver.close()

    def clear(self):
        while True:
            result = self.run_query(
                """
                MATCH (n)
                WITH n LIMIT 400
                DETACH DELETE n
                RETURN count(n) AS deleted
                """
            )

            deleted = result[0]["deleted"] if result else 0

            print(f"[{self.name}] deleted {deleted} nodes...")

            if deleted == 0:
                break

    def ensure_indexes(self) -> None:
        self.run_query(
            "CREATE INDEX IF NOT EXISTS FOR (n:Person) ON (n.id)"
        )

        self.run_query(
            "CREATE INDEX IF NOT EXISTS FOR (n:Person) ON (n.bucket)"
        )

    def load_nodes_batch(self, nodes: Iterable[dict]) -> None:
        self.run_query(
            """
            UNWIND $rows AS row
            CREATE (n:Person {
                id: row.id,
                bucket: row.id % 50
            })
            """,
            {
                "rows": list(nodes)
            },
        )

    def load_edges_batch(self, edges: Iterable[dict]) -> None:
        self.run_query(
            """
            UNWIND $rows AS row
            MATCH 
                (a:Person {id: row.src}),
                (b:Person {id: row.dst})
            CREATE (a)-[:KNOWS]->(b)
            """,
            {
                "rows": list(edges)
            },
        )

    def run_query(
        self,
        query: str,
        params: dict | None = None,
        _retries: int = 8
    ) -> list[dict]:

        last_exc = None

        for attempt in range(_retries):

            try:
                with self._driver.session() as session:

                    result = session.run(
                        query,
                        params or {}
                    )

                    query_upper = query.strip().upper()

                    if (
                        query_upper.startswith(
                            (
                                "CREATE",
                                "MATCH",
                                "UNWIND",
                                "MERGE",
                                "DELETE",
                                "DETACH",
                                "DROP",
                            )
                        )
                        and "RETURN" not in query_upper
                    ):
                        result.consume()
                        return []

                    return [
                        record.data()
                        for record in result
                    ]

            except (
                ServiceUnavailable,
                SessionExpired,
                TransientError,
                DatabaseError,
                OSError,
            ) as e:

                last_exc = e

                wait = min(
                    5 * (attempt + 1),
                    30
                )

                print(
                    f"[{self.name}] connection dropped "
                    f"({type(e).__name__}: {e}) "
                    f"retrying in {wait}s "
                    f"({attempt + 1}/{_retries})"
                )

                time.sleep(wait)

                try:
                    self._driver.close()
                except Exception:
                    pass

                self._driver = None

                try:
                    self.connect()

                except Exception as reconnect_error:
                    print(
                        f"[{self.name}] reconnect failed: "
                        f"{reconnect_error}"
                    )

        raise last_exc

    def count_nodes(self) -> int:
        return self.run_query(
            "MATCH (n) RETURN count(n) AS c"
        )[0]["c"]

    def count_edges(self) -> int:
        return self.run_query(
            "MATCH ()-[r]->() RETURN count(r) AS c"
        )[0]["c"]

    @classmethod
    def for_platform(cls, platform_key: str):
        return lambda: cls(platform_key)