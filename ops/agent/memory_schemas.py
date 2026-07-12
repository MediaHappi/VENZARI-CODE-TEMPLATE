#!/usr/bin/env python3
"""
Memory Layer Database Schemas — Phase 1a

6 PostgreSQL schemas for memory system:
- episodic: session logs, handoffs, state snapshots
- semantic: facts, findings, discovered patterns
- reasoning: decisions, precedents, choices
- temporal: access times, decay scores, relevance tracking
- entities: services, tasks, configs, incidents
- relationships: depends_on, caused_by, related_to
"""

EPISODIC_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodic_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT UNIQUE NOT NULL,
    handoff_summary TEXT,
    task_completions JSONB DEFAULT '[]',
    state_snapshot JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    age_hours INTEGER GENERATED ALWAYS AS (EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600) STORED,
    KEY_INDEX (session_id),
    KEY_INDEX (created_at)
);
"""

SEMANTIC_SCHEMA = """
CREATE TABLE IF NOT EXISTS semantic_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    domain TEXT DEFAULT 'general',
    source_task_id TEXT,
    embedding_id TEXT,
    confidence_score FLOAT DEFAULT 0.5,
    decay_score FLOAT DEFAULT 100.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    KEY_INDEX (domain),
    KEY_INDEX (decay_score),
    KEY_INDEX (created_at)
);
"""

REASONING_SCHEMA = """
CREATE TABLE IF NOT EXISTS reasoning_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL,
    reasoning TEXT,
    choice_made TEXT,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    precedent_id UUID REFERENCES reasoning_decisions(id),
    precedent_similarity FLOAT DEFAULT 0.0,
    agent_role TEXT,
    KEY_INDEX (task_id),
    KEY_INDEX (category),
    KEY_INDEX (created_at)
);
"""

TEMPORAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS temporal_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fact_id UUID NOT NULL REFERENCES semantic_facts(id) ON DELETE CASCADE,
    last_accessed TIMESTAMPTZ DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    importance_score FLOAT DEFAULT 1.0,
    relevance_score FLOAT GENERATED ALWAYS AS (
        importance_score * EXP(-EXTRACT(EPOCH FROM (NOW() - last_accessed)) / (7 * 86400.0))
    ) STORED,
    half_life_days FLOAT DEFAULT 7.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    KEY_INDEX (fact_id),
    KEY_INDEX (relevance_score),
    UNIQUE (fact_id)
);
"""

ENTITIES_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    entity_type TEXT DEFAULT 'service',
    service_name TEXT,
    incident_link_count INTEGER DEFAULT 0,
    occurrence_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    KEY_INDEX (name),
    KEY_INDEX (entity_type),
    KEY_INDEX (service_name),
    UNIQUE (name)
);
"""

RELATIONSHIPS_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES knowledge_entities(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES knowledge_entities(id) ON DELETE CASCADE,
    relationship_type TEXT DEFAULT 'related_to',
    evidence_count INTEGER DEFAULT 1,
    last_evidence_date TIMESTAMPTZ DEFAULT NOW(),
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    KEY_INDEX (source_id),
    KEY_INDEX (target_id),
    KEY_INDEX (relationship_type),
    UNIQUE (source_id, target_id, relationship_type)
);
"""

SCHEMA_DEFINITIONS = {
    'episodic': EPISODIC_SCHEMA,
    'semantic': SEMANTIC_SCHEMA,
    'reasoning': REASONING_SCHEMA,
    'temporal': TEMPORAL_SCHEMA,
    'entities': ENTITIES_SCHEMA,
    'relationships': RELATIONSHIPS_SCHEMA,
}


def get_create_schemas_sql() -> str:
    """Return all schema creation SQL."""
    return '\n\n'.join(SCHEMA_DEFINITIONS.values())


def get_indexes_sql() -> str:
    """Return additional performance indexes."""
    return """
    CREATE INDEX IF NOT EXISTS idx_semantic_domain ON semantic_facts(domain);
    CREATE INDEX IF NOT EXISTS idx_semantic_decay ON semantic_facts(decay_score DESC);
    CREATE INDEX IF NOT EXISTS idx_temporal_relevance ON temporal_facts(relevance_score DESC);
    CREATE INDEX IF NOT EXISTS idx_temporal_decay_score ON temporal_facts(relevance_score DESC);
    CREATE INDEX IF NOT EXISTS idx_relationships_type ON knowledge_relationships(relationship_type);
    CREATE INDEX IF NOT EXISTS idx_entities_type ON knowledge_entities(entity_type);
    """


if __name__ == "__main__":
    print("Memory Layer Schemas")
    print("=" * 60)
    for layer, schema in SCHEMA_DEFINITIONS.items():
        table_count = schema.count('CREATE TABLE')
        print(f"\n{layer.upper()}: {table_count} table(s)")
        print(schema[:80] + "...")
    print("\n" + "=" * 60)
    print("✓ All 6 schemas defined")
    print(f"Total schema lines: {sum(len(s.split(chr(10))) for s in SCHEMA_DEFINITIONS.values())}")
