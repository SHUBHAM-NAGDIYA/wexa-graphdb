"""
Common interface every graph DB adapter implements, so the loader and
workload runner can treat all five platforms identically.
"""
from abc import ABC, abstractmethod
from typing import Any, Iterable


class GraphDBAdapter(ABC):
    name: str = "base"
    query_language: str = "cypher"  # "cypher" or "aql"

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    @abstractmethod
    def clear(self) -> None:
        """Wipe the instance before loading, so runs are repeatable."""
        ...

    @abstractmethod
    def ensure_indexes(self) -> None:
        """Create the indexes used by the 'indexed lookup' workload."""
        ...

    @abstractmethod
    def load_nodes_batch(self, nodes: Iterable[dict]) -> None:
        ...

    @abstractmethod
    def load_edges_batch(self, edges: Iterable[dict]) -> None:
        ...

    @abstractmethod
    def run_query(self, query: str, params: dict | None = None) -> list[dict]:
        """Run a single query and return rows as list of dicts."""
        ...

    @abstractmethod
    def count_nodes(self) -> int:
        ...

    @abstractmethod
    def count_edges(self) -> int:
        ...
