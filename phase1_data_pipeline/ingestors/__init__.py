"""
Base ingestor — all data source parsers inherit from this.

Each ingestor converts a raw data source (Slack exports, WhatsApp chats,
PDFs, photos) into a standardized Document format that can be embedded
and stored in the vector database.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from loguru import logger


class DataCategory(str, Enum):
    """Content categories for authorization tier mapping."""
    PROFESSIONAL = "professional"
    PUBLIC_OPINIONS = "public_opinions"
    GENERAL_KNOWLEDGE = "general_knowledge"
    PERSONAL_STORIES = "personal_stories"
    PREFERENCES = "preferences"
    DAILY_LIFE = "daily_life"
    DEEP_THOUGHTS = "deep_thoughts"
    VULNERABILITIES = "vulnerabilities"
    PRIVATE_DECISIONS = "private_decisions"
    COMMUNICATION_STYLE = "communication_style"
    HUMOR = "humor"
    RELATIONSHIPS = "relationships"


class SourceType(str, Enum):
    """Types of data sources."""
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    KEYBASE = "keybase"
    EMAIL = "email"
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"
    CODE = "code"
    PHOTO = "photo"
    SOCIAL = "social"


@dataclass
class Document:
    """
    Standardized document format.
    
    Every piece of data — whether it's a Slack message, a paragraph from
    a PDF, or a description of a photo — gets converted into this format
    before embedding and storage.
    """
    
    # Core content
    content: str                              # The actual text
    source_type: SourceType                   # Where it came from
    source_file: str = ""                     # Original file path
    
    # Identity
    doc_id: str = ""                          # Unique identifier
    
    # Temporal
    timestamp: Optional[datetime] = None      # When was this created/sent
    
    # Classification
    category: DataCategory = DataCategory.GENERAL_KNOWLEDGE
    access_tier: str = "friends"              # Default tier
    
    # Metadata
    metadata: dict = field(default_factory=dict)
    
    # Context (for messages: who said it, conversation context)
    author: str = ""                          # Who wrote this
    is_self: bool = False                     # Is this the twin owner's content?
    conversation_id: str = ""                 # Thread/conversation grouping
    
    # For communication style extraction
    tone: str = ""                            # detected tone
    formality: float = 0.5                    # 0=casual, 1=formal
    
    def to_embedding_text(self) -> str:
        """Format for embedding — includes relevant context."""
        parts = []
        if self.author and self.is_self:
            parts.append(f"[My message]")
        elif self.author:
            parts.append(f"[Message from {self.author}]")
        if self.timestamp:
            parts.append(f"[{self.timestamp.strftime('%Y-%m-%d')}]")
        parts.append(self.content)
        return " ".join(parts)
    
    def to_metadata(self) -> dict:
        """Flatten to dict for ChromaDB metadata storage."""
        meta = {
            "source_type": self.source_type.value,
            "source_file": self.source_file,
            "category": self.category.value,
            "access_tier": self.access_tier,
            "author": self.author,
            "is_self": self.is_self,
            "conversation_id": self.conversation_id,
        }
        if self.timestamp:
            meta["timestamp"] = self.timestamp.isoformat()
        meta.update(self.metadata)
        return meta


class BaseIngestor(ABC):
    """
    Base class for all data source ingestors.
    
    Subclasses implement `ingest()` to parse their specific format
    and yield standardized Document objects.
    """
    
    def __init__(self, source_dir: str, owner_name: str = "Ade"):
        self.source_dir = Path(source_dir)
        self.owner_name = owner_name
        self.documents: list[Document] = []
    
    @abstractmethod
    def ingest(self) -> list[Document]:
        """Parse the data source and return Documents."""
        ...
    
    def _is_owner_message(self, author: str) -> bool:
        """Check if a message was sent by the twin owner."""
        owner_variants = [
            self.owner_name.lower(),
            self.owner_name.lower().replace(" ", ""),
        ]
        return author.lower().strip() in owner_variants
    
    def _generate_doc_id(self, source_type: str, index: int, extra: str = "") -> str:
        """Generate a unique document ID."""
        import hashlib
        raw = f"{source_type}:{index}:{extra}:{datetime.now().isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    
    def validate(self) -> bool:
        """Check if the source directory exists and has data."""
        if not self.source_dir.exists():
            logger.warning(f"Source directory not found: {self.source_dir}")
            return False
        return True
