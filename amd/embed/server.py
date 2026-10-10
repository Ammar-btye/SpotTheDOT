"""OpenAI-compatible embedding service (contract §1): POST /v1/embeddings, GET /health.

sentence-transformers on PyTorch: ROCm on the AMD box (torch sees the Radeon as "cuda"), MPS or CPU locally.
It is the fallback for when llama-server / TEI aren't used; clients can't tell the difference.

  EMBED_MODEL=Qwen/Qwen3-Embedding-0.6B python server.py           # port EMBED_PORT (default 8081)
  uvicorn server:app --host 0.0.0.0 --port 8081

Env: EMBED_MODEL (required), EMBED_DIM (optional: checked against the model, or used to truncate an MRL model
if smaller), EMBED_DEVICE (cuda|mps|cpu, auto), EMBED_DTYPE (bfloat16|float16|float32, auto: bf16 on a GPU that
supports it, else fp32), EMBED_BATCH (32), EMBED_MAX_INPUTS (2048), EMBED_NORMALIZE (1), EMBED_PADDING_SIDE
(left for Qwen3-Embedding, per its card), HF_HOME (model cache). Prefixes are NOT applied here: clients add
EMBED_QUERY_PREFIX / EMBED_DOC_PREFIX (amd/embed/client.py), exactly as they would for llama-server.
"""
import logging
import os
import threading
import time
from typing import List, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

log = logging.getLogger("embed")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MODEL_ID = os.environ.get("EMBED_MODEL", "").strip()
WANT_DIM = int(os.environ["EMBED_DIM"]) if os.environ.get("EMBED_DIM") else None
BATCH = int(os.environ.get("EMBED_BATCH", "32"))
MAX_INPUTS = int(os.environ.get("EMBED_MAX_INPUTS", "2048"))
NORMALIZE = os.environ.get("EMBED_NORMALIZE", "1") not in ("0", "false", "False")

state = {"status": "loading", "error": None}
_lock = threading.Lock()   # one encode at a time on the GPU


def _pick_device(torch) -> str:
    want = os.environ.get("EMBED_DEVICE")
    if want:
        return want
    if torch.cuda.is_available():          # ROCm builds report the Radeon GPU as "cuda"
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _pick_dtype(torch, device: str):
    name = os.environ.get("EMBED_DTYPE")
    if name:
        return getattr(torch, name)
    if device == "cuda" and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    return torch.float32


def _load() -> None:
    try:
        if not MODEL_ID:
            raise RuntimeError("EMBED_MODEL is not set")
        import torch
        from sentence_transformers import SentenceTransformer
        device = _pick_device(torch)
        dtype = _pick_dtype(torch, device)
        t0 = time.perf_counter()
        trust = os.environ.get("EMBED_TRUST_REMOTE_CODE") == "1"
        try:   # transformers >= 4.56 calls it `dtype`; older versions only know `torch_dtype`
            model = SentenceTransformer(MODEL_ID, device=device, model_kwargs={"dtype": dtype}, trust_remote_code=trust)
        except TypeError:
            model = SentenceTransformer(MODEL_ID, device=device, model_kwargs={"torch_dtype": dtype},
                                        trust_remote_code=trust)
        pad = os.environ.get("EMBED_PADDING_SIDE") or ("left" if "qwen3-embedding" in MODEL_ID.lower() else None)
        if pad and getattr(model, "tokenizer", None) is not None:
            model.tokenizer.padding_side = pad
        native = model.get_sentence_embedding_dimension()
        dim = native
        if WANT_DIM and WANT_DIM != native:
            if WANT_DIM < native:
                model.truncate_dim = WANT_DIM            # Matryoshka truncation (Qwen3-Embedding supports 32..1024)
                dim = WANT_DIM
                log.warning("truncating %d-d embeddings to EMBED_DIM=%d", native, WANT_DIM)
            else:
                raise RuntimeError("EMBED_DIM=%d exceeds the model's %d dims" % (WANT_DIM, native))
        model.encode(["warmup"], batch_size=1, show_progress_bar=False)
        state.update(model=model, dim=dim, device=device, dtype=str(dtype).replace("torch.", ""),
                     torch=torch.__version__, hip=getattr(torch.version, "hip", None),
                     gpu=torch.cuda.get_device_name(0) if device == "cuda" else None,
                     load_s=round(time.perf_counter() - t0, 1), status="ok")
        log.info("loaded %s on %s (%s), dim=%d in %.1fs", MODEL_ID, device, state["dtype"], dim, state["load_s"])
    except Exception as e:  # surfaced on /health
        log.exception("model load failed")
        state.update(status="error", error=repr(e))


app = FastAPI(title="spot-embed")


@app.on_event("startup")
def _startup() -> None:
    threading.Thread(target=_load, daemon=True).start()   # /health answers 503 "loading" during the download


class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: Optional[str] = None
    encoding_format: Optional[str] = "float"
    dimensions: Optional[int] = None
    user: Optional[str] = None


@app.get("/health")
def health():
    body = {k: v for k, v in state.items() if k != "model"}
    body["model"] = MODEL_ID
    return JSONResponse(body, status_code=200 if state["status"] == "ok" else 503)


@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": MODEL_ID, "object": "model", "owned_by": "local"}]}


@app.post("/v1/embeddings")
def embeddings(req: EmbeddingRequest):
    if state["status"] != "ok":
        raise HTTPException(503, "model %s: %s" % (state["status"], state.get("error") or "loading"))
    texts = [req.input] if isinstance(req.input, str) else list(req.input)
    if not texts:
        raise HTTPException(400, "input is empty")
    if len(texts) > MAX_INPUTS:
        raise HTTPException(413, "too many inputs (%d > %d)" % (len(texts), MAX_INPUTS))
    if req.encoding_format not in (None, "float"):
        raise HTTPException(400, "only encoding_format=float is supported")
    model = state["model"]
    with _lock:
        t0 = time.perf_counter()
        vecs = model.encode(texts, batch_size=BATCH, normalize_embeddings=NORMALIZE, convert_to_numpy=True,
                             show_progress_bar=False)
        ms = (time.perf_counter() - t0) * 1000
    if req.dimensions:
        if req.dimensions > vecs.shape[1]:
            raise HTTPException(400, "dimensions > %d" % vecs.shape[1])
        vecs = vecs[:, :req.dimensions]
    try:
        n_tok = sum(len(ids) for ids in model.tokenizer(texts)["input_ids"])
    except Exception:
        n_tok = sum(len(t.split()) for t in texts)
    return {
        "object": "list",
        "model": MODEL_ID,
        "data": [{"object": "embedding", "index": i, "embedding": v.tolist()} for i, v in enumerate(vecs)],
        "usage": {"prompt_tokens": n_tok, "total_tokens": n_tok},
        # extras (ignored by OpenAI clients): evidence for the AMD latency numbers
        "timing": {"ms": round(ms, 2), "tokens_per_sec": round(n_tok / (ms / 1000), 1) if ms else None,
                   "device": state["device"], "dtype": state["dtype"], "gpu": state["gpu"]},
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("EMBED_HOST", "0.0.0.0"), port=int(os.environ.get("EMBED_PORT", "8081")))
