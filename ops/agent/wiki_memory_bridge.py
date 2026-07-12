#!/usr/bin/env python3
"""
Wiki Memory Bridge — Integrate wiki into claude memory system (Task I0000000037)

Bridges wiki_search_engine.py output with memory_ingest and memory_aging systems.
Enables agents to search and reference wiki knowledge in their context.

Pipeline:
1. Load wiki chunks from search engine
2. Create memory entries with wiki content
3. Track staleness via memory_aging
4. Enable context injection for agents
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

sys.path.insert(0, str(Path(__file__).parent))

try:
    from wiki_search_engine import WikiSearchEngine
except ImportError:
    WikiSearchEngine = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

REPO_DIR = Path("/opt/YOUR-PROJECT")
MEMORY_DIR = REPO_DIR / ".memory"


@dataclass
class WikiMemoryEntry:
    """Memory entry created from wiki content."""
    memory_id: str
    source: str  # 'wiki'
    source_id: str  # incident_id or entity_name
    type: str  # 'incident' or 'entity'
    section: str  # Which section (summary, prevention, etc)
    content: str  # The actual content
    metadata: Dict
    created_at: str
    accessed_at: str
    relevance: float  # How relevant to recent work


class WikiMemoryBridge:
    """Bridge between wiki system and memory."""

    def __init__(self):
        self.search_engine = None
        self.memory_dir = MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_index = self._load_memory_index()

        # Initialize search engine if available
        if WikiSearchEngine:
            try:
                self.search_engine = WikiSearchEngine()
                self.search_engine.index_all_wiki_pages()
                logger.info("✓ Wiki search engine initialized")
            except Exception as e:
                logger.warning(f"Wiki search engine not ready: {e}")

    def _load_memory_index(self) -> Dict:
        """Load memory index from disk."""
        index_file = self.memory_dir / "memory_index.json"
        if index_file.exists():
            with open(index_file) as f:
                return json.load(f)
        return {}

    def _save_memory_index(self):
        """Save memory index to disk."""
        index_file = self.memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump(self.memory_index, f, indent=2)

    def ingest_wiki_to_memory(self) -> Dict:
        """Load all wiki content into memory system."""
        if not self.search_engine:
            logger.error("Search engine not available")
            return {'status': 'error', 'message': 'Search engine not initialized'}

        try:
            stats = {'entries_created': 0, 'incidents': 0, 'entities': 0}

            # Get all wiki chunks (WikiChunk objects, not dicts)
            for chunk_id, chunk in self.search_engine.index.chunks.items():
                # Create memory entry from WikiChunk dataclass
                memory_id = f"wiki_{chunk.chunk_id}"
                entry = {
                    'memory_id': memory_id,
                    'source': 'wiki',
                    'source_id': chunk.metadata.get('incident_id') or chunk.metadata.get('entity_name', 'unknown'),
                    'type': chunk.page_type,
                    'section': chunk.section_title,
                    'content': chunk.content,
                    'metadata': chunk.metadata,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'accessed_at': datetime.now(timezone.utc).isoformat(),
                    'relevance': 1.0  # Will be updated by usage patterns
                }

                self.memory_index[memory_id] = entry
                stats['entries_created'] += 1

                if chunk.page_type == 'incident':
                    stats['incidents'] += 1
                else:
                    stats['entities'] += 1

            self._save_memory_index()
            logger.info(f"✓ Ingested {stats['entries_created']} wiki entries to memory")
            return stats

        except Exception as e:
            logger.error(f"Error ingesting wiki to memory: {e}")
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'error': str(e)}

    def query_wiki_from_context(self, query: str, agent_id: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """Query wiki for agent context injection."""
        if not self.search_engine:
            return []

        try:
            # Search wiki
            results = self.search_engine.search(query, limit)

            # Convert to memory format
            context = []
            for result in results:
                memory_id = f"wiki_{result['chunk_id']}"

                # Update accessed_at if in memory
                if memory_id in self.memory_index:
                    self.memory_index[memory_id]['accessed_at'] = datetime.now(timezone.utc).isoformat()

                context.append({
                    'type': result['page_type'],
                    'section': result['section'],
                    'content': result['content'],
                    'source': f"wiki/{result['metadata'].get('service', 'unknown')}",
                    'score': result.get('score', 0)
                })

            self._save_memory_index()
            logger.info(f"✓ Query '{query}' returned {len(context)} memory entries")
            return context

        except Exception as e:
            logger.error(f"Error querying wiki for context: {e}")
            return []

    def sync_memory_aging(self) -> Dict:
        """Integrate with memory_aging for content lifecycle."""
        try:
            stats = {'stale': 0, 'refreshed': 0, 'active': 0}

            now = datetime.now(timezone.utc)

            for memory_id, entry in self.memory_index.items():
                accessed_at = datetime.fromisoformat(entry['accessed_at'])
                days_since_access = (now - accessed_at).days

                # Mark stale after 90 days of no access
                if days_since_access > 90:
                    entry['stale'] = True
                    stats['stale'] += 1
                else:
                    entry['stale'] = False
                    stats['active'] += 1

            self._save_memory_index()
            logger.info(f"✓ Memory aging sync: {stats['stale']} stale, {stats['active']} active")
            return stats

        except Exception as e:
            logger.error(f"Error syncing memory aging: {e}")
            return {'status': 'error'}

    def get_memory_stats(self) -> Dict:
        """Get statistics about wiki memory."""
        stats = {
            'total_entries': len(self.memory_index),
            'incidents': sum(1 for e in self.memory_index.values() if e.get('type') == 'incident'),
            'entities': sum(1 for e in self.memory_index.values() if e.get('type') == 'entity'),
            'stale': sum(1 for e in self.memory_index.values() if e.get('stale', False)),
            'active': sum(1 for e in self.memory_index.values() if not e.get('stale', False))
        }
        return stats


if __name__ == "__main__":
    logger.info("Wiki Memory Bridge Initialization")

    bridge = WikiMemoryBridge()

    # Ingest wiki to memory
    logger.info("\n=== Ingesting Wiki to Memory ===")
    ingest_result = bridge.ingest_wiki_to_memory()
    print(f"Ingestion result: {ingest_result}")

    # Test context queries
    logger.info("\n=== Testing Context Injection ===")
    queries = ["prevention", "timeline", "evidence"]
    for query in queries:
        context = bridge.query_wiki_from_context(query, limit=2)
        print(f"Query '{query}': {len(context)} results")

    # Show memory stats
    logger.info("\n=== Memory Statistics ===")
    stats = bridge.get_memory_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # Sync aging
    logger.info("\n=== Memory Aging Sync ===")
    aging = bridge.sync_memory_aging()
    print(f"Aging sync: {aging}")

    logger.info("\n✓ Wiki Memory Bridge Ready")
