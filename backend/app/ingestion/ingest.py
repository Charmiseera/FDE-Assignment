"""
Transcript ingestion pipeline.

Usage (from backend/):
    python -m app.ingestion.ingest            # Ingest default top 30 landmark episodes
    python -m app.ingestion.ingest --limit 50  # Ingest top 50 landmark episodes
    python -m app.ingestion.ingest --all       # Ingest all 303 ChatPRD episodes
    python -m app.ingestion.ingest --refresh  # Force re-embed all chunks

Rules (per architecture.md):
- Direct parsing of transcript.md files from episodes/{guest}/transcript.md.
- Frontmatter extraction (yaml.safe_load) as primary title/guest source.
- Chunking: ~500 words, 50-word overlap, sentence-boundary aware.
- Embedding: nomic-embed-text via Ollama (768-dim).
- Upsert key: (source_file, chunk_index) — idempotent re-ingestion.
- Skip: if content_hash matches existing row, skip embedding call.
- CLI only — not an HTTP endpoint.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Iterator

import ollama
import structlog
import yaml
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Add parent to path so `python -m app.ingestion.ingest` works from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.models import Chunk
from app.db.session import AsyncSessionLocal

logger = structlog.get_logger()

# ── constants ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "nomic-embed-text"
CHUNK_WORDS = 500
OVERLAP_WORDS = 50
def _resolve_transcript_dir() -> Path:
    """
    Resolve the transcripts_temp directory.

    Priority:
    1. TRANSCRIPT_DIR env var (set in Docker via compose or CLI --episodes-dir)
    2. Walk up from this file: backend/app/ingestion/ingest.py → project root → data/transcripts_temp
       - parents[3] works locally (project/backend/app/ingestion/ingest.py)
       - But inside Docker the file is /app/app/ingestion/ingest.py → parents[3] = /
       - Guard: if the computed path resolves to /, fall back to /app/data/transcripts_temp
    """
    env_override = os.environ.get("TRANSCRIPT_DIR")
    if env_override:
        return Path(env_override)
    candidate = Path(__file__).resolve().parents[3] / "data" / "transcripts_temp"
    if str(candidate).startswith("/data") or str(candidate) == "/data/transcripts_temp":
        # Docker layout: /app/app/ingestion/ingest.py → parents[3] = /
        return Path("/app/data/transcripts_temp")
    return candidate

ROOT_DIR = Path(__file__).resolve().parents[3]
TRANSCRIPT_TEMP_DIR = _resolve_transcript_dir()

# Selected landmark topics for top-N ranking — covering the full scope of Lenny's Podcast
TARGET_INDEX_FILES = [
    # Core product & growth
    "product-management.md",
    "product-led-growth.md",
    "retention.md",
    "growth-strategy.md",
    "startup-growth.md",
    "product-market-fit.md",
    "product-strategy.md",
    # Experimentation & data
    "experimentation.md",
    "analytics.md",
    # Go-to-market & distribution
    "marketing.md",
    "word-of-mouth.md",
    "network-effects.md",
    # Leadership & org
    "leadership.md",
    "ai.md",
    "power.md",
]


# ── chunking ─────────────────────────────────────────────────────────────────

def _split_sentences(text_content: str) -> list[str]:
    """Rough sentence splitter — good enough for transcript text."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text_content) if s.strip()]


def _chunk_text(full_text: str, chunk_words: int, overlap_words: int) -> Iterator[str]:
    """
    Yield overlapping word-window chunks that respect sentence boundaries.
    Each chunk targets ~chunk_words words; overlap carries the last
    overlap_words words of the previous chunk into the next one.
    """
    sentences = _split_sentences(full_text)
    if not sentences:
        return

    buffer: list[str] = []
    buffer_word_count = 0

    for sentence in sentences:
        words = sentence.split()
        buffer.append(sentence)
        buffer_word_count += len(words)

        if buffer_word_count >= chunk_words:
            yield " ".join(buffer)
            # retain overlap
            overlap_sentences: list[str] = []
            kept = 0
            for s in reversed(buffer):
                w = len(s.split())
                if kept + w > overlap_words:
                    break
                overlap_sentences.insert(0, s)
                kept += w
            buffer = overlap_sentences
            buffer_word_count = kept

    if buffer:
        yield " ".join(buffer)


def _extract_metadata_and_body(file_text: str, default_slug: str) -> tuple[str, str, str]:
    """
    Parse YAML frontmatter (between first two '---' markers).
    Returns (episode_title, guest, body_text).
    """
    episode_title = ""
    guest = ""
    body = file_text

    parts = file_text.split("---", 2)
    if len(parts) >= 3:
        try:
            fm = yaml.safe_load(parts[1])
            if isinstance(fm, dict):
                guest = str(fm.get("guest") or "")
                episode_title = str(fm.get("title") or "")
                body = parts[2].strip()
        except Exception:
            pass

    if not episode_title:
        # Fallback to first H1 heading or guest name or slug
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("# "):
                episode_title = line[2:].strip()
                break
        if not episode_title:
            episode_title = guest if guest else default_slug.replace("-", " ").title()

    return episode_title, guest, body


def _sha256(text_str: str) -> str:
    return hashlib.sha256(text_str.encode()).hexdigest()


# ── embedding ─────────────────────────────────────────────────────────────────

def _embed(text_str: str) -> list[float]:
    """Call Ollama synchronously for a single embedding."""
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    client = ollama.Client(host=base_url)
    response = client.embeddings(model=EMBEDDING_MODEL, prompt=text_str)
    return response["embedding"]


# ── DB upsert ────────────────────────────────────────────────────────────────

async def _get_existing_hashes(session, source_file: str) -> dict[int, str]:
    """Return {chunk_index: content_hash} for an already-ingested file."""
    result = await session.execute(
        select(Chunk.chunk_index, Chunk.content_hash).where(
            Chunk.source_file == source_file
        )
    )
    return {row.chunk_index: row.content_hash for row in result}


async def _upsert_chunk(
    session,
    source_file: str,
    episode_title: str,
    chunk_index: int,
    chunk_text: str,
    embedding: list[float],
    content_hash: str,
) -> None:
    stmt = pg_insert(Chunk).values(
        source_file=source_file,
        episode_title=episode_title,
        chunk_index=chunk_index,
        chunk_text=chunk_text,
        content_hash=content_hash,
        embedding=embedding,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_file", "chunk_index"],
        set_={
            "chunk_text": stmt.excluded.chunk_text,
            "content_hash": stmt.excluded.content_hash,
            "embedding": stmt.excluded.embedding,
            "episode_title": stmt.excluded.episode_title,
        },
    )
    await session.execute(stmt)


# ── Ranking landmark episodes ─────────────────────────────────────────────────

def _rank_episodes_by_topic_indices(episodes_dir: Path, index_dir: Path) -> list[Path]:
    """
    Ranks transcript.md files based on frequency of occurrence across landmark topic index files.
    """
    scored_slugs: dict[str, int] = {}
    if index_dir.exists():
        for idx_file in TARGET_INDEX_FILES:
            idx_path = index_dir / idx_file
            if idx_path.exists():
                content = idx_path.read_text(encoding="utf-8", errors="ignore")
                matches = re.findall(r"episodes/([^/)\s]+)", content)
                for slug in matches:
                    scored_slugs[slug] = scored_slugs.get(slug, 0) + 1

    all_transcript_files: list[Path] = []
    if episodes_dir.exists():
        for ep_dir in sorted(episodes_dir.iterdir()):
            md_file = ep_dir / "transcript.md"
            if ep_dir.is_dir() and md_file.exists():
                all_transcript_files.append(md_file)

    def sort_key(p: Path) -> tuple[int, str]:
        slug = p.parent.name
        score = scored_slugs.get(slug, 0)
        return (-score, slug)

    all_transcript_files.sort(key=sort_key)
    return all_transcript_files


# ── main pipeline ─────────────────────────────────────────────────────────────

async def ingest_file(
    md_path: Path,
    refresh: bool,
) -> dict[str, int]:
    """Ingest one transcript.md file. Returns stats dict."""
    source_file = f"{md_path.parent.name}/{md_path.name}"
    raw = md_path.read_text(encoding="utf-8", errors="replace")
    episode_title, _guest, body = _extract_metadata_and_body(raw, md_path.parent.name)

    chunks = list(_chunk_text(body, CHUNK_WORDS, OVERLAP_WORDS))
    stats = {"total": len(chunks), "embedded": 0, "skipped": 0}

    async with AsyncSessionLocal() as session:
        existing: dict[int, str] = {} if refresh else await _get_existing_hashes(
            session, source_file
        )

        for idx, chunk in enumerate(chunks):
            content_hash = _sha256(chunk)

            if not refresh and existing.get(idx) == content_hash:
                stats["skipped"] += 1
                continue

            try:
                embedding = _embed(chunk)
            except Exception as exc:
                logger.error(
                    "embedding_failed",
                    file=source_file,
                    chunk_index=idx,
                    error=str(exc),
                )
                continue

            await _upsert_chunk(
                session,
                source_file=source_file,
                episode_title=episode_title,
                chunk_index=idx,
                chunk_text=chunk,
                embedding=embedding,
                content_hash=content_hash,
            )
            stats["embedded"] += 1

        await session.commit()

    return stats


async def run_ingestion(
    episodes_dir: Path,
    index_dir: Path,
    limit: int | None,
    refresh: bool,
) -> None:
    ranked_files = _rank_episodes_by_topic_indices(episodes_dir, index_dir)

    if not ranked_files:
        print(f"[ingest] No transcript.md files found under {episodes_dir}")
        return

    total_available = len(ranked_files)
    selected_files = ranked_files if limit is None else ranked_files[:limit]
    print(
        f"[ingest] Found {total_available} total ChatPRD episodes. "
        f"Processing {len(selected_files)} episode(s) (limit={limit if limit else 'ALL'})..."
    )

    total_embedded = 0
    for idx, md_path in enumerate(selected_files, 1):
        slug = md_path.parent.name
        print(f"[{idx}/{len(selected_files)}] Processing {slug}/transcript.md ...", end=" ", flush=True)
        stats = await ingest_file(md_path, refresh=refresh)
        total_embedded += stats["embedded"]
        print(
            f"chunks={stats['total']}  embedded={stats['embedded']}  skipped={stats['skipped']}"
        )

    print(f"[ingest] Complete! Total new embeddings stored: {total_embedded}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lenny ChatPRD transcript ingestion pipeline")
    parser.add_argument(
        "--episodes-dir",
        type=Path,
        default=TRANSCRIPT_TEMP_DIR / "episodes",
        help="Directory containing episodes/{slug}/transcript.md",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=TRANSCRIPT_TEMP_DIR / "index",
        help="Directory containing repository topic index files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Number of top index-backed landmark episodes to ingest (default: 30)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest all 303 episodes in the ChatPRD repository (overrides --limit)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-embed all chunks (ignores content_hash)",
    )
    args = parser.parse_args()

    limit = None if args.all else args.limit

    if not args.episodes_dir.exists():
        print(f"[ingest] ERROR: Episodes directory not found: {args.episodes_dir}")
        sys.exit(1)

    asyncio.run(
        run_ingestion(
            episodes_dir=args.episodes_dir,
            index_dir=args.index_dir,
            limit=limit,
            refresh=args.refresh,
        )
    )


if __name__ == "__main__":
    main()
