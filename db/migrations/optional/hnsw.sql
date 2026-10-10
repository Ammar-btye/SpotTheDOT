-- target: main
-- OPTIONAL. Not applied by default: exact search (no ANN index) is the contract's default, because at a few
-- thousand rows it is fast and filtered queries never drop results. Apply only if EXPLAIN ANALYZE of
-- match_documents shows it is slow:   python db/setup.py migrate --hnsw
-- The search functions already carry `SET hnsw.iterative_scan = strict_order` (pgvector >= 0.8; Neon ships 0.8.x),
-- so metadata filters still return match_count rows once this index exists.
-- Remove it again with:  DROP INDEX IF EXISTS documents_embedding_hnsw;
-- {{VEC_OPS}} is vector_cosine_ops, or halfvec_cosine_ops when EMBED_DIM > 2000.
CREATE INDEX IF NOT EXISTS documents_embedding_hnsw ON documents USING hnsw (embedding {{VEC_OPS}});
