"""
Photo Ingestor — Processes images using vision models.

From the original 2020 system: "around 380 GB of datasets, including photos of 
my friends, family, buildings, etc."

Modern approach: Use vision models to generate rich text descriptions
of each photo, then embed those descriptions. The twin can then recall
and reference visual memories through language.
"""

import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from . import BaseIngestor, Document, SourceType, DataCategory


class PhotoIngestor(BaseIngestor):
    """
    Ingest photos by generating text descriptions via vision models.
    
    Supports: .jpg, .jpeg, .png, .webp, .gif
    
    For each image:
    1. Extract EXIF metadata (date, location if available)
    2. Send to vision model for description
    3. Store description + metadata as a Document
    """
    
    EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    
    def __init__(self, source_dir: str, owner_name: str = "Ade",
                 vision_provider: str = "anthropic", vision_model: str = "claude-sonnet-4-20250514"):
        super().__init__(source_dir, owner_name)
        self.vision_provider = vision_provider
        self.vision_model = vision_model
    
    def ingest(self) -> list[Document]:
        if not self.validate():
            return []
        
        documents = []
        image_files = []
        
        for ext in self.EXTENSIONS:
            image_files.extend(self.source_dir.glob(f"**/*{ext}"))
            image_files.extend(self.source_dir.glob(f"**/*{ext.upper()}"))
        
        image_files = sorted(set(image_files))
        logger.info(f"Found {len(image_files)} images to process")
        
        for i, img_path in enumerate(image_files):
            try:
                # Extract metadata
                metadata = self._extract_metadata(img_path)
                
                # Generate description using vision model
                description = self._describe_image(img_path)
                
                if not description:
                    description = f"Photo: {img_path.name}"
                
                # Build the document
                timestamp = metadata.get("date_taken")
                
                doc = Document(
                    content=description,
                    source_type=SourceType.PHOTO,
                    source_file=str(img_path),
                    doc_id=self._generate_doc_id("photo", i, img_path.name),
                    timestamp=timestamp,
                    category=DataCategory.PERSONAL_STORIES,
                    is_self=True,
                    metadata={
                        "filename": img_path.name,
                        "file_size_kb": img_path.stat().st_size // 1024,
                        **{k: v for k, v in metadata.items() if k != "date_taken"},
                    }
                )
                documents.append(doc)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(image_files)} images")
                    
            except Exception as e:
                logger.warning(f"Error processing image {img_path}: {e}")
        
        logger.info(f"Photo ingestor: processed {len(documents)} images")
        self.documents = documents
        return documents
    
    def _extract_metadata(self, img_path: Path) -> dict:
        """Extract EXIF and file metadata from image."""
        metadata = {}
        
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            with Image.open(img_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format
                
                exif_data = img._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        
                        if tag_name == "DateTimeOriginal":
                            try:
                                metadata["date_taken"] = datetime.strptime(
                                    str(value), "%Y:%m:%d %H:%M:%S"
                                )
                            except ValueError:
                                pass
                        elif tag_name == "GPSInfo":
                            metadata["has_gps"] = True
                        elif tag_name == "ImageDescription":
                            metadata["exif_description"] = str(value)
                            
        except Exception as e:
            logger.debug(f"Could not extract EXIF from {img_path.name}: {e}")
        
        # Fall back to file modification time
        if "date_taken" not in metadata:
            try:
                mtime = os.path.getmtime(img_path)
                metadata["date_taken"] = datetime.fromtimestamp(mtime)
            except OSError:
                pass
        
        return metadata
    
    def _describe_image(self, img_path: Path) -> Optional[str]:
        """Generate a text description of the image using a vision model."""
        
        try:
            # Read and encode the image
            with open(img_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Determine media type
            ext = img_path.suffix.lower()
            media_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            media_type = media_types.get(ext, "image/jpeg")
            
            if self.vision_provider == "anthropic":
                return self._describe_with_anthropic(image_data, media_type)
            elif self.vision_provider == "openai":
                return self._describe_with_openai(image_data, media_type)
            else:
                return self._describe_with_ollama(img_path)
                
        except Exception as e:
            logger.warning(f"Vision model error for {img_path.name}: {e}")
            return None
    
    def _describe_with_anthropic(self, image_data: str, media_type: str) -> Optional[str]:
        """Use Claude's vision to describe the image."""
        try:
            import anthropic
            
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=self.vision_model,
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            }
                        },
                        {
                            "type": "text",
                            "text": (
                                "Describe this personal photo in detail for a memory system. "
                                "Include: who/what is in the photo, the setting/location, "
                                "the mood/atmosphere, any notable details. "
                                "Write as if recording a personal memory. "
                                "Be specific and descriptive in 2-3 sentences."
                            )
                        }
                    ]
                }]
            )
            return response.content[0].text
            
        except Exception as e:
            logger.warning(f"Anthropic vision error: {e}")
            return None
    
    def _describe_with_openai(self, image_data: str, media_type: str) -> Optional[str]:
        """Use GPT-4V to describe the image."""
        try:
            from openai import OpenAI
            
            client = OpenAI()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": (
                                "Describe this personal photo in detail for a memory system. "
                                "Include: who/what is in the photo, the setting/location, "
                                "the mood/atmosphere, any notable details. "
                                "Write as if recording a personal memory. 2-3 sentences."
                            )
                        }
                    ]
                }]
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"OpenAI vision error: {e}")
            return None
    
    def _describe_with_ollama(self, img_path: Path) -> Optional[str]:
        """Use local Ollama with llava for image description."""
        try:
            import ollama
            
            response = ollama.chat(
                model="llava",
                messages=[{
                    "role": "user",
                    "content": (
                        "Describe this personal photo in detail for a memory system. "
                        "2-3 sentences covering who/what, where, and the mood."
                    ),
                    "images": [str(img_path)]
                }]
            )
            return response["message"]["content"]
            
        except Exception as e:
            logger.warning(f"Ollama vision error: {e}")
            return None
