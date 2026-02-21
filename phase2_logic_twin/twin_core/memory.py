"""
Memory System — RAG-based retrieval for the digital twin.

Replaces the static 380GB dataset approach. Instead of holding
everything in memory, the twin queries relevant memories on-demand
based on the current conversation context.

Think of it as: the original system loaded ALL data into the neural net.
This system loads only RELEVANT data into the LLM's context window,
which actually produces better results because the signal-to-noise ratio
is dramatically higher.
"""

from loguru import logger

from phase1_data_pipeline.embeddings import EmbeddingEngine
from phase1_data_pipeline.vector_store import VectorStore


class MemorySystem:
    """
    RAG (Retrieval Augmented Generation) memory for the twin.
    
    Given a query or conversation context, retrieves the most relevant
    memories from the vector store, respecting authorization tiers.
    """
    
    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_engine: EmbeddingEngine | None = None,
    ):
        from config_loader import settings
        
        self.vector_store = vector_store or VectorStore(
            persist_dir=settings.chroma_persist_dir,
            collection_name=settings.chroma_collection_name,
        )
        self.embedding_engine = embedding_engine or EmbeddingEngine(
            model_name=settings.embedding_model
        )
    
    def recall(
        self,
        query: str,
        n_results: int = 5,
        access_tier: str = "public",
        source_type: str | None = None,
        category: str | None = None,
    ) -> list[dict]:
        """
        Recall memories relevant to the query.
        
        This is the primary interface — the twin calls this to
        "remember" things relevant to the current conversation.
        
        Args:
            query: What to search for in memory
            n_results: How many memories to retrieve
            access_tier: Authorization level of the requester
            source_type: Filter by source (e.g., "slack", "photo")
            category: Filter by category (e.g., "professional")
        
        Returns:
            List of memory dicts with 'content', 'metadata', 'relevance'
        """
        # Embed the query
        query_embedding = self.embedding_engine.embed_query(query)
        
        # Search with authorization filtering
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            access_tier=access_tier,
            source_type=source_type,
            category=category,
        )
        
        # Format results with relevance score
        memories = []
        for r in results:
            # ChromaDB distance is cosine distance (0 = identical, 2 = opposite)
            # Convert to relevance score (1 = perfect match, 0 = no match)
            relevance = max(0, 1 - r.get("distance", 1))
            
            memories.append({
                "content": r["content"],
                "metadata": r["metadata"],
                "relevance": relevance,
                "source": r["metadata"].get("source_type", "unknown"),
            })
        
        logger.debug(
            f"Recalled {len(memories)} memories for query '{query[:50]}...' "
            f"(tier={access_tier})"
        )
        
        return memories
    
    def recall_for_context(
        self,
        messages: list[dict],
        n_results: int = 8,
        access_tier: str = "public",
    ) -> list[dict]:
        """
        Recall memories based on conversation context.
        
        Instead of a single query, this looks at the recent conversation
        and retrieves memories relevant to the overall discussion.
        
        Args:
            messages: List of conversation messages [{"role": "...", "content": "..."}]
            n_results: Number of memories per query
            access_tier: Authorization level
        """
        # Build a context query from recent messages
        recent_content = " ".join(
            m["content"] for m in messages[-3:]  # Last 3 messages
            if m.get("content")
        )
        
        if not recent_content.strip():
            return []
        
        # Main context query
        memories = self.recall(
            query=recent_content,
            n_results=n_results,
            access_tier=access_tier,
        )
        
        # If the conversation seems to be about a specific topic,
        # also search for that topic specifically
        # (Simple keyword extraction — could be enhanced with NER)
        if len(recent_content.split()) > 10:
            # Take the last message as a focused query
            last_msg = messages[-1].get("content", "")
            if last_msg:
                focused = self.recall(
                    query=last_msg,
                    n_results=3,
                    access_tier=access_tier,
                )
                # Add unique focused memories
                existing_ids = {m["content"][:50] for m in memories}
                for f in focused:
                    if f["content"][:50] not in existing_ids:
                        memories.append(f)
        
        # Sort by relevance
        memories.sort(key=lambda m: m["relevance"], reverse=True)
        
        return memories[:n_results + 3]  # Return a few extra for good measure
    
    def format_memories_for_prompt(self, memories: list[dict]) -> str:
        """
        Format retrieved memories into a string for the LLM prompt.
        
        This is injected into the conversation as context the twin
        can reference when responding.
        """
        if not memories:
            return "No relevant memories found."
        
        parts = ["## Relevant Memories\n"]
        
        for i, mem in enumerate(memories, 1):
            source = mem.get("source", "unknown")
            relevance = mem.get("relevance", 0)
            content = mem["content"]
            
            # Add temporal context if available
            timestamp = mem["metadata"].get("timestamp", "")
            time_str = f" [{timestamp[:10]}]" if timestamp else ""
            
            parts.append(
                f"**Memory {i}** (source: {source}, relevance: {relevance:.0%}{time_str}):\n"
                f"{content}\n"
            )
        
        return "\n".join(parts)
    
    def get_stats(self) -> dict:
        """Get memory system statistics."""
        return self.vector_store.get_stats()
