'''supabase_prep

Revision ID: 002_supabase_prep
Revises: 001_initial_schema
Create Date: 2026-09-15

Changes:
  1. Re-enable pgvector in the extensions schema (Supabase convention).
  2. Add embedding_model provenance column to chunks (additive, nullable).
  3. Drop old HNSW index and recreate with explicit m=16, ef_construction=64.
  4. Enable Row Level Security on all four tables with no permissive policies.
'''
from alembic import op
import sqlalchemy as sa

revision = '002_supabase_prep'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    # 1. pgvector in extensions schema
    op.execute('CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions')

    # 2. embedding_model provenance column
    op.add_column('chunks', sa.Column('embedding_model', sa.Text(), nullable=True))

    # 3. Rebuild HNSW index with explicit parameters
    op.execute('DROP INDEX IF EXISTS ix_chunks_embedding_hnsw')
    op.execute(
        'CREATE INDEX ix_chunks_embedding_hnsw '
        'ON chunks USING hnsw (embedding vector_cosine_ops) '
        'WITH (m=16, ef_construction=64)'
    )

    # 4. Row Level Security - deny-by-default for anon/authenticated roles
    for table in ('sessions', 'messages', 'artifacts', 'chunks'):
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')


def downgrade():
    for table in ('sessions', 'messages', 'artifacts', 'chunks'):
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY')

    op.execute('DROP INDEX IF EXISTS ix_chunks_embedding_hnsw')
    op.execute('CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)')
    op.drop_column('chunks', 'embedding_model')
