"""Vector database port - Interface for vector storage operations."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class VectorDBPort(ABC):
    """Port (interface) for vector database operations.

    This defines the contract that any vector database adapter must implement.
    Following hexagonal architecture, the application layer defines this port,
    and the infrastructure layer provides the implementation.
    """

    @abstractmethod
    def search_similar(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in the database.

        Args:
            query_vector: The query vector to search for.
            limit: Maximum number of results to return.
            score_threshold: Minimum similarity score (0.0 to 1.0).

        Returns:
            List of similar vectors with their metadata and scores.
        """
        pass

    @abstractmethod
    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]]
    ) -> bool:
        """Insert or update vectors in the database.

        Args:
            vectors: List of dictionaries containing:
                - id: Unique identifier for the vector
                - vector: The vector embedding
                - payload: Metadata associated with the vector

        Returns:
            True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def ensure_collection_exists(self) -> bool:
        """Ensure the collection exists, create if it doesn't.

        Returns:
            True if collection exists or was created successfully.
        """
        pass

