"""Phase 1: Data Collection & Pipeline — Ingests personal data into the vector store."""

from phase1_data_pipeline.ingestors import BaseIngestor, Document, DataCategory, SourceType
from phase1_data_pipeline.ingestors.messages import (
    SlackIngestor, WhatsAppIngestor, DiscordIngestor, KeybaseIngestor,
)
from phase1_data_pipeline.ingestors.documents import (
    PDFIngestor, DocxIngestor, MarkdownIngestor, CodeIngestor,
)
from phase1_data_pipeline.ingestors.photos import PhotoIngestor
from phase1_data_pipeline.processors.text_processor import TextProcessor, StyleExtractor
from phase1_data_pipeline.embeddings import EmbeddingEngine
from phase1_data_pipeline.vector_store import VectorStore

__all__ = [
    "BaseIngestor", "Document", "DataCategory", "SourceType",
    "SlackIngestor", "WhatsAppIngestor", "DiscordIngestor", "KeybaseIngestor",
    "PDFIngestor", "DocxIngestor", "MarkdownIngestor", "CodeIngestor",
    "PhotoIngestor", "TextProcessor", "StyleExtractor",
    "EmbeddingEngine", "VectorStore",
]
