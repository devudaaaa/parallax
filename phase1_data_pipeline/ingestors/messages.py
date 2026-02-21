"""
Message Ingestors — Parse chat exports from Slack, WhatsApp, Discord, Keybase.

These are critical for the digital twin because messaging patterns ARE
the personality. The original 2020 system achieved 55-65% similarity on
messaging platforms — this pipeline feeds the system that targets 85%+.

Supported formats:
- Slack: JSON export (workspace export or per-channel)
- WhatsApp: .txt export (standard "DD/MM/YYYY, HH:MM - Name: Message")
- Discord: JSON export (via DiscordChatExporter or similar)
- Keybase: JSON export
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from . import BaseIngestor, Document, SourceType, DataCategory


class SlackIngestor(BaseIngestor):
    """
    Parse Slack workspace exports.
    
    Slack exports as:
    workspace_export/
    ├── channels/
    │   ├── general/
    │   │   ├── 2024-01-01.json
    │   │   └── 2024-01-02.json
    │   └── random/
    │       └── ...
    ├── users.json
    └── channels.json
    """
    
    def ingest(self) -> list[Document]:
        if not self.validate():
            return []
        
        documents = []
        user_map = self._load_user_map()
        
        # Walk through channel directories
        for channel_dir in sorted(self.source_dir.iterdir()):
            if channel_dir.is_dir():
                channel_name = channel_dir.name
                for json_file in sorted(channel_dir.glob("*.json")):
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            messages = json.load(f)
                        
                        for i, msg in enumerate(messages):
                            if msg.get("subtype") in ["channel_join", "channel_leave", "bot_message"]:
                                continue
                            
                            text = msg.get("text", "").strip()
                            if not text or len(text) < 5:
                                continue
                            
                            user_id = msg.get("user", "unknown")
                            author = user_map.get(user_id, user_id)
                            ts = msg.get("ts", "")
                            
                            timestamp = None
                            if ts:
                                try:
                                    timestamp = datetime.fromtimestamp(float(ts))
                                except (ValueError, OSError):
                                    pass
                            
                            doc = Document(
                                content=text,
                                source_type=SourceType.SLACK,
                                source_file=str(json_file),
                                doc_id=self._generate_doc_id("slack", i, f"{channel_name}:{ts}"),
                                timestamp=timestamp,
                                category=DataCategory.COMMUNICATION_STYLE,
                                author=author,
                                is_self=self._is_owner_message(author),
                                conversation_id=f"slack:{channel_name}",
                                metadata={
                                    "channel": channel_name,
                                    "thread_ts": msg.get("thread_ts", ""),
                                    "reactions": [r["name"] for r in msg.get("reactions", [])],
                                }
                            )
                            documents.append(doc)
                            
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Error parsing {json_file}: {e}")
        
        logger.info(f"Slack ingestor: parsed {len(documents)} messages")
        self.documents = documents
        return documents
    
    def _load_user_map(self) -> dict:
        """Load user ID → display name mapping."""
        users_file = self.source_dir / "users.json"
        if not users_file.exists():
            # Try parent directory
            users_file = self.source_dir.parent / "users.json"
        
        if users_file.exists():
            with open(users_file, "r") as f:
                users = json.load(f)
            return {
                u["id"]: u.get("real_name", u.get("name", u["id"]))
                for u in users
            }
        return {}


class WhatsAppIngestor(BaseIngestor):
    """
    Parse WhatsApp .txt exports.
    
    Standard format:
    DD/MM/YYYY, HH:MM - Name: Message text here
    DD/MM/YYYY, HH:MM - Name: Another message
    
    Also handles:
    [DD/MM/YYYY, HH:MM:SS] Name: Message
    MM/DD/YY, HH:MM AM/PM - Name: Message
    """
    
    # Multiple date formats WhatsApp uses across regions
    PATTERNS = [
        # DD/MM/YYYY, HH:MM - Name: Message
        re.compile(
            r"(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\s*[-–]\s*(.+?):\s*(.*)",
            re.IGNORECASE
        ),
        # [DD/MM/YYYY, HH:MM:SS] Name: Message
        re.compile(
            r"\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.+?):\s*(.*)",
            re.IGNORECASE
        ),
    ]
    
    DATE_FORMATS = [
        "%d/%m/%Y, %H:%M",
        "%m/%d/%Y, %H:%M",
        "%d/%m/%y, %H:%M",
        "%m/%d/%y, %I:%M %p",
        "%d/%m/%Y, %H:%M:%S",
    ]
    
    def ingest(self) -> list[Document]:
        if not self.validate():
            return []
        
        documents = []
        
        for txt_file in sorted(self.source_dir.glob("*.txt")):
            chat_name = txt_file.stem  # e.g., "WhatsApp Chat with John"
            
            try:
                # Try different encodings
                content = None
                for encoding in ["utf-8", "utf-8-sig", "latin-1"]:
                    try:
                        content = txt_file.read_text(encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if not content:
                    continue
                
                current_msg = None
                
                for line in content.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Try each pattern
                    matched = False
                    for pattern in self.PATTERNS:
                        match = pattern.match(line)
                        if match:
                            # Save previous message
                            if current_msg:
                                documents.append(current_msg)
                            
                            date_str, time_str, author, text = match.groups()
                            timestamp = self._parse_datetime(f"{date_str}, {time_str}")
                            
                            current_msg = Document(
                                content=text,
                                source_type=SourceType.WHATSAPP,
                                source_file=str(txt_file),
                                doc_id=self._generate_doc_id("whatsapp", len(documents), f"{chat_name}"),
                                timestamp=timestamp,
                                category=DataCategory.COMMUNICATION_STYLE,
                                author=author.strip(),
                                is_self=self._is_owner_message(author.strip()),
                                conversation_id=f"whatsapp:{chat_name}",
                                metadata={"chat": chat_name}
                            )
                            matched = True
                            break
                    
                    if not matched and current_msg:
                        # Continuation of previous message
                        current_msg.content += f"\n{line}"
                
                # Don't forget the last message
                if current_msg:
                    documents.append(current_msg)
                    
            except Exception as e:
                logger.warning(f"Error parsing {txt_file}: {e}")
        
        logger.info(f"WhatsApp ingestor: parsed {len(documents)} messages")
        self.documents = documents
        return documents
    
    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        return None


class DiscordIngestor(BaseIngestor):
    """
    Parse Discord exports (from DiscordChatExporter — JSON format).
    
    Format:
    {
        "guild": {...},
        "channel": {...},
        "messages": [
            {
                "id": "...",
                "content": "message text",
                "author": {"name": "...", "id": "..."},
                "timestamp": "2024-01-01T12:00:00+00:00"
            }
        ]
    }
    """
    
    def ingest(self) -> list[Document]:
        if not self.validate():
            return []
        
        documents = []
        
        for json_file in sorted(self.source_dir.glob("**/*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                channel_name = data.get("channel", {}).get("name", json_file.stem)
                guild_name = data.get("guild", {}).get("name", "DM")
                messages = data.get("messages", [])
                
                for i, msg in enumerate(messages):
                    text = msg.get("content", "").strip()
                    if not text:
                        continue
                    
                    author_data = msg.get("author", {})
                    author = author_data.get("name", "unknown")
                    
                    timestamp = None
                    ts_str = msg.get("timestamp", "")
                    if ts_str:
                        try:
                            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        except ValueError:
                            pass
                    
                    doc = Document(
                        content=text,
                        source_type=SourceType.DISCORD,
                        source_file=str(json_file),
                        doc_id=self._generate_doc_id("discord", i, msg.get("id", "")),
                        timestamp=timestamp,
                        category=DataCategory.COMMUNICATION_STYLE,
                        author=author,
                        is_self=self._is_owner_message(author),
                        conversation_id=f"discord:{guild_name}:{channel_name}",
                        metadata={
                            "guild": guild_name,
                            "channel": channel_name,
                            "attachments": len(msg.get("attachments", [])),
                        }
                    )
                    documents.append(doc)
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error parsing {json_file}: {e}")
        
        logger.info(f"Discord ingestor: parsed {len(documents)} messages")
        self.documents = documents
        return documents


class KeybaseIngestor(BaseIngestor):
    """
    Parse Keybase chat exports (JSON).
    
    Keybase was specifically mentioned in the original system as one of the
    platforms where the original bot was deployed.
    """
    
    def ingest(self) -> list[Document]:
        if not self.validate():
            return []
        
        documents = []
        
        for json_file in sorted(self.source_dir.glob("**/*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Keybase export format varies — handle both array and object
                messages = data if isinstance(data, list) else data.get("messages", [])
                conv_name = json_file.stem
                
                for i, msg in enumerate(messages):
                    # Handle nested message structure
                    msg_body = msg.get("msg", msg) if isinstance(msg, dict) else {}
                    content = msg_body.get("content", {})
                    
                    text = ""
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, dict):
                        text = content.get("text", {}).get("body", "")
                    
                    if not text.strip():
                        continue
                    
                    sender = msg_body.get("sender", {})
                    author = sender.get("username", "unknown") if isinstance(sender, dict) else str(sender)
                    
                    doc = Document(
                        content=text.strip(),
                        source_type=SourceType.KEYBASE,
                        source_file=str(json_file),
                        doc_id=self._generate_doc_id("keybase", i, conv_name),
                        category=DataCategory.COMMUNICATION_STYLE,
                        author=author,
                        is_self=self._is_owner_message(author),
                        conversation_id=f"keybase:{conv_name}",
                        metadata={"conversation": conv_name}
                    )
                    documents.append(doc)
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error parsing {json_file}: {e}")
        
        logger.info(f"Keybase ingestor: parsed {len(documents)} messages")
        self.documents = documents
        return documents
