# Embedding model + serving on AMD ROCm + pgvector in Neon (System 2 RAG)

Researched 2026-10-10 (Sat). Every claim has a URL. **Unverified** marks anything I couldn't confirm. Nothing was tested on our hardware.

## 1. Scope

- **Searched:** HF model cards (via the Hub API, including 2026 releases sorted by trending), docs for TEI, llama.cpp, vLLM, Infinity and Lemonade, Neon's pgvector docs, and the pgvector README.
- **Skipped:** the live MTEB leaderboard. I used card-printed scores, which come from **different benchmarks and aren't comparable across rows**.
- **Reused, not re-researched:** ROCm/llama.cpp setup on gfx1151 (`tech-amd-rocm-hf-serving-2026-10-09.md`).

## 2. Findings

### 2.1 Models

| Model | Params | Dim (MRL) | Max len | Retrieval score (as printed on its card) | License | Required prefix |
|---|---|---|---|---|---|---|
| **Qwen3-Embedding-0.6B** | 0.6B | 1024 (32–1024) | 32K | MTEB-eng-v2 Retr **61.83**; MMTEB Retr 64.64 | **Apache-2.0** | Query: `Instruct: {task}\nQuery:`; docs: none |
| Qwen3-Embedding-4B | 4B | 2560 (MRL) | 32K | 68.46 / 69.60 | Apache-2.0 | same |
| Qwen3-Embedding-8B | 8B | 4096 (MRL) | 32K | 69.44 / 70.88 | Apache-2.0 | same |
| EmbeddingGemma-300m | 0.3B | 768 (512/256/128) | 2048 | MTEB-eng-v2 mean 69.67 (no retrieval mean on card) | **Gemma terms, gated** | `task: search result \| query: ` / `title: none \| text: `; no fp16 |
| **EmbeddingGemma 2** (released 2026-10-06) | 740M (text-only 270M) | 768 (512/256/128) | 8K | MTEB-eng-v2 mean 68.46; MMTEB mean 61.36 | Apache-2.0 | same as above; **no fp16**; needs sentence-transformers ≥6.1.0 |
| BGE-M3 | 568M | 1024 | 8192 | MMTEB Retr 54.60; BEIR 48.8 | MIT | none (also sparse + multi-vector) |
| nomic-embed-text-v1.5 | ~0.1B | 768 (512–64) | 8192* | MTEB avg 62.28 | Apache-2.0 | `search_query: ` / `search_document: `; `trust_remote_code` |
| nomic-embed-text-v2-moe | 475M (305M active) | 768 (→256) | 512 | BEIR 52.86 | Apache-2.0 | same as v1.5 |
| snowflake-arctic-embed-l-v2.0 | 568M | 1024 (MRL 256) | 8192 | BEIR 55.6 | Apache-2.0 | `query: ` on queries only |
| mxbai-embed-large-v1 | 335M | not stated on card (MRL + binary) | not stated | MTEB Retr 54.39 | Apache-2.0 | `Represent this sentence for searching relevant passages: ` |
| granite-embedding-english-r2 | 149M | 768 | 8192 | BEIR 53.1; MTEB-v2 Retr 56.4 | Apache-2.0 | none shown |
| granite-embedding-311m-multilingual-r2 (Apr 2026) | 311M | 768 (512–128) | 32,768 | MMTEB Retr 65.2 | Apache-2.0 | none shown |
| gte-modernbert-base | 149M | 768 | 8192 | BEIR 55.33 | Apache-2.0 | none; transformers ≥4.48 |
| nomic modernbert-embed-base | 149M | 768 | n/a | MTEB-v2 Retr 48.7 (granite table) | Apache-2.0 | unverified |
| multilingual-e5-large-instruct | 560M | 1024 | 512 | MTEB-eng-v2 Retr 53.47 | MIT | `Instruct: {task}\nQuery: ` |
| multilingual-e5-large | 560M | 1024 | 512 | n/a | MIT | `query: ` / `passage: ` (required) |
| jina-embeddings-v3 | 572M | | | | **CC-BY-NC-4.0: do not use** | |
| jina-embeddings-v4 | 3.8B | | | | **Qwen Research License (first released as CC-BY-NC): do not use** | |
| jina-embeddings-v5-omni-small (Aug 2026) | 1.6B | | | | **CC-BY-NC-4.0: do not use** | |

*The nomic v1.5 card says going past 2048 tokens needs a tokenizer and RoPE change.

Sources:
- Qwen3-Embedding: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B. Its ST prompt config (`query` = `Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:`, `document` = empty; last-token pooling + Normalize module) is in the repo's `config_sentence_transformers.json`, `1_Pooling/config.json` and `modules.json`.
- Gemma: https://huggingface.co/google/embeddinggemma-300m, https://huggingface.co/google/embeddinggemma-2. EmbeddingGemma 2's `config_sentence_transformers.json` records that it was built with `transformers 5.18.0.dev0`.
- BGE-M3: https://huggingface.co/BAAI/bge-m3. Its BEIR 48.8 comes from the Arctic card, and MMTEB 54.60 from the Qwen card.
- Nomic: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5, https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe
- Arctic: https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0
- mxbai: https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1
- Granite: https://huggingface.co/ibm-granite/granite-embedding-english-r2, https://huggingface.co/ibm-granite/granite-embedding-311m-multilingual-r2
- GTE: https://huggingface.co/Alibaba-NLP/gte-modernbert-base
- E5: https://huggingface.co/intfloat/multilingual-e5-large-instruct, https://huggingface.co/intfloat/multilingual-e5-large
- Jina: https://huggingface.co/jinaai/jina-embeddings-v3, https://huggingface.co/jinaai/jina-embeddings-v4, https://huggingface.co/jinaai/jina-embeddings-v5-omni-small (licenses read from Hub metadata)

**Rerankers.** Both run on top-100 results from Qwen3-Embedding-0.6B, measured on MTEB-eng-v2 retrieval (https://huggingface.co/Qwen/Qwen3-Reranker-0.6B):

| Model | MTEB-R | License |
|---|---|---|
| Qwen3-Embedding-0.6B alone | 61.82 | Apache-2.0 |
| **Qwen3-Reranker-0.6B** | **65.80** | Apache-2.0 |
| bge-reranker-v2-m3 | 57.03 | Apache-2.0 (https://huggingface.co/BAAI/bge-reranker-v2-m3) |

Qwen3-Reranker-0.6B loads as `CrossEncoder("Qwen/Qwen3-Reranker-0.6B")` in sentence-transformers. The minimum ST version for that is **unverified**.

**Takeaways**
- Qwen3-Embedding-0.6B has the best printed English retrieval score under 1B with a clean license (61.83 vs 53.47 for mE5-large-instruct, same table). It shares the Qwen family with System 2, and 1024 dims fits pgvector's 2,000-dim index limit.
- EmbeddingGemma 2 is strong but **4 days old** and built against a **dev** transformers, a dependency risk next to AMD's torch 2.12 wheels.
- 4B/8B dims (2560/4096) exceed the `vector` index limit (4096 exceeds `halfvec` too), so they'd need MRL truncation. Not worth it at our scale.

### 2.2 Serving on AMD, ranked by "works tonight"

| # | Option | Status on our hardware | Verdict |
|---|---|---|---|
| 1 | **sentence-transformers + FastAPI on PyTorch ROCm** | Torch already works on both boxes (user). Qwen3-Embedding needs `transformers>=4.51.0` and `sentence-transformers>=2.7.0` (Qwen card). | **Primary.** Pure HF stack on ROCm, which is load-bearing for both the HF and AMD prizes. |
| 2 | **llama.cpp `llama-server --embedding`** (HIP) | Official `Qwen3-Embedding-0.6B-Q8_0.gguf` (639 MB) and `f16` (1.2 GB). The card's command: `llama-server -m model.gguf --embedding --pooling last -ub 8192` (https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF). The server serves `/v1/embeddings`, and `--embd-normalize` defaults to 2 (L2) (https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md). | **Fallback** if torch misbehaves, and the obvious choice if System 2 already runs a HIP llama.cpp build. Vulkan works too, but it isn't ROCm (weak for the AMD prize). |
| 3 | Lemonade | `/v1/embeddings` only for `llamacpp`/`flm` recipes. Reranking is listed only as a `/rerank` label, undocumented (https://lemonade-server.ai/docs/api/openai/). | Needs root to install (prior file). Only worth it if Lemonade is already running. |
| 4 | vLLM pooling | `--runner pooling` (usually auto-detected), served at `/v1/embeddings` (https://docs.vllm.ai/en/latest/models/pooling_models.html). The Qwen card shows `LLM(..., task="embed")` with vllm ≥0.8.5. | The AMD image is about 25 GB with slow warmups (prior file). Skip. |
| 5 | Infinity | Its ROCm image is "for MI200/MI300", "not build via CI/CD", so pin the version (https://github.com/michaelfeil/infinity). | Skip: not aimed at Radeon. |
| 6 | HF TEI | "AMD ROCm support is **experimental**. Only AMD Instinct GPUs (MI200, MI300 series) are tested." It's a source build: Rust plus protobuf plus a Python backend (https://huggingface.co/docs/text-embeddings-inference/amd_gpu.md). | **Skip.** It's untested on Radeon and has the longest setup. |

**gfx1151/gfx1201 gotchas**
- **Attention.** Don't enable `flash_attention_2`, even though the Qwen card suggests it. Flash-attn for gfx1151 is unverified (prior file). Keep the default SDPA.
- **dtype.** Use bf16 if `torch.cuda.is_bf16_supported()`, otherwise fp32. Never fp16 for the Gemma models (their cards say so).
- **Torch replacement.** After `pip install`, check that `torch.version.hip` is still set, so pip didn't swap in a CUDA wheel (prior file).
- **Shared memory on Strix Halo.** It shares about 30 GB of usable GPU memory with the LLM (prior file). Qwen3-0.6B in bf16 is about 1.2 GB of weights (f16 GGUF size as a proxy).
- **gfx1201 is new.** A llama.cpp discussion reports incomplete HIP kernel/runtime support on gfx1201, though for a Mamba model (https://github.com/ggml-org/llama.cpp/discussions/20881). For llama.cpp on the R9700, ROCm led prompt processing on dense 7–8B models (https://www.phoronix.com/review/rocm-71-llama-cpp-vulkan/3). Embedding is prefill-only.
- **Don't mix backends.** GGUF and ST vectors can differ in EOS handling and pooling. A third-party GGUF card says recent llama.cpp appends EOS automatically (https://huggingface.co/Mungert/Qwen3-Embedding-0.6B-GGUF, **unverified**). Embed the corpus and the queries with the same backend.
- **Latency.** I found no published embedding numbers for gfx1151/gfx1201 (**unverified**). Measure it (§3.3) and put the number in the AMD pitch.

### 2.3 pgvector in Neon

- **Version.** Neon ships pgvector **0.8.0 on PG14–17 and 0.8.6 on PG18** (https://neon.com/docs/extensions/pg-extensions). Upstream latest is v0.8.7 (https://github.com/pgvector/pgvector).
- **Dimension limits.**
  - Storage: up to 16,000 dims.
  - HNSW/IVFFlat: `vector` ≤ 2,000, `halfvec` ≤ 4,000, `bit` ≤ 64,000 (https://github.com/pgvector/pgvector, https://neon.com/docs/extensions/pgvector).
  - `halfvec` roughly halves storage and memory (Neon page).
- **Exact search is the default.** "By default, pgvector performs exact nearest neighbor search, which provides perfect recall." Adding an index makes search approximate (pgvector README; Neon page). With a few thousand rows, a sequential scan is very likely fast enough. That's my estimate (**unverified**), so measure with `EXPLAIN ANALYZE`.
- **If we add an index, use HNSW.**
  - It has a better speed-recall tradeoff than IVFFlat and can be built on an empty table. IVFFlat needs data before you build it.
  - Defaults: `m` 16, `ef_construction` 64, `hnsw.ef_search` 40 (Neon page).
  - DDL: `USING hnsw (embedding vector_cosine_ops)` (pgvector README).
- **Filters with ORDER BY `<=>`.**
  - Exact search: put a B-tree index on the filter columns (Neon page; pgvector README).
  - With an ANN index, filters are applied after the index scan, so you can get fewer than LIMIT rows. Since 0.8.0, `SET hnsw.iterative_scan = strict_order` (or `relaxed_order`) fixes this (pgvector README). Neon's 0.8.0 should include it (inferred from the version; Neon's page doesn't mention it).
  - Use partial indexes when there are only a few filter values (both sources).
- **Normalized vectors.** "If vectors are normalized to length 1 … use inner product for best performance" (`<#>`, pgvector README). Qwen3's ST pipeline normalizes (modules.json), so `<=>` and `<#>` give the same ranking.
- **Hybrid search.**
  - The pgvector README says: "Use together with Postgres full-text search for hybrid search … Reciprocal Rank Fusion or a cross-encoder."
  - RRF scores each row as 1/(k+rank) with k ≈ 60 and needs no score normalization (https://api.pgxn.org/src/pg_search/pg_search-0.25.3/docs/documentation/hybrid/rrf.mdx).
  - Lexical search catches exact tokens such as error codes that vectors miss (https://docs.railway.com/guides/hybrid-search-postgres-pgvector).
  - **Is it worth it for us?** Partly. IDs like "Pump 05" or "HX-204" should mainly be **metadata columns plus WHERE**, not something we hope the embedding matches. A `simple`-config tsvector is cheap to add (one generated column plus a GIN index) and helps with manual error codes and free-text notes. How the `simple` parser splits "HX-204" is **unverified**; test it with `SELECT to_tsvector('simple','HX-204 fault')`.

## 3. Recommendation

### 3.1 Choices

- **Primary model.**
  - `Qwen/Qwen3-Embedding-0.6B`, full **1024 dims**, Apache-2.0.
  - Query instruction (no prefix on documents), customized as the card recommends: `Instruct: Given an operator question about a SPOT robot inspection, retrieve relevant inspection events, anomaly notes, operator notes, and Spot manual passages\nQuery:`
- **Fallback model.** `Snowflake/snowflake-arctic-embed-l-v2.0`, **1024 dims**, Apache-2.0. Queries get the `query: ` prefix (`prompt_name="query"`), documents get none. It uses the same column width, so falling back only means re-embedding, and it's an encoder (XLM-R) with a different code path from Qwen.
- **Reranker (stretch).** `Qwen/Qwen3-Reranker-0.6B` on the top 20.
- **Serving.** sentence-transformers + FastAPI on the AMD torch wheels. The fallback is `llama-server` with the official Q8_0 GGUF.
- **Index.** Exact search plus B-tree indexes on the metadata columns. Add HNSW `vector_cosine_ops` (with `hnsw.iterative_scan`) only if `EXPLAIN ANALYZE` shows it's slow.

### 3.2 Install and launch (the venv that already has AMD torch)

```bash
pip install "sentence-transformers>=2.7.0" "transformers>=4.51.0" fastapi uvicorn
python -c "import torch;print(torch.__version__, torch.version.hip, torch.cuda.is_available())"  # must still show +rocm
```

```python
# amd/embed/server.py
import torch, time
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
MODEL = "Qwen/Qwen3-Embedding-0.6B"
QI = ("Instruct: Given an operator question about a SPOT robot inspection, retrieve relevant "
      "inspection events, anomaly notes, operator notes, and Spot manual passages\nQuery:")
dt = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float32
m = SentenceTransformer(MODEL, device="cuda", model_kwargs={"torch_dtype": dt},
                        tokenizer_kwargs={"padding_side": "left"})
app = FastAPI()
class Req(BaseModel):
    texts: list[str]
    kind: str = "document"   # "query" | "document"
@app.post("/embed")
def embed(r: Req):
    t = time.perf_counter()
    v = m.encode(r.texts, prompt=QI if r.kind == "query" else "", normalize_embeddings=True, batch_size=32)
    return {"model": MODEL, "dim": v.shape[1], "ms": (time.perf_counter()-t)*1e3, "vectors": v.tolist()}
```

`uvicorn server:app --host 0.0.0.0 --port 8090`

The `padding_side="left"` setting follows the card's suggestion for last-token pooling. **Unverified:** whether the ST pooling already handles right-padding correctly.

**Fallback launch** (from the GGUF card; HIP build as in the prior file):

```bash
hf download Qwen/Qwen3-Embedding-0.6B-GGUF Qwen3-Embedding-0.6B-Q8_0.gguf --local-dir models
llama-server -m models/Qwen3-Embedding-0.6B-Q8_0.gguf --embedding --pooling last -ub 8192 --port 8091
```

Prepend the same `Instruct: …\nQuery:` string to query text yourself. The `hf download` CLI form is **unverified** for our installed `huggingface_hub` version (older versions use `huggingface-cli download`).

### 3.3 DDL (Neon)

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE rag_chunk (
  id          bigserial PRIMARY KEY,
  source_type text NOT NULL CHECK (source_type IN ('event','anomaly','ack_note','s2_explanation','manual')),
  source_ref  text NOT NULL,          -- row id / "manual p.42" for citations
  mission_id  text, step int, asset_id text, waypoint_id text,
  anomaly_type text, severity text, manual_page int,
  content     text NOT NULL,
  content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
  embedding   vector(1024) NOT NULL,
  embed_model text NOT NULL DEFAULT 'Qwen/Qwen3-Embedding-0.6B',
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON rag_chunk (asset_id);
CREATE INDEX ON rag_chunk (mission_id);
CREATE INDEX ON rag_chunk (source_type);
CREATE INDEX ON rag_chunk USING gin (content_tsv);
-- Only if EXPLAIN ANALYZE says exact scan is slow:
-- CREATE INDEX ON rag_chunk USING hnsw (embedding vector_cosine_ops);
```

### 3.4 Query patterns (`$1` = query vector as the text `'[0.01,…]'`)

```sql
-- Dense + metadata filter (exact search)
SELECT id, source_type, source_ref, content, 1 - (embedding <=> $1::vector) AS sim
FROM rag_chunk
WHERE embed_model = 'Qwen/Qwen3-Embedding-0.6B'
  AND ($2::text IS NULL OR asset_id = $2)
  AND source_type = ANY($3::text[])
ORDER BY embedding <=> $1::vector
LIMIT 8;
-- If an HNSW index exists, run first: SET LOCAL hnsw.iterative_scan = strict_order;

-- Hybrid (RRF, k=60); $4 = raw query text
WITH sem AS (
  SELECT id, row_number() OVER (ORDER BY embedding <=> $1::vector) AS r
  FROM rag_chunk WHERE ($2::text IS NULL OR asset_id = $2)
  ORDER BY embedding <=> $1::vector LIMIT 20),
lex AS (
  SELECT id, row_number() OVER (ORDER BY ts_rank_cd(content_tsv, q) DESC) AS r
  FROM rag_chunk, websearch_to_tsquery('simple', $4) q
  WHERE content_tsv @@ q AND ($2::text IS NULL OR asset_id = $2)
  ORDER BY ts_rank_cd(content_tsv, q) DESC LIMIT 20)
SELECT c.id, c.source_ref, c.content,
       COALESCE(1.0/(60+sem.r),0) + COALESCE(1.0/(60+lex.r),0) AS rrf
FROM sem FULL OUTER JOIN lex USING (id) JOIN rag_chunk c USING (id)
ORDER BY rrf DESC LIMIT 8;
```

**Pitch:** the MCP tool returns `source_ref` for citations; log `/embed` `ms` for an AMD latency slide; credit "Qwen3-Embedding-0.6B via sentence-transformers on ROCm" in Devpost.

## 4. Open questions

- No ROCm embedding latency or throughput is published for gfx1151/gfx1201. Benchmark both boxes (batch 1 and batch 32).
- Whether ST's Qwen3 last-token pooling is correct without `padding_side="left"`, and whether llama.cpp vectors match ST vectors (EOS handling).
- How the `simple` text-search config tokenizes asset IDs like "HX-204".
- The minimum sentence-transformers version for `CrossEncoder("Qwen/Qwen3-Reranker-0.6B")`.
- Whether EmbeddingGemma 2 loads with AMD's torch 2.12 wheel and a released transformers version. Its card was built with `5.18.0.dev0`. Retry it after the demo is stable; its multimodal image embeddings could later match SPOT inspection photos.
- Lemonade's `/rerank` route is undocumented. The HF TEI-on-Radeon path is untested.
