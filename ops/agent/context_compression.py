#!/usr/bin/env python3
"""
context_compression.py — Headroom token compression for [YOUR-AI-NAME] agent context.

Integrates headroom-ai for 40-60% token reduction in Router-bound message
payloads before they reach Ollama (num_ctx=2048 constraint).

Design: ADR-035 (docs/decisions/ADR-035-context-optimization-token-management.md)
Library: headroom-ai >= 0.22.4 (pip3 install headroom-ai)
Tested: v0.22.4 (Venzari VPS), v0.26.0 (Venzari VPS) — both achieve ~55% reduction

Key functions:
  compress_messages(messages, model, model_limit) -> (messages, stats)
  compress_context_string(text, query, model_limit) -> (text, stats)
  benchmark_baseline(query) -> dict

CLI:
  python3 context_compression.py "<query>" [--benchmark] [--verbose]
  python3 context_compression.py --self-test
"""

import sys
import os
import json
import time
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from incident_detector import Incident, IncidentType, IncidentSeverity
from finding_creator import FindingCreator
from opensre_findings_format import OpenSREFindingsExporter

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

PROJECT_CTO = "/opt/YOUR-PROJECT"

# [YOUR-AI-NAME] Ollama context window (num_ctx setting in Router)
OLLAMA_CTX = 2048
# Model for token counting (Anthropic-compatible)
TOKEN_COUNT_MODEL = "claude-haiku-4-5-20251001"
# Minimum tokens before compression is attempted
MIN_TOKENS = 300

try:
    from headroom import compress, CompressConfig, CompressResult
    HAS_HEADROOM = True
except ImportError:
    HAS_HEADROOM = False
    logger.warning("headroom not installed — compression disabled. Run: pip3 install headroom")


def export_compression_metrics(before_tokens: int, after_tokens: int, reduction_pct: float):
    """REAL: Export compression metrics as findings → wiki"""
    try:
        if reduction_pct < 10:  # Only export significant compressions
            return
        finding_creator = FindingCreator()
        findings_exporter = OpenSREFindingsExporter()

        incident = Incident(
            id=f"incident-compression-{int(datetime.now().timestamp())}",
            service="context-compression",
            incident_type=IncidentType.OPERATIONAL_ISSUE,
            severity=IncidentSeverity.INFORMATIONAL,
            timestamp=datetime.now(timezone.utc).isoformat(),
            title=f"Context compressed: {before_tokens} → {after_tokens} tokens ({reduction_pct:.1f}%)",
            evidence=[{"type": "compression", "text": f"Before: {before_tokens}, After: {after_tokens}, Reduction: {reduction_pct:.1f}%"}],
            related_metrics={"before_tokens": before_tokens, "after_tokens": after_tokens, "reduction_pct": reduction_pct}
        )

        finding = finding_creator.create_finding_from_incident(incident)
        findings_exporter.export_finding(finding)
    except Exception:
        pass  # Non-blocking


def _token_estimate(text: str) -> int:
    """Fast approximation: 1 token ≈ 4 chars."""
    return len(text) // 4


def compress_messages(
    messages: list[dict],
    model: str = TOKEN_COUNT_MODEL,
    model_limit: int = OLLAMA_CTX,
    target_ratio: float | None = 0.50,
    protect_recent: int = 1,
) -> tuple[list[dict], dict]:
    """
    Compress a list of messages using Headroom.

    Compresses system + user messages with protect_recent=1 (keeps final user turn).
    Config works on both headroom-ai v0.22.4 and v0.26.0.

    Returns (compressed_messages, stats) where stats contains:
      tokens_before, tokens_after, tokens_saved, compression_ratio, skipped_reason
    """
    if not HAS_HEADROOM:
        return messages, {"skipped_reason": "headroom not installed", "tokens_before": 0, "tokens_after": 0, "tokens_saved": 0, "compression_ratio": 0.0}

    total_text = " ".join(str(m.get("content", "")) for m in messages)
    approx_tokens = _token_estimate(total_text)

    if approx_tokens < MIN_TOKENS:
        return messages, {
            "skipped_reason": f"context too small ({approx_tokens} tokens < {MIN_TOKENS} minimum)",
            "tokens_before": approx_tokens,
            "tokens_after": approx_tokens,
            "tokens_saved": 0,
            "compression_ratio": 0.0,
        }

    try:
        # compress_user_messages=True required for v0.26.0 to fire text compression
        # protect_recent=1 keeps the final user turn (the actual task) intact
        config = CompressConfig(
            compress_system_messages=True,
            compress_user_messages=True,
            protect_recent=protect_recent,
            target_ratio=target_ratio,
            min_tokens_to_compress=MIN_TOKENS,
        )
        result = compress(messages, model=model, model_limit=model_limit, config=config)

        # Export compression metrics as findings
        if result.compression_ratio > 0.1:  # Only if >10% reduction
            reduction_pct = (1 - result.compression_ratio) * 100
            export_compression_metrics(result.tokens_before, result.tokens_after, reduction_pct)

        return result.messages, {
            "skipped_reason": None,
            "tokens_before": result.tokens_before,
            "tokens_after": result.tokens_after,
            "tokens_saved": result.tokens_saved,
            "compression_ratio": result.compression_ratio,
            "transforms_applied": result.transforms_applied,
        }
    except Exception as e:
        logger.warning(f"headroom compress failed: {e}")
        return messages, {"skipped_reason": f"compression error: {e}", "tokens_before": approx_tokens, "tokens_after": approx_tokens, "tokens_saved": 0, "compression_ratio": 0.0}


def compress_context_string(
    context_text: str,
    task_query: str = "",
    model_limit: int = OLLAMA_CTX,
) -> tuple[str, dict]:
    """
    Compress a plain-text context string (inject_context.py output).

    Wraps text as a system message, compresses, unwraps.
    Returns (compressed_text, stats).
    """
    messages = [
        {"role": "system", "content": context_text},
        {"role": "user", "content": task_query or "Execute task"},
    ]
    compressed_msgs, stats = compress_messages(messages, model_limit=model_limit)
    compressed_text = compressed_msgs[0].get("content", context_text) if compressed_msgs else context_text
    return compressed_text, stats


def benchmark_baseline(query: str = "Fix inference overflow context", verbose: bool = False) -> dict:
    """
    Measure compression against the current inject_context.py baseline.

    Runs inject_context.py, then applies compression, measures reduction.
    """
    import subprocess
    t0 = time.time()
    result = subprocess.run(
        ["python3", f"{PROJECT_CTO}/ops/agent/inject_context.py", query],
        capture_output=True, text=True, timeout=30,
    )
    inject_time = time.time() - t0
    baseline_text = result.stdout

    tokens_before_inject = _token_estimate(baseline_text)
    t1 = time.time()
    compressed, stats = compress_context_string(baseline_text, task_query=query)
    compress_time = time.time() - t1

    report = {
        "query": query,
        "baseline_chars": len(baseline_text),
        "baseline_tokens_approx": tokens_before_inject,
        "compressed_chars": len(compressed),
        "tokens_before": stats.get("tokens_before", tokens_before_inject),
        "tokens_after": stats.get("tokens_after", tokens_before_inject),
        "tokens_saved": stats.get("tokens_saved", 0),
        "compression_ratio": stats.get("compression_ratio", 0.0),
        "skipped_reason": stats.get("skipped_reason"),
        "inject_time_ms": round(inject_time * 1000),
        "compress_time_ms": round(compress_time * 1000),
    }

    if verbose:
        print(f"\n=== [YOUR-AI-NAME] Context Compression Benchmark ===")
        print(f"Query: {query}")
        print(f"Baseline: {report['baseline_chars']} chars / ~{report['baseline_tokens_approx']} tokens")
        if report["skipped_reason"]:
            print(f"Skipped: {report['skipped_reason']}")
        else:
            print(f"Compressed: {report['compressed_chars']} chars")
            print(f"Tokens: {report['tokens_before']} → {report['tokens_after']} (saved {report['tokens_saved']})")
            print(f"Ratio: {report['compression_ratio']:.1%}")
        print(f"Inject time: {report['inject_time_ms']}ms")
        print(f"Compress time: {report['compress_time_ms']}ms")
        print(f"==========================================")
    return report


def benchmark_router_payload(verbose: bool = False) -> dict:
    """
    Benchmark headroom on a realistic Router payload.

    Simulates the full system-prompt + conversation that goes to Ollama,
    measuring how much compression headroom achieves.
    """
    soul_excerpt = (
        "You are [Your-AI-Name], an AI assistant for Billy Burrows at Venzari AI. "
        "IDENTITY: Confident, direct, resourceful. Revenue focus. "
        "RULES: Never patch running containers. Verify with curl. "
        "SSOT is /opt/YOUR-PROJECT. VenzariAI Router at :4001. "
        "Two models only: jeanne-primary + nomic-embed-text. "
        "Every task needs a .tasks/ entry. Commit after every meaningful change. "
        "BUSINESS CONTEXT: B2B SaaS targeting podcast/broadcast industry at $5K MRR. "
        "Products: [YOUR-AI-NAME] CTO Platform, AI content pipeline, Telegram bot. "
        "Current state: OpenClaw UP, Router v2.3.5, Ollama UP, ChromaDB UP. "
        "MEMORY: 3 proposals pending. Last inference: 106s latency morning-brief. "
        "ADR-035: headroom context compression approved for Phase 5. "
    )
    # Simulate workspace injection (bootstrapMaxChars=4000 → ~1000 tokens)
    workspace = soul_excerpt * 4 + "\n\nWORKSPACE:\n" + "Task: 1684 - headroom integration\n" * 20

    messages = [
        {"role": "system", "content": workspace},
        {"role": "user", "content": "Morning brief for Billy — 8:30am CDT. Run health checks and write status."},
        {"role": "assistant", "content": "Running checks now."},
        {"role": "user", "content": "[tool: shell] docker ps: 15 containers running. Router: {status: ok}. Proposals: 2 PENDING."},
    ]

    before_text = " ".join(m.get("content", "") for m in messages)
    before_tokens = _token_estimate(before_text)

    compressed_msgs, stats = compress_messages(messages, model_limit=OLLAMA_CTX, protect_recent=2)

    report = {
        "scenario": "router_payload_simulation",
        "messages_count": len(messages),
        "approx_tokens_before": before_tokens,
        "tokens_before": stats.get("tokens_before", before_tokens),
        "tokens_after": stats.get("tokens_after", before_tokens),
        "tokens_saved": stats.get("tokens_saved", 0),
        "compression_ratio": stats.get("compression_ratio", 0.0),
        "skipped_reason": stats.get("skipped_reason"),
        "transforms": stats.get("transforms_applied", []),
        "ollama_ctx_limit": OLLAMA_CTX,
        "fits_in_ollama_ctx": stats.get("tokens_after", before_tokens) <= OLLAMA_CTX,
    }

    if verbose:
        print(f"\n=== Router Payload Benchmark ===")
        print(f"Messages: {report['messages_count']}, Tokens before: {report['tokens_before']}")
        if report["skipped_reason"]:
            print(f"Skipped: {report['skipped_reason']}")
        else:
            print(f"Tokens after: {report['tokens_after']} (saved {report['tokens_saved']})")
            print(f"Compression: {report['compression_ratio']:.1%}")
            print(f"Fits in Ollama num_ctx={OLLAMA_CTX}: {report['fits_in_ollama_ctx']}")
            print(f"Transforms: {report['transforms']}")
        print(f"================================")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="Fix inference overflow context compression headroom",
                        help="Query to use for benchmark")
    parser.add_argument("--benchmark", action="store_true", help="Run baseline benchmark against inject_context.py")
    parser.add_argument("--router-benchmark", action="store_true", help="Run Router payload simulation benchmark")
    parser.add_argument("--self-test", action="store_true", help="Run self-test to verify headroom integration")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.self_test:
        print("=== Self Test: [YOUR-AI-NAME] context_compression.py ===")
        print(f"headroom installed: {HAS_HEADROOM}")
        if HAS_HEADROOM:
            import headroom
            print(f"headroom version: {headroom.__version__}")
            report = benchmark_router_payload(verbose=True)
            ok = report["compression_ratio"] > 0.3 or report["skipped_reason"] is not None
            print(f"\nSelf-test: {'PASS' if ok else 'FAIL'}")
            sys.exit(0 if ok else 1)
        else:
            print("FAIL: headroom not installed")
            sys.exit(1)

    results = {}

    if args.benchmark or not any([args.router_benchmark]):
        results["inject_baseline"] = benchmark_baseline(args.query, verbose=args.verbose)

    if args.router_benchmark:
        results["router_payload"] = benchmark_router_payload(verbose=args.verbose)

    if not any([args.benchmark, args.router_benchmark, args.self_test]):
        # Default: both benchmarks
        results["inject_baseline"] = benchmark_baseline(args.query, verbose=True)
        results["router_payload"] = benchmark_router_payload(verbose=True)

    if args.as_json:
        print(json.dumps(results, indent=2))
    elif not args.verbose and results:
        for name, r in results.items():
            ratio = r.get("compression_ratio", 0)
            saved = r.get("tokens_saved", 0)
            reason = r.get("skipped_reason", "")
            if reason:
                print(f"{name}: SKIPPED ({reason})")
            else:
                print(f"{name}: {ratio:.1%} compression, {saved} tokens saved")


if __name__ == "__main__":
    main()
