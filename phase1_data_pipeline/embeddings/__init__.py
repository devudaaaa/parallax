"""
Embedding Engine — Convert documents into vectors for similarity search.

This is the bridge between raw data and the vector store.
Uses sentence-transformers for local embeddings (fast, free, no API needed).
"""

from typing import Optional
import numpy as np
from loguru import logger

from phase1_data_pipeline.ingestors import Document


class EmbeddingEngine:
    """
    Generate embeddings for documents using sentence-transformers.
    
    Default model: all-MiniLM-L6-v2 (384 dimensions, fast, good quality)
    Alternative: all-mpnet-base-v2 (768 dimensions, higher quality, slower)
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
    
    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Model loaded. Dimension: {self._model.get_sentence_embedding_dimension()}")
        return self._model
    
    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()
    
    def embed_documents(self, documents: list[Document], batch_size: int = 64) -> list[list[float]]:
        """
        Generate embeddings for a list of documents.
        
        Uses the document's `to_embedding_text()` method which includes
        relevant context (author, timestamp) alongside the content.
        """
        texts = [doc.to_embedding_text() for doc in documents]
        
        logger.info(f"Embedding {len(texts)} documents in batches of {batch_size}")
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        
        # Convert numpy arrays to lists for ChromaDB compatibility
        return [emb.tolist() for emb in embeddings]
    
    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string for similarity search."""
        embedding = self.model.encode(
            query,
            normalize_embeddings=True,
        )
        return embedding.tolist()
    
    def embed_texts(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Embed a list of raw text strings."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 100,
            normalize_embeddings=True,
        )
        return [emb.tolist() for emb in embeddings]
