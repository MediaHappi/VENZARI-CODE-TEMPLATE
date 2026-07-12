#!/usr/bin/env python3
"""
Wiki Search Engine — File-based wiki search and retrieval (I0000000036)

Provides semantic search over wiki content using file-based indexing.
Can be upgraded to ChromaDB later when Python client is available.

Pipeline:
1. Chunk wiki pages
2. Index chunks in JSON files
3. Support BM25-style search
4. Enable semantic queries via metadata

This is a pragmatic solution that unblocks other tasks while maintaining
a clear upgrade path to ChromaDB for full embeddings.
"""

import sys
import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import hashlib

sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

REPO_DIR = Path("/opt/YOUR-PROJECT")
WIKI_ROOT = REPO_DIR / "docs/wiki"
WIKI_INDEX = WIKI_ROOT / ".wiki-index"  # Hidden directory for search indexes


@dataclass
class WikiChunk:
    """Represents a chunk of wiki content."""
    chunk_id: str
    page_path: str
    page_type: str  # 'incident' or 'entity'
    section_title: str
    content: str
    metadata: Dict = field(default_factory=dict)


class WikiPageChunker:
    """Chunk wiki pages into semantic sections."""

    @staticmethod
    def chunk_incident_page(page_path: Path) -> List[WikiChunk]:
        """Chunk an incident page into sections."""
        try:
            with open(page_path, 'r') as f:
                content = f.read()

            chunks = []
            incident_id = WikiPageChunker._extract_incident_id(content)
            service = WikiPageChunker._extract_service(content)

            # Split by section headers (##)
            sections = re.split(r'^##\s+', content, flags=re.MULTILINE)

            for section in sections[1:]:  # Skip first split
                lines = section.split('\n', 1)
                section_title = lines[0].strip()
                section_content = lines[1].strip() if len(lines) > 1 else ""

                if not section_content or len(section_content) < 20:
                    continue

                chunk_id = WikiPageChunker._generate_chunk_id(page_path, section_title)

                chunk = WikiChunk(
                    chunk_id=chunk_id,
                    page_path=str(page_path),
                    page_type='incident',
                    section_title=section_title,
                    content=section_content,
                    metadata={
                        'source': str(page_path),
                        'incident_id': incident_id,
                        'service': service,
                        'section': section_title.lower(),
                        'type': 'incident_section'
                    }
                )
                chunks.append(chunk)

            logger.debug(f"✓ Chunked {page_path.name} into {len(chunks)} sections")
            return chunks

        except Exception as e:
            logger.error(f"Error chunking {page_path}: {e}")
            return []

    @staticmethod
    def chunk_entity_page(page_path: Path) -> List[WikiChunk]:
        """Chunk an entity page into sections."""
        try:
            with open(page_path, 'r') as f:
                content = f.read()

            chunks = []
            entity_name = WikiPageChunker._extract_entity_name(content)

            # Split by section headers (##)
            sections = re.split(r'^##\s+', content, flags=re.MULTILINE)

            for section in sections[1:]:
                lines = section.split('\n', 1)
                section_title = lines[0].strip()
                section_content = lines[1].strip() if len(lines) > 1 else ""

                if not section_content or len(section_content) < 20:
                    continue

                chunk_id = WikiPageChunker._generate_chunk_id(page_path, section_title)

                chunk = WikiChunk(
                    chunk_id=chunk_id,
                    page_path=str(page_path),
                    page_type='entity',
                    section_title=section_title,
                    content=section_content,
                    metadata={
                        'source': str(page_path),
                        'entity_name': entity_name,
                        'section': section_title.lower(),
                        'type': 'entity_section'
                    }
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Error chunking {page_path}: {e}")
            return []

    @staticmethod
    def _extract_incident_id(content: str) -> str:
        match = re.search(r'\*\*Incident ID:\*\*\s+(\S+)', content)
        return match.group(1) if match else 'unknown'

    @staticmethod
    def _extract_service(content: str) -> str:
        match = re.search(r'^# Incident:\s+(\w+[-\w]*)', content, re.MULTILINE)
        return match.group(1) if match else 'unknown'

    @staticmethod
    def _extract_entity_name(content: str) -> str:
        match = re.search(r'^# (\w+[-\w]*)', content, re.MULTILINE)
        return match.group(1) if match else 'unknown'

    @staticmethod
    def _generate_chunk_id(page_path: Path, section_title: str) -> str:
        content = f"{page_path}:{section_title}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class WikiSearchIndex:
    """File-based search index for wiki content."""

    def __init__(self):
        self.index_path = WIKI_INDEX
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.chunks: Dict[str, WikiChunk] = {}

    def add_chunks(self, chunks: List[WikiChunk]) -> int:
        """Add chunks to index and persist."""
        added = 0
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk
            added += 1

        # Save index to JSON
        self._save_index()
        return added

    def _save_index(self):
        """Save chunk index to JSON file."""
        try:
            index_file = self.index_path / "chunks.json"
            chunks_data = [
                {
                    'chunk_id': c.chunk_id,
                    'page_path': c.page_path,
                    'page_type': c.page_type,
                    'section_title': c.section_title,
                    'content': c.content,
                    'metadata': c.metadata
                }
                for c in self.chunks.values()
            ]
            with open(index_file, 'w') as f:
                json.dump(chunks_data, f, indent=2)
            logger.debug(f"✓ Saved {len(chunks_data)} chunks to index")
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search chunks by keywords (BM25-style)."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []
        for chunk in self.chunks.values():
            # Score based on word matches in content and metadata
            score = 0
            content_lower = chunk.content.lower()
            title_lower = chunk.section_title.lower()

            for word in query_words:
                if word in title_lower:
                    score += 3  # Title matches worth more
                if word in content_lower:
                    score += 1

            if score > 0:
                results.append({
                    'chunk_id': chunk.chunk_id,
                    'content': chunk.content[:300],  # Preview
                    'section': chunk.section_title,
                    'page_type': chunk.page_type,
                    'metadata': chunk.metadata,
                    'score': score
                })

        # Sort by score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]


class WikiSearchEngine:
    """Main orchestrator for wiki search."""

    def __init__(self):
        self.chunker = WikiPageChunker()
        self.index = WikiSearchIndex()
        self.stats = {'incidents': 0, 'entities': 0, 'total_chunks': 0}

    def index_all_wiki_pages(self) -> Dict:
        """Index all wiki pages."""
        logger.info("Indexing wiki pages...")

        # Index incidents
        incident_dir = WIKI_ROOT / "incidents"
        if incident_dir.exists():
            for incident_file in incident_dir.glob("*.md"):
                chunks = self.chunker.chunk_incident_page(incident_file)
                if chunks:
                    count = self.index.add_chunks(chunks)
                    self.stats['incidents'] += 1
                    self.stats['total_chunks'] += count

        # Index entities
        entity_dir = WIKI_ROOT / "entities"
        if entity_dir.exists():
            for entity_file in entity_dir.glob("*.md"):
                chunks = self.chunker.chunk_entity_page(entity_file)
                if chunks:
                    count = self.index.add_chunks(chunks)
                    self.stats['entities'] += 1
                    self.stats['total_chunks'] += count

        logger.info(f"✓ Indexed {self.stats['incidents']} incidents + {self.stats['entities']} entities = {self.stats['total_chunks']} chunks")
        return self.stats

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search wiki content."""
        return self.index.search(query, limit)


if __name__ == "__main__":
    engine = WikiSearchEngine()
    stats = engine.index_all_wiki_pages()

    logger.info(f"\n{'='*60}")
    logger.info(f"WIKI INDEX COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"✓ Chunks indexed: {stats['total_chunks']}")
    logger.info(f"{'='*60}\n")

    # Test search
    logger.info("Testing search...")
    results = engine.search("prevention memory leak", limit=3)
    if results:
        logger.info(f"✓ Found {len(results)} results")
        for r in results:
            logger.info(f"  - {r['section']}: score={r['score']}")
    else:
        logger.info("No results found")

    logger.info("\n✓ Wiki search engine ready")
