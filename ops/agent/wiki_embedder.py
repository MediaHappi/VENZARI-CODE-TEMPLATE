#!/usr/bin/env python3
"""
Wiki Embedder — Chunk wiki pages and create ChromaDB embeddings (Task I0000000036)

Bridges opensre_wiki_ingest.py output with ChromaDB for semantic search.

Pipeline:
1. Load wiki markdown pages
2. Chunk by semantic boundaries (sections)
3. Create embeddings for each chunk
4. Store in ChromaDB with metadata
5. Enable semantic search queries

Uses existing ChromaDB instance (127.0.0.1:8001)
Collections: 'wiki-incidents', 'wiki-entities'
"""

import sys
import os
import re
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

REPO_DIR = Path("/opt/YOUR-PROJECT")
WIKI_ROOT = REPO_DIR / "docs/wiki"

# ChromaDB configuration
CHROMADB_HOST = "127.0.0.1"
CHROMADB_PORT = 8001
CHROMADB_API_VERSION = "/v2"  # Use v2 API (v1 is deprecated)
COLLECTIONS = {
    'incidents': 'wiki-incidents',
    'entities': 'wiki-entities'
}


@dataclass
class WikiChunk:
    """Represents a chunk of wiki content for embedding."""
    chunk_id: str  # Stable hash-based ID
    page_path: str  # Source wiki page path
    page_type: str  # 'incident' or 'entity'
    section_title: str  # Section heading
    content: str  # Markdown content
    metadata: Dict = field(default_factory=dict)  # source, entity_name, incident_id, service, etc.

    def to_dict(self):
        return {
            'id': self.chunk_id,
            'page_path': str(self.page_path),
            'page_type': self.page_type,
            'section_title': self.section_title,
            'content': self.content,
            'metadata': self.metadata
        }


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

            for i, section in enumerate(sections[1:], 1):  # Skip first split (before first ##)
                lines = section.split('\n', 1)
                section_title = lines[0].strip()
                section_content = lines[1].strip() if len(lines) > 1 else ""

                if not section_content or len(section_content) < 20:
                    continue

                chunk_id = WikiPageChunker._generate_chunk_id(page_path, section_title)

                chunk = WikiChunk(
                    chunk_id=chunk_id,
                    page_path=page_path,
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

            for i, section in enumerate(sections[1:], 1):  # Skip first split
                lines = section.split('\n', 1)
                section_title = lines[0].strip()
                section_content = lines[1].strip() if len(lines) > 1 else ""

                if not section_content or len(section_content) < 20:
                    continue

                chunk_id = WikiPageChunker._generate_chunk_id(page_path, section_title)

                chunk = WikiChunk(
                    chunk_id=chunk_id,
                    page_path=page_path,
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

            logger.debug(f"✓ Chunked {page_path.name} into {len(chunks)} sections")
            return chunks

        except Exception as e:
            logger.error(f"Error chunking {page_path}: {e}")
            return []

    @staticmethod
    def _extract_incident_id(content: str) -> str:
        """Extract incident ID from content."""
        match = re.search(r'\*\*Incident ID:\*\*\s+(\S+)', content)
        return match.group(1) if match else 'unknown'

    @staticmethod
    def _extract_service(content: str) -> str:
        """Extract service name from incident page."""
        match = re.search(r'^# Incident:\s+(\w+[-\w]*)', content, re.MULTILINE)
        return match.group(1) if match else 'unknown'

    @staticmethod
    def _extract_entity_name(content: str) -> str:
        """Extract entity name from entity page."""
        match = re.search(r'^# (\w+[-\w]*)', content, re.MULTILINE)
        return match.group(1) if match else 'unknown'

    @staticmethod
    def _generate_chunk_id(page_path: Path, section_title: str) -> str:
        """Generate stable chunk ID."""
        content = f"{page_path}:{section_title}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class ChromaDBConnector:
    """Interface to ChromaDB for storing and retrieving wiki embeddings."""

    def __init__(self, host: str = CHROMADB_HOST, port: int = CHROMADB_PORT):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self.client = None
        self.embedding_fn = None
        self._connect()

    def _connect(self):
        """Connect to ChromaDB via HTTP client (requests library)."""
        try:
            import requests
            # Simple connection test by trying to get API version
            response = requests.get(f"{self.url}/api", timeout=5)
            # Accept any 2xx or 4xx response (4xx means API exists but endpoint not found)
            if response.status_code >= 500:
                raise Exception(f"ChromaDB error: {response.status_code}")
            self.client = requests  # Use requests library for HTTP calls
            logger.info(f"✓ Connected to ChromaDB at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise

    def _get_or_create_collection(self, collection_name: str):
        """Get or create ChromaDB collection via HTTP API (v2)."""
        try:
            import requests
            # ChromaDB v2 uses POST to /v2/collections with "get_or_create" action
            response = requests.post(
                f"{self.url}/api/v2/collections",
                json={
                    "name": collection_name,
                    "get_or_create": True,
                    "metadata": {"hnsw:space": "cosine"}
                },
                timeout=5
            )
            if response.status_code in [200, 201]:
                logger.info(f"✓ Using collection: {collection_name}")
                return collection_name
            else:
                logger.error(f"ChromaDB error ({response.status_code}): {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error with collection {collection_name}: {e}")
            return None

    def embed_chunks(self, chunks: List[WikiChunk], collection_type: str = 'incidents') -> Dict:
        """Embed wiki chunks and store in ChromaDB via HTTP API (v2)."""
        if not chunks:
            return {'status': 'no_chunks', 'count': 0}

        collection_name = COLLECTIONS.get(collection_type, 'wiki-incidents')
        collection = self._get_or_create_collection(collection_name)

        if not collection:
            return {'status': 'error', 'error': 'Failed to create collection'}

        try:
            import requests
            # Prepare data for ChromaDB
            ids = [chunk.chunk_id for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]

            # Add documents to ChromaDB via v2 HTTP API
            response = requests.post(
                f"{self.url}/api/v2/collections/{collection_name}/add",
                json={
                    "ids": ids,
                    "documents": documents,
                    "metadatas": metadatas
                },
                timeout=10
            )

            if response.status_code in [200, 201]:
                logger.info(f"✓ Embedded {len(chunks)} chunks in {collection_name}")
                return {
                    'status': 'success',
                    'collection': collection_name,
                    'chunks_embedded': len(chunks)
                }
            else:
                logger.error(f"ChromaDB error ({response.status_code}): {response.text}")
                return {'status': 'error', 'error': f"Status {response.status_code}: {response.text}"}

        except Exception as e:
            logger.error(f"Error embedding chunks: {e}")
            return {'status': 'error', 'error': str(e)}

    def search(self, query: str, collection_type: str = 'incidents', limit: int = 5) -> List[Dict]:
        """Search wiki content via ChromaDB HTTP API (v2)."""
        try:
            import requests
            collection_name = COLLECTIONS.get(collection_type, 'wiki-incidents')

            # Query via v2 HTTP API
            response = requests.post(
                f"{self.url}/api/v2/collections/{collection_name}/query",
                json={
                    "query_texts": [query],
                    "n_results": limit
                },
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Search error ({response.status_code}): {response.text}")
                return []

            results = response.json()

            # Format results
            formatted = []
            if results and 'ids' in results and len(results['ids']) > 0:
                for i, chunk_id in enumerate(results['ids'][0]):
                    formatted.append({
                        'chunk_id': chunk_id,
                        'content': results['documents'][0][i] if results['documents'] else '',
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0
                    })

            logger.info(f"✓ Search found {len(formatted)} results")
            return formatted

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []


class WikiEmbedder:
    """Main orchestrator for wiki embedding."""

    def __init__(self):
        self.chunker = WikiPageChunker()
        self.db = ChromaDBConnector()
        self.stats = {'incidents': 0, 'entities': 0, 'total_chunks': 0}

    def embed_all_wiki_pages(self) -> Dict:
        """Embed all wiki pages into ChromaDB."""
        logger.info("Starting wiki embedding into ChromaDB...")

        # Embed incidents
        incident_dir = WIKI_ROOT / "incidents"
        if incident_dir.exists():
            incident_files = list(incident_dir.glob("*.md"))
            for incident_file in incident_files:
                chunks = self.chunker.chunk_incident_page(incident_file)
                if chunks:
                    result = self.db.embed_chunks(chunks, 'incidents')
                    if result['status'] == 'success':
                        self.stats['incidents'] += 1
                        self.stats['total_chunks'] += result['chunks_embedded']

        # Embed entities
        entity_dir = WIKI_ROOT / "entities"
        if entity_dir.exists():
            entity_files = list(entity_dir.glob("*.md"))
            for entity_file in entity_files:
                chunks = self.chunker.chunk_entity_page(entity_file)
                if chunks:
                    result = self.db.embed_chunks(chunks, 'entities')
                    if result['status'] == 'success':
                        self.stats['entities'] += 1
                        self.stats['total_chunks'] += result['chunks_embedded']

        logger.info(f"\n{'='*60}")
        logger.info(f"WIKI EMBEDDING COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"✓ Incidents embedded: {self.stats['incidents']}")
        logger.info(f"✓ Entities embedded: {self.stats['entities']}")
        logger.info(f"✓ Total chunks: {self.stats['total_chunks']}")
        logger.info(f"{'='*60}")

        return self.stats

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search wiki content."""
        logger.info(f"Searching for: {query}")

        # Search both collections
        incident_results = self.db.search(query, 'incidents', limit)
        entity_results = self.db.search(query, 'entities', limit // 2)

        combined = incident_results + entity_results
        return combined[:limit]


if __name__ == "__main__":
    logger.info("Wiki Embedder - ChromaDB Integration")

    embedder = WikiEmbedder()
    stats = embedder.embed_all_wiki_pages()

    # Test search
    logger.info("\nTesting search functionality...")
    results = embedder.search("prevention measures for memory leak")
    if results:
        logger.info(f"✓ Search returned {len(results)} results")
        for r in results[:2]:
            logger.info(f"  - {r['metadata'].get('section', 'unknown')}: {r['content'][:100]}...")
    else:
        logger.warning("⚠️ No search results found")

    logger.info("\n✓ Wiki embedding complete and tested")
