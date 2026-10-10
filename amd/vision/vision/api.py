"""FastAPI app: POST /v1/vision, POST /v1/ocr, GET /v1/info, GET /health (docs/vision-contract.md).

Endpoints are sync (FastAPI runs them in its threadpool); OCR calls are serialised by textaxes' engine lock.
Hardening (contract vision.2): X-API-Key required unless VISION_ALLOW_NO_AUTH=1 (only /health is open); the request
body is capped before the JSON is parsed (BodyLimit); at most VISION_MAX_CONCURRENCY analyses run at once, a request
waits VISION_QUEUE_TIMEOUT_S for a slot, then gets 503 (cache hits never wait).
"""
import hashlib
import hmac
import json
import logging
import threading
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from . import SERVICE_VERSION, textaxes
from .compare import TOLERANCES
from .config import Settings
from .contract import OcrRequest, OcrResponse, VisionRequest, VisionResponse
from .imageio import FORMATS, ImageError
from .pipeline import VERSION, analyze, ocr_only
from .router import ACTION_TYPE_MAP, KINDS

log = logging.getLogger("vision")
KEY_HEADER = "X-API-Key"
CACHE_HEADER = "X-Vision-Cache"
OPEN_PATHS = frozenset({"/health"})


class BodyLimit:
    """ASGI middleware: 413 for a body over `max_bytes`, from Content-Length up front and while streaming."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        length = dict(scope.get("headers") or []).get(b"content-length")
        if length is not None and (not length.isdigit() or int(length) > self.max_bytes):
            response = JSONResponse({"detail": "request body over %d bytes" % self.max_bytes}, status_code=413)
            return await response(scope, receive, send)
        seen = 0

        async def limited():
            nonlocal seen
            msg = await receive()
            if msg.get("type") == "http.request":
                seen += len(msg.get("body") or b"")
                if seen > self.max_bytes:   # chunked body: FastAPI re-raises HTTPException as is
                    raise HTTPException(status_code=413, detail="request body over %d bytes" % self.max_bytes)
            return msg

        return await self.app(scope, limited, send)


class LRU:
    def __init__(self, size: int):
        self.size = size
        self._d: "OrderedDict[str, dict]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, k: str) -> Optional[dict]:
        if self.size <= 0:
            return None
        with self._lock:
            v = self._d.get(k)
            if v is not None:
                self._d.move_to_end(k)
            return v

    def put(self, k: str, v: dict) -> None:
        if self.size <= 0:
            return
        with self._lock:
            self._d[k] = v
            self._d.move_to_end(k)
            while len(self._d) > self.size:
                self._d.popitem(last=False)


def _cache_key(req: dict) -> str:
    img = hashlib.sha256(req["image_b64"].encode("ascii", "ignore")).hexdigest()
    opts = {k: v for k, v in req.items() if k not in ("image_b64", "request_id")}
    return img + ":" + hashlib.sha256((json.dumps(opts, sort_keys=True, default=str)
                                       + SERVICE_VERSION).encode()).hexdigest()


def create_app(settings: Optional[Settings] = None, warm: bool = True) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.check()
    expected = settings.api_key.encode("ascii") if settings.api_key else None
    if expected is None:
        log.warning("VISION_ALLOW_NO_AUTH=1: every route is open (tests only)")
    textaxes.configure(settings.ocr_threads)
    cache = LRU(settings.cache_size)
    slots = threading.BoundedSemaphore(settings.max_concurrency)

    @asynccontextmanager
    async def lifespan(app):
        if warm:   # load the ONNX models off the request path; /health reports ocr_ready
            threading.Thread(target=textaxes.engine, name="ocr-warmup", daemon=True).start()
        yield

    # No /docs or /openapi.json: docs/vision-contract.md is the contract (and they would bypass nothing useful).
    app = FastAPI(title="SPOT vision/OCR", version=SERVICE_VERSION, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.slots = slots
    # Inside the auth middleware (added first): a 413 raised while streaming then reaches FastAPI's own exception
    # handling directly instead of being wrapped in BaseHTTPMiddleware's task group (which would turn it into a 400).
    app.add_middleware(BodyLimit, max_bytes=settings.max_body_bytes)

    @app.middleware("http")
    async def auth(request: Request, call_next):
        if expected is not None and request.url.path not in OPEN_PATHS:
            got = request.headers.get(KEY_HEADER)        # Starlette decodes header bytes as latin-1
            if got is None or not hmac.compare_digest(got.encode("latin-1"), expected):
                return JSONResponse({"detail": "missing or invalid %s" % KEY_HEADER}, status_code=401)
        return await call_next(request)

    def busy() -> JSONResponse:
        return JSONResponse({"detail": "vision busy: %d analyses running; retry shortly" % settings.max_concurrency},
                            status_code=503, headers={"Retry-After": "1"})

    @app.exception_handler(ImageError)
    async def image_error(_request: Request, exc: ImageError):
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    @app.get("/health")
    def health():
        return {"status": "ok", "ocr_ready": textaxes.ocr_ready(), "version": SERVICE_VERSION}

    @app.get("/v1/info")
    def info():
        return {"version": VERSION, "readers": [k for k in KINDS], "kinds": ["auto", *KINDS],
                "action_type_map": ACTION_TYPE_MAP, "tolerances": TOLERANCES,
                "limits": {"max_image_bytes": settings.max_image_bytes, "max_pixels": settings.max_pixels,
                           "max_body_bytes": settings.max_body_bytes, "work_max_side": settings.work_max_side,
                           "max_concurrency": settings.max_concurrency, "formats": list(FORMATS)}}

    @app.post("/v1/vision", response_model=VisionResponse, response_model_exclude_none=False)
    def vision(body: VisionRequest):
        req = body.model_dump()
        key = _cache_key(req)
        hit = cache.get(key)
        if hit is not None:
            return JSONResponse(hit, headers={CACHE_HEADER: "hit"})
        if not slots.acquire(timeout=settings.queue_timeout_s):
            return busy()
        try:
            out = analyze(req, settings)
        finally:
            slots.release()
        out = VisionResponse.model_validate(out).model_dump()
        cache.put(key, out)
        log.info("vision request=%s media=%s kind=%s readings=%d flags=%s %d ms", body.request_id, out["media_id"],
                 out["kind"], len(out["readings"]), ",".join(out["flags"]) or "-", out["latency_ms"])
        return JSONResponse(out, headers={CACHE_HEADER: "miss"})

    @app.post("/v1/ocr", response_model=OcrResponse)
    def ocr(body: OcrRequest):
        if not slots.acquire(timeout=settings.queue_timeout_s):
            return busy()
        try:
            return ocr_only(body.image_b64, body.upscale, settings)
        finally:
            slots.release()

    return app
