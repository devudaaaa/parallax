"""
Text Processor — Clean, enrich, and prepare documents for embedding.

Handles:
- Text cleaning and normalization
- Communication style extraction (for personality replication)
- Content classification for authorization tiers
- Chunking optimization
"""

import re
from collections import Counter
from loguru import logger

from phase1_data_pipeline.ingestors import Document, DataCategory


class TextProcessor:
    """Process and enrich documents before embedding."""
    
    # Patterns indicating personal/private content
    PRIVATE_INDICATORS = [
        r"don't tell anyone", r"between us", r"secret", r"private",
        r"confidential", r"password", r"account number",
    ]
    
    EMOTIONAL_INDICATORS = [
        r"i feel", r"i'm afraid", r"i love", r"i hate", r"struggling",
        r"worried", r"excited", r"disappointed", r"grateful", r"faith",
        r"believe", r"god", r"devudaaaa", r"prayer",
    ]
    
    def process_batch(self, documents: list[Document]) -> list[Document]:
        """Process a batch of documents."""
        processed = []
        
        for doc in documents:
            processed_doc = self.process(doc)
            if processed_doc:
                processed.append(processed_doc)
        
        logger.info(f"Processed {len(processed)}/{len(documents)} documents")
        return processed
    
    def process(self, doc: Document) -> Document | None:
        """Process a single document."""
        # Clean the text
        doc.content = self._clean_text(doc.content)
        
        # Skip empty or too-short documents
        if len(doc.content.strip()) < 10:
            return None
        
        # Enrich with style analysis (for owner's messages)
        if doc.is_self:
            doc.formality = self._estimate_formality(doc.content)
            doc.tone = self._detect_tone(doc.content)
        
        # Classify for authorization
        doc = self._classify_access_tier(doc)
        
        return doc
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove URLs (keep the fact that a link was shared)
        text = re.sub(r"https?://\S+", "[link]", text)
        
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        
        # Remove common Slack/Discord formatting artifacts
        text = re.sub(r"<@\w+>", "[mention]", text)  # User mentions
        text = re.sub(r"<#\w+\|(\w+)>", r"#\1", text)  # Channel mentions
        text = re.sub(r":\w+:", "", text)  # Emoji codes (keep unicode emojis)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _estimate_formality(self, text: str) -> float:
        """
        Estimate formality level of text (0=casual, 1=formal).
        
        Used to build the twin's adaptive formality range —
        the twin should match the owner's formality in similar contexts.
        """
        casual_markers = [
            "lol", "haha", "omg", "nah", "yeah", "gonna", "wanna",
            "btw", "idk", "imo", "tbh", "lmao", "bruh", "ngl",
        ]
        formal_markers = [
            "therefore", "furthermore", "regarding", "pursuant",
            "accordingly", "nonetheless", "hereby", "shall",
        ]
        
        words = text.lower().split()
        if not words:
            return 0.5
        
        casual_count = sum(1 for w in words if w in casual_markers)
        formal_count = sum(1 for w in words if w in formal_markers)
        
        # Also check sentence structure
        has_contractions = bool(re.search(r"\w+n't|\w+'re|\w+'ll|\w+'ve", text.lower()))
        has_proper_punctuation = text.endswith((".","!","?"))
        starts_with_capital = text[0].isupper() if text else False
        
        score = 0.5
        score -= casual_count * 0.1
        score += formal_count * 0.1
        if has_contractions:
            score -= 0.05
        if has_proper_punctuation:
            score += 0.05
        if starts_with_capital:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _detect_tone(self, text: str) -> str:
        """Detect the emotional tone of the text."""
        text_lower = text.lower()
        
        tones = {
            "analytical": ["because", "therefore", "data", "analysis", "result", "evidence"],
            "humorous": ["haha", "lol", "joke", "funny", "😂", "😄"],
            "passionate": ["amazing", "incredible", "love", "absolutely", "!", "fantastic"],
            "reflective": ["wonder", "think about", "realize", "interesting", "curious"],
            "serious": ["important", "concern", "critical", "need to", "must"],
            "spiritual": ["faith", "believe", "god", "devudaaaa", "soul", "prayer", "miracle"],
        }
        
        scores = {}
        for tone, markers in tones.items():
            scores[tone] = sum(1 for m in markers if m in text_lower)
        
        if not any(scores.values()):
            return "neutral"
        
        return max(scores, key=scores.get)
    
    def _classify_access_tier(self, doc: Document) -> Document:
        """Classify document into authorization tier based on content."""
        content_lower = doc.content.lower()
        
        # Check for restricted content (never share)
        restricted_patterns = [
            r"password\s*[:=]", r"api[_\s]*key", r"ssn\s*[:=]",
            r"credit\s*card", r"account\s*number",
        ]
        for pattern in restricted_patterns:
            if re.search(pattern, content_lower):
                doc.access_tier = "private"
                return doc
        
        # Check for private indicators
        for pattern in self.PRIVATE_INDICATORS:
            if re.search(pattern, content_lower):
                doc.access_tier = "private"
                return doc
        
        # Check for emotional/deep content
        emotional_count = sum(
            1 for pattern in self.EMOTIONAL_INDICATORS
            if re.search(pattern, content_lower)
        )
        if emotional_count >= 2:
            doc.access_tier = "close"
            doc.category = DataCategory.DEEP_THOUGHTS
            return doc
        
        # Professional content is more public
        if doc.category == DataCategory.PROFESSIONAL:
            doc.access_tier = "public"
        elif doc.category == DataCategory.COMMUNICATION_STYLE:
            doc.access_tier = "friends"
        
        return doc


class StyleExtractor:
    """
    Extract communication style patterns from the owner's messages.
    
    This is the modern replacement for the neural network's 10K parameters.
    Instead of training a custom net, we extract style features and use
    them to prompt the LLM to match the owner's voice.
    """
    
    def __init__(self):
        self.style_profile = {
            "avg_message_length": 0,
            "vocabulary_richness": 0,
            "formality_distribution": [],
            "tone_distribution": {},
            "common_phrases": [],
            "emoji_usage": [],
            "response_patterns": [],
            "question_frequency": 0,
            "humor_frequency": 0,
        }
    
    def analyze(self, documents: list[Document]) -> dict:
        """Analyze a collection of the owner's messages to build a style profile."""
        
        owner_docs = [d for d in documents if d.is_self]
        if not owner_docs:
            logger.warning("No owner messages found for style analysis")
            return self.style_profile
        
        # Message length
        lengths = [len(d.content.split()) for d in owner_docs]
        self.style_profile["avg_message_length"] = sum(lengths) / len(lengths)
        
        # Vocabulary richness
        all_words = []
        for d in owner_docs:
            all_words.extend(d.content.lower().split())
        unique_ratio = len(set(all_words)) / len(all_words) if all_words else 0
        self.style_profile["vocabulary_richness"] = unique_ratio
        
        # Formality distribution
        formalities = [d.formality for d in owner_docs if d.formality > 0]
        self.style_profile["formality_distribution"] = {
            "mean": sum(formalities) / len(formalities) if formalities else 0.5,
            "min": min(formalities) if formalities else 0.3,
            "max": max(formalities) if formalities else 0.8,
        }
        
        # Tone distribution
        tones = [d.tone for d in owner_docs if d.tone]
        tone_counts = Counter(tones)
        total = sum(tone_counts.values()) or 1
        self.style_profile["tone_distribution"] = {
            t: c / total for t, c in tone_counts.most_common()
        }
        
        # Common phrases (bigrams and trigrams)
        from collections import Counter
        bigrams = []
        for d in owner_docs:
            words = d.content.lower().split()
            bigrams.extend(zip(words, words[1:]))
        common_bigrams = Counter(bigrams).most_common(20)
        self.style_profile["common_phrases"] = [
            " ".join(bg) for bg, count in common_bigrams if count > 2
        ]
        
        # Question frequency
        questions = sum(1 for d in owner_docs if "?" in d.content)
        self.style_profile["question_frequency"] = questions / len(owner_docs)
        
        # Humor frequency
        humor_docs = sum(1 for d in owner_docs if d.tone == "humorous")
        self.style_profile["humor_frequency"] = humor_docs / len(owner_docs)
        
        logger.info(f"Style analysis complete from {len(owner_docs)} messages")
        return self.style_profile
    
    def to_prompt_instructions(self) -> str:
        """Convert style profile into LLM prompt instructions."""
        profile = self.style_profile
        
        instructions = []
        instructions.append(f"Average message length: {profile['avg_message_length']:.0f} words")
        
        formality = profile.get("formality_distribution", {})
        if formality:
            instructions.append(
                f"Formality range: {formality.get('min', 0.3):.1f} to {formality.get('max', 0.8):.1f} "
                f"(average {formality.get('mean', 0.5):.1f})"
            )
        
        tone_dist = profile.get("tone_distribution", {})
        if tone_dist:
            top_tones = sorted(tone_dist.items(), key=lambda x: -x[1])[:3]
            tone_str = ", ".join(f"{t} ({v:.0%})" for t, v in top_tones)
            instructions.append(f"Primary tones: {tone_str}")
        
        phrases = profile.get("common_phrases", [])
        if phrases:
            instructions.append(f"Characteristic phrases: {', '.join(phrases[:10])}")
        
        if profile.get("humor_frequency", 0) > 0.1:
            instructions.append(f"Uses humor in ~{profile['humor_frequency']:.0%} of messages")
        
        if profile.get("question_frequency", 0) > 0.2:
            instructions.append(f"Frequently asks questions (~{profile['question_frequency']:.0%})")
        
        return "\n".join(instructions)
