"""
Vector Store — ChromaDB-based persistent memory for the digital twin.

This replaces the original 380GB static dataset approach.
Instead of loading everything into memory, documents are embedded
and stored in ChromaDB, then retrieved on-demand via similarity search.

The authorization tier system is enforced at query time — the store
filters results based on the requester's access level.
"""

from pathlib import Path
from typing import Optional
from loguru import logger

from phase1_data_pipeline.ingestors import Document


# Authorization tier hierarchy (higher tiers include lower ones)
TIER_HIERARCHY = {
    "public": 0,
    "friends": 1,
    "close": 2,
    "private": 3,
}


class VectorStore:
    """
    ChromaDB-backed vector store with authorization-aware retrieval.
    
    Replaces the REGO/ABAC module from the original system.
    """
    
    def __init__(
        self,
        persist_dir: str = "./data/chromadb",
        collection_name: str = "digital_twin_memory",
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self._client = None
        self._collection = None
    
    @property
    def client(self):
        """Lazy-load ChromaDB client."""
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info(f"ChromaDB initialized at {self.persist_dir}")
        return self._client
    
    @property
    def collection(self):
        """Get or create the main collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},  # Cosine similarity
            )
            logger.info(
                f"Collection '{self.collection_name}' ready. "
                f"Contains {self._collection.count()} documents."
            )
        return self._collection
    
    def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]],
    ) -> int:
        """
        Add documents with their embeddings to the store.
        
        Returns the number of documents added.
        """
        if not documents or not embeddings:
            return 0
        
        if len(documents) != len(embeddings):
            raise ValueError(
                f"Document count ({len(documents)}) != embedding count ({len(embeddings)})"
            )
        
        # Prepare data for ChromaDB
        ids = [doc.doc_id for doc in documents]
        texts = [doc.content for doc in documents]
        metadatas = [doc.to_metadata() for doc in documents]
        
        # ChromaDB has a batch limit, so chunk if needed
        batch_size = 500
        total_added = 0
        
        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            
            try:
                self.collection.upsert(
                    ids=ids[i:batch_end],
                    embeddings=embeddings[i:batch_end],
                    documents=texts[i:batch_end],
                    metadatas=metadatas[i:batch_end],
                )
                total_added += batch_end - i
            except Exception as e:
                logger.error(f"Error adding batch {i}-{batch_end}: {e}")
        
        logger.info(f"Added {total_added} documents to vector store")
        return total_added
    
    def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        access_tier: str = "public",
        source_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        """
        Query the vector store with authorization filtering.
        
        This is where the ABAC replacement happens:
        - The access_tier determines what documents are visible
        - Higher tiers see everything lower tiers can see
        
        Args:
            query_embedding: The embedded query vector
            n_results: Number of results to return
            access_tier: Requester's authorization level
            source_type: Optional filter by source (slack, photo, etc.)
            category: Optional filter by content category
        
        Returns:
            List of dicts with 'content', 'metadata', and 'distance'
        """
        # Build the where filter for authorization
        tier_level = TIER_HIERARCHY.get(access_tier, 0)
        allowed_tiers = [
            tier for tier, level in TIER_HIERARCHY.items()
            if level <= tier_level
        ]
        
        where_filter = {"access_tier": {"$in": allowed_tiers}}
        
        # Add optional filters
        if source_type:
            where_filter["source_type"] = source_type
        if category:
            where_filter["category"] = category
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
            
            # Flatten results
            output = []
            if results and results["documents"]:
                for i in range(len(results["documents"][0])):
                    output.append({
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                        "id": results["ids"][0][i] if results["ids"] else "",
                    })
            
            return output
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []
    
    def query_by_text(
        self,
        query_text: str,
        n_results: int = 10,
        access_tier: str = "public",
    ) -> list[dict]:
        """
        Query using text (ChromaDB will embed it internally).
        Useful for quick lookups without pre-embedding.
        """
        tier_level = TIER_HIERARCHY.get(access_tier, 0)
        allowed_tiers = [
            tier for tier, level in TIER_HIERARCHY.items()
            if level <= tier_level
        ]
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where={"access_tier": {"$in": allowed_tiers}},
                include=["documents", "metadatas", "distances"],
            )
            
            output = []
            if results and results["documents"]:
                for i in range(len(results["documents"][0])):
                    output.append({
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    })
            
            return output
            
        except Exception as e:
            logger.error(f"Text query error: {e}")
            return []
    
    def get_stats(self) -> dict:
        """Get statistics about the vector store contents."""
        total = self.collection.count()
        
        stats = {
            "total_documents": total,
            "collection_name": self.collection_name,
            "persist_dir": str(self.persist_dir),
        }
        
        # Sample to get distribution info
        if total > 0:
            sample_size = min(total, 1000)
            sample = self.collection.get(
                limit=sample_size,
                include=["metadatas"],
            )
            
            if sample["metadatas"]:
                # Count by source type
                source_counts = {}
                tier_counts = {}
                for meta in sample["metadatas"]:
                    st = meta.get("source_type", "unknown")
                    source_counts[st] = source_counts.get(st, 0) + 1
                    at = meta.get("access_tier", "unknown")
                    tier_counts[at] = tier_counts.get(at, 0) + 1
                
                stats["source_distribution"] = source_counts
                stats["tier_distribution"] = tier_counts
        
        return stats
    
    def clear(self):
        """Clear all documents from the collection."""
        self.client.delete_collection(self.collection_name)
        self._collection = None
        logger.warning(f"Cleared collection '{self.collection_name}'")
