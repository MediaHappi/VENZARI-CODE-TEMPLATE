#!/usr/bin/env python3
"""Wire task completion to PostgreSQL memory schemas."""
import os
import json
import sys
from datetime import datetime, timezone
from typing import Dict, Optional

def _get_db_connection_string():
    """Get database connection string from environment or use default."""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url

    # Use explicit connection parameters (common in Docker/testing)
    user = os.getenv('POSTGRES_USER', 'readykit')
    password = os.getenv('POSTGRES_PASSWORD', 'readykit')
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    database = os.getenv('POSTGRES_DB', 'venzarai_hub')

    return f'postgresql://{user}:{password}@{host}:{port}/{database}'

def _ensure_schemas_exist(cur):
    """Create memory layer schemas if they don't exist."""
    schemas = [
        """CREATE TABLE IF NOT EXISTS semantic_facts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content TEXT NOT NULL,
            domain TEXT DEFAULT 'general',
            source_task_id TEXT,
            embedding_id TEXT,
            confidence_score FLOAT DEFAULT 0.5,
            decay_score FLOAT DEFAULT 100.0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_accessed TIMESTAMPTZ DEFAULT NOW(),
            access_count INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS reasoning_decisions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id TEXT NOT NULL,
            reasoning TEXT,
            choice_made TEXT,
            category TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            agent_role TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS episodic_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id TEXT UNIQUE NOT NULL,
            handoff_summary TEXT,
            task_completions JSONB DEFAULT '[]',
            state_snapshot JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )"""
    ]

    for schema in schemas:
        try:
            cur.execute(schema)
        except Exception as e:
            # Table might already exist; check if it's a "already exists" error
            if 'already exists' not in str(e).lower():
                raise

def record_task_to_memory(task: Dict, evidence: str, summary: str) -> bool:
    """Write task findings to PostgreSQL memory schemas.

    CRITICAL: This MUST succeed. Memory persistence is NOT optional.
    Includes automatic retry for transient failures.
    """
    import time
    import psycopg2
    from psycopg2.extras import Json

    # Retry configuration for transient failures
    max_retries = 3
    retry_delay = 0.5  # seconds

    try:
        conn_str = _get_db_connection_string()

        # Ensure DATABASE_URL or explicit params are set
        if not os.getenv('DATABASE_URL') and not os.getenv('POSTGRES_USER'):
            raise EnvironmentError(
                "CRITICAL: Memory persistence cannot proceed without database configuration.\n"
                "Set either DATABASE_URL or POSTGRES_USER+POSTGRES_PASSWORD+POSTGRES_HOST+POSTGRES_DB"
            )

        task_id = task.get('id')
        domain = task.get('layer', 'general')
        now = datetime.now(timezone.utc)

        # Retry loop for transient failures (connection issues, etc)
        last_error = None
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(conn_str)
                cur = conn.cursor()

                # Ensure schemas exist
                _ensure_schemas_exist(cur)

                # 1. Insert to semantic_facts
                cur.execute("""
                    INSERT INTO semantic_facts
                    (content, domain, source_task_id, created_at)
                    VALUES (%s, %s, %s, %s)
                """, (f"{task.get('title')}: {summary}\nEvidence: {evidence[:500]}",
                      domain, task_id, now))

                # 2. Insert to reasoning_decisions
                cur.execute("""
                    INSERT INTO reasoning_decisions
                    (task_id, reasoning, choice_made, category, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (task_id, summary, f"Completed {task_id}", domain, now))

                # 3. Insert to episodic_sessions
                cur.execute("""
                    INSERT INTO episodic_sessions
                    (session_id, task_completions, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE
                    SET task_completions = episodic_sessions.task_completions || %s
                """, (os.getenv('SESSION_ID', 'default'),
                      Json([task_id]), now,
                      Json([task_id])))

                # If commit succeeds, we're done
                conn.commit()
                cur.close()
                conn.close()
                return True

            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                # Transient connection errors — retry with backoff
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    raise

            except psycopg2.DatabaseError as e:
                # Database errors (constraint violations, etc) — do NOT retry
                raise

            except Exception as e:
                # Other unexpected errors
                raise

        # Should not reach here
        raise RuntimeError(f"Memory persistence failed after {max_retries} attempts: {last_error}")

    except ImportError:
        raise RuntimeError("psycopg2 not installed — cannot persist memory")
    except EnvironmentError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Memory persistence failed: {e}")
