"""
Phase 1 Pipeline Runner — Orchestrates the full data ingestion process.

This is the entry point for converting raw personal data into the
vector store that powers the digital twin's memory.

Usage:
    python -m phase1_data_pipeline.run_pipeline
    python -m phase1_data_pipeline.run_pipeline --sources slack whatsapp
    python -m phase1_data_pipeline.run_pipeline --clear
"""

import json
import sys
import time
from pathlib import Path
from loguru import logger

from config_loader import settings, yaml_config, ensure_directories, DATA_DIR

from phase1_data_pipeline.ingestors.messages import (
    SlackIngestor, WhatsAppIngestor, DiscordIngestor, KeybaseIngestor
)
from phase1_data_pipeline.ingestors.documents import (
    PDFIngestor, DocxIngestor, MarkdownIngestor, CodeIngestor
)
from phase1_data_pipeline.ingestors.photos import PhotoIngestor
from phase1_data_pipeline.processors.text_processor import TextProcessor, StyleExtractor
from phase1_data_pipeline.embeddings import EmbeddingEngine
from phase1_data_pipeline.vector_store import VectorStore


class Pipeline:
    """
    Main data pipeline orchestrator.
    
    Flow:
    1. Ingest raw data from all sources
    2. Process and enrich documents
    3. Extract communication style profile
    4. Generate embeddings
    5. Store in ChromaDB vector store
    6. Export style profile for Phase 2
    """
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.style_extractor = StyleExtractor()
        self.embedding_engine = EmbeddingEngine(model_name=settings.embedding_model)
        self.vector_store = VectorStore(
            persist_dir=settings.chroma_persist_dir,
            collection_name=settings.chroma_collection_name,
        )
        
        # All available ingestors
        self.ingestors = {
            "slack": lambda: SlackIngestor(
                str(DATA_DIR / "raw" / "slack"),
                owner_name=settings.twin_name,
            ),
            "whatsapp": lambda: WhatsAppIngestor(
                str(DATA_DIR / "raw" / "whatsapp"),
                owner_name=settings.twin_name,
            ),
            "discord": lambda: DiscordIngestor(
                str(DATA_DIR / "raw" / "discord"),
                owner_name=settings.twin_name,
            ),
            "keybase": lambda: KeybaseIngestor(
                str(DATA_DIR / "raw" / "keybase"),
                owner_name=settings.twin_name,
            ),
            "pdf": lambda: PDFIngestor(
                str(DATA_DIR / "raw" / "documents" / "pdfs"),
                owner_name=settings.twin_name,
            ),
            "docx": lambda: DocxIngestor(
                str(DATA_DIR / "raw" / "documents" / "docs"),
                owner_name=settings.twin_name,
            ),
            "markdown": lambda: MarkdownIngestor(
                str(DATA_DIR / "raw" / "documents" / "notes"),
                owner_name=settings.twin_name,
            ),
            "code": lambda: CodeIngestor(
                str(DATA_DIR / "raw" / "documents" / "code"),
                owner_name=settings.twin_name,
            ),
            "photos": lambda: PhotoIngestor(
                str(DATA_DIR / "raw" / "photos"),
                owner_name=settings.twin_name,
            ),
        }
    
    def run(self, sources: list[str] | None = None, clear: bool = False):
        """
        Run the full pipeline.
        
        Args:
            sources: Specific sources to ingest (None = all)
            clear: Whether to clear the vector store first
        """
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("🧠 Digital Twin Data Pipeline — Phase 1")
        logger.info("=" * 60)
        
        # Ensure directory structure exists
        ensure_directories()
        
        # Optionally clear existing data
        if clear:
            logger.warning("Clearing existing vector store...")
            self.vector_store.clear()
        
        # ── Step 1: Ingest ─────────────────────────────
        logger.info("\n📥 Step 1: Ingesting data sources...")
        all_documents = []
        
        active_sources = sources or list(self.ingestors.keys())
        
        for source_name in active_sources:
            if source_name not in self.ingestors:
                logger.warning(f"Unknown source: {source_name}")
                continue
            
            logger.info(f"  → Ingesting: {source_name}")
            ingestor = self.ingestors[source_name]()
            
            if ingestor.validate():
                docs = ingestor.ingest()
                all_documents.extend(docs)
                logger.info(f"    ✓ {len(docs)} documents from {source_name}")
            else:
                logger.info(f"    ⊘ No data found for {source_name} (directory empty/missing)")
        
        if not all_documents:
            logger.warning("No documents ingested. Add data to ./data/raw/ and try again.")
            self._print_data_guide()
            return
        
        logger.info(f"\n  Total raw documents: {len(all_documents)}")
        
        # ── Step 2: Process ────────────────────────────
        logger.info("\n🔧 Step 2: Processing and enriching documents...")
        processed_docs = self.text_processor.process_batch(all_documents)
        logger.info(f"  Processed: {len(processed_docs)} documents ({len(all_documents) - len(processed_docs)} filtered)")
        
        # ── Step 3: Style Extraction ───────────────────
        logger.info("\n🎭 Step 3: Extracting communication style profile...")
        style_profile = self.style_extractor.analyze(processed_docs)
        
        # Save style profile for Phase 2
        style_output = DATA_DIR / "processed" / "style_profile.json"
        with open(style_output, "w") as f:
            json.dump(style_profile, f, indent=2, default=str)
        logger.info(f"  Style profile saved to {style_output}")
        
        # Generate prompt instructions from style
        prompt_instructions = self.style_extractor.to_prompt_instructions()
        prompt_output = DATA_DIR / "processed" / "style_prompt.txt"
        with open(prompt_output, "w") as f:
            f.write(prompt_instructions)
        logger.info(f"  Style prompt instructions saved to {prompt_output}")
        
        # ── Step 4: Embed ──────────────────────────────
        logger.info("\n🧮 Step 4: Generating embeddings...")
        embeddings = self.embedding_engine.embed_documents(processed_docs)
        logger.info(f"  Generated {len(embeddings)} embeddings (dim={self.embedding_engine.dimension})")
        
        # ── Step 5: Store ──────────────────────────────
        logger.info("\n💾 Step 5: Storing in vector database...")
        added = self.vector_store.add_documents(processed_docs, embeddings)
        
        # ── Summary ────────────────────────────────────
        elapsed = time.time() - start_time
        stats = self.vector_store.get_stats()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Pipeline Complete!")
        logger.info("=" * 60)
        logger.info(f"  Time: {elapsed:.1f}s")
        logger.info(f"  Documents ingested: {len(all_documents)}")
        logger.info(f"  Documents processed: {len(processed_docs)}")
        logger.info(f"  Documents stored: {added}")
        logger.info(f"  Total in store: {stats['total_documents']}")
        
        if "source_distribution" in stats:
            logger.info(f"\n  Source distribution:")
            for src, count in stats["source_distribution"].items():
                logger.info(f"    {src}: {count}")
        
        if "tier_distribution" in stats:
            logger.info(f"\n  Authorization tier distribution:")
            for tier, count in stats["tier_distribution"].items():
                logger.info(f"    {tier}: {count}")
        
        logger.info(f"\n  Style profile highlights:")
        logger.info(f"    Avg message length: {style_profile.get('avg_message_length', 0):.0f} words")
        logger.info(f"    Vocabulary richness: {style_profile.get('vocabulary_richness', 0):.2f}")
        logger.info(f"    Humor frequency: {style_profile.get('humor_frequency', 0):.1%}")
        
        logger.info(f"\n🔜 Next: Run Phase 2 to activate the Logic Twin")
        logger.info(f"   python -m phase2_logic_twin.twin")
    
    def _print_data_guide(self):
        """Print instructions for adding data."""
        guide = """
╔══════════════════════════════════════════════════════════════╗
║              📂 Data Directory Guide                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Place your data exports in these directories:               ║
║                                                              ║
║  ./data/raw/slack/          → Slack workspace export          ║
║    └── channel_name/                                         ║
║        └── YYYY-MM-DD.json                                   ║
║                                                              ║
║  ./data/raw/whatsapp/       → WhatsApp chat exports (.txt)   ║
║                                                              ║
║  ./data/raw/discord/        → Discord exports (.json)        ║
║                                                              ║
║  ./data/raw/keybase/        → Keybase exports (.json)        ║
║                                                              ║
║  ./data/raw/documents/pdfs/ → PDF files                      ║
║  ./data/raw/documents/docs/ → Word documents                 ║
║  ./data/raw/documents/notes/→ Markdown notes                 ║
║  ./data/raw/documents/code/ → Code files                     ║
║                                                              ║
║  ./data/raw/photos/         → Photos (jpg, png, webp)        ║
║                                                              ║
║  How to export:                                              ║
║  • Slack: Workspace Settings → Import/Export → Export         ║
║  • WhatsApp: Chat → More → Export chat → Without media       ║
║  • Discord: Use DiscordChatExporter (github)                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(guide)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Digital Twin Data Pipeline")
    parser.add_argument(
        "--sources", nargs="+",
        choices=["slack", "whatsapp", "discord", "keybase", "pdf", "docx", "markdown", "code", "photos"],
        help="Specific sources to ingest (default: all)",
    )
    parser.add_argument("--clear", action="store_true", help="Clear existing vector store first")
    parser.add_argument("--stats", action="store_true", help="Show vector store stats and exit")
    
    args = parser.parse_args()
    
    pipeline = Pipeline()
    
    if args.stats:
        stats = pipeline.vector_store.get_stats()
        print(json.dumps(stats, indent=2))
        return
    
    pipeline.run(sources=args.sources, clear=args.clear)


if __name__ == "__main__":
    main()
