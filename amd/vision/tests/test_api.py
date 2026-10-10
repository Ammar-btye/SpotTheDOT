import base64
import io
import threading

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import synth
from vision.api import create_app
from vision.config import Settings
from vision.contract import VisionResponse
from vision.imageio import to_b64_png

KEY = "k" * 24
OPEN = Settings(allow_no_auth=True)      # tests only: the service refuses to start without a key otherwise


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(OPEN, warm=False)) as c:
        yield c


def gauge_b64(psi=117):
    return to_b64_png(synth.render_gauge(psi))


def test_health_and_info(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    info = client.get("/v1/info").json()
    assert "gauge" in info["readers"] and info["tolerances"]["temperature_c"] == 4.0
    assert info["version"]["contract"].endswith("vision.2")
    assert info["limits"]["formats"] == ["JPEG", "PNG", "WEBP"] and info["limits"]["max_pixels"] == 12_000_000


def test_vision_gauge_with_logged_value(client):
    body = {"request_id": "t1", "media_id": "g1", "action_type": "GAUGE_READING", "image_b64": gauge_b64(117),
            "logged": {"reading_id": "R9", "measurement_type": "PRESSURE_PSI", "value": 118.0}}
    r = client.post("/v1/vision", json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    VisionResponse.model_validate(out)
    assert out["media_id"] == "g1" and out["kind"] == "gauge" and out["router"]["method"] == "action_type"
    assert out["readings"][0]["id"] == "V1" and abs(out["readings"][0]["value"] - 117) <= 6
    assert out["comparison"]["agrees"] is True and out["alert"] is None
    assert out["annotated_image_b64"] != body["image_b64"]                 # never echoes the input
    Image.open(io.BytesIO(base64.b64decode(out["annotated_image_b64"]))).verify()
    assert any(w["text"] == "150" for w in out["ocr"])
    assert r.headers["X-Vision-Cache"] == "miss"
    assert client.post("/v1/vision", json=body).headers["X-Vision-Cache"] == "hit"


def test_vision_disagreement_raises_alert(client):
    body = {"action_type": "GAUGE_READING", "image_b64": gauge_b64(233), "annotate": False,
            "logged": {"reading_id": "R10", "measurement_type": "PRESSURE_PSI", "value": 150.0}}
    out = client.post("/v1/vision", json=body).json()
    assert out["comparison"]["agrees"] is False and out["alert"]["severity"] == 2
    assert out["alert"]["source"] == "vision.compare" and out["annotated_image_b64"] is None
    assert out["media_id"].startswith("sha256:")


def test_data_url_and_ocr_endpoint(client):
    b = "data:image/png;base64," + gauge_b64()
    r = client.post("/v1/ocr", json={"image_b64": b})
    assert r.status_code == 200
    out = r.json()
    assert out["width"] == 360 and {"150", "300"} <= {w["text"] for w in out["words"]}


@pytest.mark.parametrize("payload,status", [
    ({"image_b64": "!!!not base64!!!"}, 422),
    ({"image_b64": base64.b64encode(b"hello world, not an image").decode()}, 422),
    ({"image_b64": ""}, 422),
    ({}, 422),
    ({"image_b64": gauge_b64(), "kind": "xray"}, 422),
])
def test_bad_requests(client, payload, status):
    assert client.post("/v1/vision", json=payload).status_code == status


def test_size_limits():
    small = Settings(allow_no_auth=True, max_image_bytes=2000, max_pixels=10_000)
    with TestClient(create_app(small, warm=False)) as c:
        big = gauge_b64()                                                  # ~20 kB PNG
        assert c.post("/v1/vision", json={"image_b64": big}).status_code == 413
        assert c.post("/v1/ocr", json={"image_b64": big}).status_code == 413
        buf = io.BytesIO()
        Image.new("RGB", (200, 200), (0, 0, 0)).save(buf, format="PNG")   # tiny file, 40k pixels
        r = c.post("/v1/vision", json={"image_b64": base64.b64encode(buf.getvalue()).decode()})
        assert r.status_code == 422 and "pixels" in r.json()["detail"]


def test_api_key():
    with TestClient(create_app(Settings(api_key=KEY), warm=False)) as c:
        assert c.get("/health").status_code == 200
        assert c.get("/v1/info").status_code == 401
        assert c.post("/v1/ocr", json={"image_b64": gauge_b64()}, headers={"X-API-Key": "wrong"}).status_code == 401
        assert c.post("/v1/vision", json={"image_b64": gauge_b64()}, headers={"X-API-Key": ("é" * 24).encode("latin-1")}).status_code == 401
        assert c.get("/v1/info", headers={"X-API-Key": KEY}).status_code == 200
        for path in ("/docs", "/openapi.json", "/redoc"):                   # no open docs: 401 before routing
            assert c.get(path).status_code == 401


def test_auth_fails_closed():
    with pytest.raises(RuntimeError, match="VISION_API_KEY is not set"):
        create_app(Settings(), warm=False)
    for bad in ("short", " " + KEY, KEY + "\n", "ключ" * 5):
        with pytest.raises(RuntimeError, match="unusable") as e:
            create_app(Settings(api_key=bad), warm=False)
        assert bad not in str(e.value)


def test_settings_from_env(monkeypatch):
    monkeypatch.delenv("VISION_API_KEY", raising=False)
    monkeypatch.delenv("VISION_ALLOW_NO_AUTH", raising=False)
    with pytest.raises(RuntimeError, match="not set"):
        Settings.from_env()
    monkeypatch.setenv("VISION_ALLOW_NO_AUTH", "1")
    s = Settings.from_env()
    assert s.api_key is None and s.max_pixels == 12_000_000 and s.max_concurrency == 2
    monkeypatch.delenv("VISION_ALLOW_NO_AUTH")
    monkeypatch.setenv("VISION_MAX_PIXELS", "123")
    monkeypatch.setenv("VISION_API_KEY", "short")
    with pytest.raises(RuntimeError):
        Settings.from_env()
    monkeypatch.setenv("VISION_API_KEY", KEY)
    assert Settings.from_env().max_pixels == 123
    for name, bad in (("VISION_MAX_PIXELS", "lots"), ("VISION_MAX_PIXELS", "60000000"),
                      ("VISION_MAX_CONCURRENCY", "0"), ("VISION_QUEUE_TIMEOUT_S", "soon")):
        monkeypatch.setenv(name, bad)
        with pytest.raises(RuntimeError):
            Settings.from_env()
        monkeypatch.delenv(name)


def png_b64(w, h, mode="RGB"):
    buf = io.BytesIO()
    Image.new(mode, (w, h)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def test_pixel_limit_is_checked_from_the_header_before_decoding(client, monkeypatch):
    from vision import imageio
    loaded = []
    real_open = imageio.Image.open

    def spy_open(*a, **k):
        im = real_open(*a, **k)
        real_load = im.load
        im.load = lambda: loaded.append(im.size) or real_load()
        return im
    monkeypatch.setattr(imageio.Image, "open", spy_open)
    big = png_b64(4000, 3001)                                  # 12,004,000 px: tiny file, just over 12 MP
    r = client.post("/v1/vision", json={"image_b64": big})
    assert r.status_code == 422 and "pixels" in r.json()["detail"] and loaded == []


@pytest.mark.parametrize("fmt", ["BMP", "GIF", "TIFF"])
def test_only_jpeg_png_webp_are_accepted(client, fmt):
    buf = io.BytesIO()
    Image.fromarray(synth.render_gauge(100)).save(buf, format=fmt)
    r = client.post("/v1/vision", json={"image_b64": base64.b64encode(buf.getvalue()).decode()})
    assert r.status_code == 422 and "JPEG, PNG or WebP" in r.json()["detail"]


def test_webp_is_accepted(client):
    buf = io.BytesIO()
    Image.fromarray(synth.render_gauge(100)).save(buf, format="WEBP", quality=95)
    r = client.post("/v1/vision", json={"kind": "gauge", "annotate": False,
                                        "image_b64": base64.b64encode(buf.getvalue()).decode()})
    assert r.status_code == 200 and r.json()["readings"]


def test_request_body_cap_before_parsing():
    s = Settings(allow_no_auth=True, max_image_bytes=3000)
    with TestClient(create_app(s, warm=False)) as c:
        body = '{"image_b64": "%s"}' % ("A" * (s.max_body_bytes + 10))
        r = c.post("/v1/vision", content=body, headers={"Content-Type": "application/json"})
        assert r.status_code == 413 and "request body" in r.json()["detail"]

        def chunks():                                          # no Content-Length: counted while streaming
            yield b'{"image_b64": "'
            for _ in range(s.max_body_bytes // 1000 + 2):
                yield b"A" * 1000
            yield b'"}'
        r = c.post("/v1/vision", content=chunks(), headers={"Content-Type": "application/json"})
        assert r.status_code == 413
        assert c.post("/v1/vision", json={"image_b64": "A" * 4100}).status_code == 413   # base64 over the image cap


def test_concurrency_limit_returns_503_and_cache_hits_never_wait():
    s = Settings(allow_no_auth=True, max_concurrency=1, queue_timeout_s=0.2)
    app = create_app(s, warm=False)
    with TestClient(app) as c:
        body = {"kind": "gauge", "annotate": False, "image_b64": gauge_b64(80)}
        assert c.post("/v1/vision", json=body).status_code == 200      # warms the cache
        assert app.state.slots.acquire(timeout=1)                        # one analysis "running"
        try:
            r = c.post("/v1/vision", json=dict(body, kind="auto"))
            assert r.status_code == 503 and r.headers["Retry-After"] == "1"
            assert c.post("/v1/ocr", json={"image_b64": gauge_b64(80)}).status_code == 503
            hit = c.post("/v1/vision", json=body)
            assert hit.status_code == 200 and hit.headers["X-Vision-Cache"] == "hit"
        finally:
            app.state.slots.release()
        assert c.post("/v1/vision", json=dict(body, kind="auto")).status_code == 200


def test_slots_are_released_after_errors():
    s = Settings(allow_no_auth=True, max_concurrency=1, queue_timeout_s=0.2)
    app = create_app(s, warm=False)
    with TestClient(app) as c:
        for _ in range(3):
            assert c.post("/v1/vision", json={"image_b64": "!!!not base64!!!"}).status_code == 422
        assert app.state.slots.acquire(timeout=0.1)
        app.state.slots.release()


def test_concurrent_requests_queue_within_the_timeout():
    s = Settings(allow_no_auth=True, max_concurrency=1, queue_timeout_s=10)
    app = create_app(s, warm=False)
    out = []
    with TestClient(app) as c:
        def call(psi):
            out.append(c.post("/v1/vision", json={"kind": "gauge", "annotate": False,
                                                   "image_b64": gauge_b64(psi)}).status_code)
        ts = [threading.Thread(target=call, args=(p,)) for p in (60, 90, 120)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
    assert out == [200, 200, 200]


def test_reader_failure_is_contained(client, monkeypatch):
    from vision import pipeline

    def boom(*a, **k):
        raise RuntimeError("bug")
    monkeypatch.setattr(pipeline.gauge, "read", boom)
    out = client.post("/v1/vision", json={"kind": "gauge", "image_b64": to_b64_png(synth.render_gauge(42)),
                                          "annotate": False}).json()
    assert "READER_FAILED" in out["flags"] and out["readings"] == [] and out["ocr"]


def test_rgba_and_grayscale_inputs(client):
    rgba = np.dstack([synth.render_gauge(100), np.full((360, 360), 255, np.uint8)])
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, format="PNG")
    r = client.post("/v1/vision", json={"kind": "gauge", "image_b64": base64.b64encode(buf.getvalue()).decode()})
    assert r.status_code == 200 and r.json()["readings"]
    g = Image.fromarray(synth.render_gauge(100)).convert("L")
    buf = io.BytesIO()
    g.save(buf, format="JPEG")
    r = client.post("/v1/vision", json={"kind": "gauge", "image_b64": base64.b64encode(buf.getvalue()).decode()})
    assert r.status_code == 200
