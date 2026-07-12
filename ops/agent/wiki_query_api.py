#!/usr/bin/env python3
"""
Wiki Query API — REST API for wiki search and retrieval (Task I0000000039)

Provides FastAPI endpoints for:
- /wiki/search — semantic search
- /wiki/incident/<id> — retrieve incident
- /wiki/entity/<name> — retrieve entity
- /wiki/health — health check
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, '/opt/YOUR-PROJECT/ops/agent')

try:
    from fastapi import FastAPI, Query, HTTPException
    from wiki_search_engine import WikiSearchEngine
except ImportError as e:
    print(f"Error importing: {e}")
    print("Install: pip install fastapi uvicorn")
    sys.exit(1)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Wiki Query API",
    description="Search and retrieve [YOUR-AI-NAME] wiki knowledge base",
    version="1.0.0"
)

# Initialize search engine once
search_engine = None

@app.on_event("startup")
async def startup_event():
    """Initialize search engine on startup."""
    global search_engine
    try:
        search_engine = WikiSearchEngine()
        search_engine.index_all_wiki_pages()
        logger.info("✓ Wiki search engine initialized")
    except Exception as e:
        logger.error(f"Failed to initialize search engine: {e}")

@app.get("/wiki/health")
async def health_check():
    """Health check endpoint."""
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not initialized")

    from datetime import datetime
    return {
        "status": "healthy",
        "chunks_indexed": len(search_engine.index.chunks),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/wiki/search")
async def search_wiki(
    q: str = Query(..., min_length=3, description="Search query"),
    limit: int = Query(5, ge=1, le=20, description="Max results to return")
):
    """Search wiki for query."""
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not ready")

    if not q:
        raise HTTPException(status_code=400, detail="Query required")

    try:
        results = search_engine.search(q, limit)
        return {
            "query": q,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.get("/wiki/incident/{incident_id}")
async def get_incident(incident_id: str):
    """Retrieve specific incident."""
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not ready")

    try:
        # Search for incident chunks
        results = search_engine.search(incident_id, limit=10)
        incident_results = [r for r in results if r.get('page_type') == 'incident']

        if not incident_results:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

        return {
            "incident_id": incident_id,
            "sections": incident_results,
            "count": len(incident_results)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving incident: {e}")
        raise HTTPException(status_code=500, detail="Retrieval failed")

@app.get("/wiki/entity/{entity_name}")
async def get_entity(entity_name: str):
    """Retrieve entity page."""
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not ready")

    try:
        # Search for entity chunks
        results = search_engine.search(entity_name, limit=10)
        entity_results = [r for r in results if r.get('page_type') == 'entity']

        if not entity_results:
            raise HTTPException(status_code=404, detail=f"Entity {entity_name} not found")

        return {
            "entity_name": entity_name,
            "sections": entity_results,
            "count": len(entity_results)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving entity: {e}")
        raise HTTPException(status_code=500, detail="Retrieval failed")

@app.get("/wiki/related/{entity_type}/{entity_name}")
async def get_related(entity_type: str, entity_name: str, limit: int = Query(5, ge=1, le=20)):
    """Get related incidents/entities."""
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not ready")

    try:
        results = search_engine.search(entity_name, limit=limit)
        filtered = [r for r in results if entity_type.lower() in [t.lower() for t in [r.get('page_type', '')]]]

        return {
            "entity_type": entity_type,
            "entity_name": entity_name,
            "related": filtered,
            "count": len(filtered)
        }
    except Exception as e:
        logger.error(f"Error finding related: {e}")
        raise HTTPException(status_code=500, detail="Query failed")

@app.get("/wiki/stats")
async def get_stats():
    """Get wiki statistics."""
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not ready")

    try:
        chunks = search_engine.index.chunks
        incidents = sum(1 for c in chunks.values() if getattr(c, 'page_type', None) == 'incident')
        entities = sum(1 for c in chunks.values() if getattr(c, 'page_type', None) == 'entity')

        return {
            "total_chunks": len(chunks),
            "incidents": incidents,
            "entities": entities,
            "engine_ready": True
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Stats failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="info")
