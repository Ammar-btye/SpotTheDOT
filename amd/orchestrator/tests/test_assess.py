"""The assessment graph: routing branches, vision, System 2 pass-through and fallbacks, deadlines."""
import base64
import copy
import json
import time

from fakes import ESCALATED_PACKET, TINY_JPEG, no_s1_packet, routine_packet
from orchestrator.assess import canonical_event, route_reasons, vision_rows

NODES_FULL = ["load_context", "system1", "route", "vision", "system2", "finalize"]


def _nodes(out):
    return [t["node"] for t in out["trace"]]


def test_escalated_flag_takes_full_path_and_passes_system2_through(make_client, world):
    out = make_client().post("/v1/assess", json={"flag_id": 42, "request_id": "r-1"}).json()
    assert out["route"] == "full"
    assert {"laya_escalate", "laya_priority", "flag_escalated", "flag_priority", "validator",
            "rules_fired"} <= set(out["route_reasons"])
    assert _nodes(out) == NODES_FULL
    assert out["source"] == "system2" and out["fallback_reason"] is None
    assert out["answer"] == world.system2_reply["answer"]                      # passed through unchanged
    assert out["evidence"] == world.system2_reply["evidence"]
    assert out["system2"]["path"] == "llm" and out["confidence"] == 0.85
    assert out["citations"] == ["F2", "V1"] and out["recommended_action_code"] == "SCHEDULE_MAINTENANCE"
    assert out["vision"] is None and world.of("vision") == []                  # no image -> vision skipped
    (call,) = world.of("system2")
    body = call["body"]
    assert call["headers"]["x-api-key"] == "s2-key-0123456789" and call["headers"]["x-request-id"] == "r-1"
    assert body["flag_id"] == 42 and body["request_id"] == "r-1" and body["event"] is None
    assert body["flag"]["id"] == "flag:42" and body["reasons"][-1] == "TEMPERATURE_C 83.5 above 80"
    assert "image_b64" not in body and "vision" not in body["context"]
    assert body["context"]["system1"] == ESCALATED_PACKET["system1"]          # packet answers, unchanged
    assert out["system1"]["source"] == "packet"
    assert world.of("mcp")[0]["headers"]["x-request-id"] == "r-1"
    assert world.of("gateway:system1") == []


def test_routine_flag_routes_system1_only(make_client, world):
    world.packet = routine_packet()
    out = make_client().post("/v1/assess", json={"flag_id": 42}).json()
    assert out["route"] == "system1_only" and out["route_reasons"] == []
    assert _nodes(out) == ["load_context", "system1", "route", "system1_only"]
    assert out["source"] == "system1" and world.of("system2") == [] and world.of("vision") == []
    assert out["recommended_action_code"] in ("MONITOR", "NO_ACTION", "REINSPECT_NEXT_ROUTE")
    assert "escalate=B" in out["reasoning"] and out["confidence"] == 0.91
    assert out["request_id"].startswith("o-")


def test_operator_image_forces_full_path_with_vision_rows(make_client, world):
    world.packet = routine_packet()
    out = make_client().post("/v1/assess", json={"flag_id": 42, "image_b64": "data:image/jpeg;base64," + TINY_JPEG,
                                                 "return_image": True}).json()
    assert out["route"] == "full" and out["route_reasons"] == ["operator_image"]
    (vcall,) = world.of("vision")
    vb = vcall["body"]
    assert vb["image_b64"] == TINY_JPEG and vb["kind"] == "auto" and vb["action_type"] == "THERMAL_INSPECTION"
    assert vb["logged"] == {"reading_id": "R0042", "measurement_type": "TEMPERATURE_C", "value": 83.5, "unit": "C"}
    rows = out["vision"]["rows"]
    assert rows[0] == {"id": "V1", "tool": "colorbar_lut", "kind": "thermal", "quantity": "max_temperature",
                       "value": 99.8, "unit": "°C", "confidence": 0.8, "trust": "HIGH", "flags": ["CLIPPED"],
                       "bound": "lower", "pairing": "linked", "logged_id": "reading:R0042", "logged_value": 83.5,
                       "delta": 16.3, "agrees": False}
    assert out["vision"]["alert"] == world.vision_reply["alert"] and "demo_alert" not in out["vision"]
    assert rows[1]["trust"] == "LOW" and "logged_id" not in rows[1]
    assert out["vision"]["annotated_image_b64"] == TINY_JPEG
    body = world.of("system2")[0]["body"]
    assert body["context"]["vision"] == rows
    assert body["context"]["ocr"][0] == {"text": "100", "conf": 0.99}
    assert [o["text"] for o in body["context"]["ocr"]] == ["100", "20", "noise"]
    assert body["image_b64"] == TINY_JPEG


def test_ocr_top_n_and_return_image_default(make_client, world):
    world.packet = routine_packet()
    out = make_client(OCR_TOP_N=1).post("/v1/assess", json={"flag_id": 42, "image_b64": TINY_JPEG}).json()
    assert out["vision"]["ocr"] == [{"text": "100", "conf": 0.99}]
    assert "annotated_image_b64" not in out["vision"]                         # small responses by default


def test_demo_image_mapping_by_action_type(make_client, world, tmp_path):
    (tmp_path / "thermal_pump_bearing_01.jpg").write_bytes(base64.b64decode(TINY_JPEG))
    out = make_client(DEMO_IMAGES=1, DEMO_IMAGES_DIR=str(tmp_path)).post("/v1/assess", json={"flag_id": 42}).json()
    (vcall,) = world.of("vision")
    assert vcall["body"]["media_id"] == "thermal_pump_bearing_01" and vcall["body"]["kind"] == "thermal"
    assert out["vision"]["pairing"] == "demo" and all(r["pairing"] == "demo" for r in out["vision"]["rows"])
    assert "operator_image" not in out["route_reasons"]                       # demo images never force the route
    # A-1: a demo image is not a reading of this asset: no logged value sent, no comparison, alert moved aside
    assert "logged" not in vcall["body"]
    assert not any({"logged_id", "logged_value", "delta", "agrees"} & set(r) for r in out["vision"]["rows"])
    assert out["vision"]["alert"] is None and out["vision"]["comparison"] is None
    assert out["vision"]["demo_alert"] == world.vision_reply["alert"]
    sent = world.of("system2")[0]["body"]["context"]["vision"]
    assert sent == out["vision"]["rows"] and all(r["pairing"] == "demo" for r in sent)


def test_demo_images_skip_navigation_and_routine(make_client, world, tmp_path):
    (tmp_path / "thermal_pump_bearing_01.jpg").write_bytes(base64.b64decode(TINY_JPEG))
    world.packet = copy.deepcopy(ESCALATED_PACKET)
    world.packet["event"]["action_type"] = "NAVIGATION"
    out = make_client(DEMO_IMAGES=1, DEMO_IMAGES_DIR=str(tmp_path)).post("/v1/assess", json={"flag_id": 42}).json()
    assert out["vision"] is None and world.of("vision") == []
    assert [t for t in out["trace"] if t["node"] == "vision"][0]["status"] == "skipped"


def test_system2_down_falls_back_to_template(make_client, world):
    world.system2_status = 503
    out = make_client().post("/v1/assess", json={"flag_id": 42, "image_b64": TINY_JPEG}).json()
    assert out["source"] == "template" and out["model"] == "template"
    assert "HTTP 503" in out["fallback_reason"]
    assert out["recommended_action_code"] == "SCHEDULE_MAINTENANCE"
    assert out["recommended_action"].startswith("SCHEDULE_MAINTENANCE: ")
    assert "Rule reading_above_safe_band" in out["reasoning"] and "Vision V1" in out["reasoning"]
    assert out["answer"].startswith("Yes. Escalate (P2, HIGH)")
    assert out["trace"][-1] == {**out["trace"][-1], "node": "finalize", "status": "fallback"}


def test_system2_invalid_reply_falls_back(make_client, world):
    world.system2_reply = {"answer": "", "evidence": []}
    out = make_client().post("/v1/assess", json={"flag_id": 42}).json()
    assert out["source"] == "template" and "no answer" in out["fallback_reason"]
    assert out["system2"] == {"answer": "", "evidence": []}


def test_system2_unset_uses_template(make_client, world):
    out = make_client(SYSTEM2_URL="").post("/v1/assess", json={"flag_id": 42}).json()
    assert out["source"] == "template" and out["fallback_reason"] == "SYSTEM2_URL is not set"
    assert [t for t in out["trace"] if t["node"] == "system2"][0]["status"] == "skipped"


def test_global_deadline_bounds_a_slow_system2(make_client, world):
    world.system2_delay = 5.0
    c = make_client(ORCH_DEADLINE_S=2)
    t0 = time.perf_counter()
    out = c.post("/v1/assess", json={"flag_id": 42}).json()
    assert time.perf_counter() - t0 < 3.0
    assert out["source"] == "template" and out["fallback_reason"].startswith("deadline:")
    assert [t for t in out["trace"] if t["node"] == "system2"][0]["status"] == "timeout"
    assert out["deadline_s"] == 2.0


def test_context_budget_and_mcp_down(make_client, world):
    world.mcp_down = True
    out = make_client().post("/v1/assess", json={"flag_id": 42}).json()
    assert out["route"] == "no_context" and out["context_source"] == "none"
    assert out["insufficient_context"] is True and out["recommended_action_code"] == "MANUAL_REVIEW"
    assert "MCP unavailable" in out["fallback_reason"] and world.of("system2") == []


def test_slow_mcp_hits_context_budget(make_client, world):
    world.mcp_delay = 3.0
    t0 = time.perf_counter()
    out = make_client(ORCH_DEADLINE_S=5).post("/v1/assess", json={"flag_id": 42}).json()   # 40 % -> 2 s
    assert time.perf_counter() - t0 < 3.0
    assert out["route"] == "no_context" and out["fallback_reason"].startswith("deadline: MCP")


def test_missing_laya_answers_are_fetched_via_gateway(make_client, world):
    world.packet = no_s1_packet()
    out = make_client().post("/v1/assess", json={"flag_id": 42}).json()
    (call,) = world.of("gateway:system1")
    assert call["headers"]["authorization"] == "Bearer sk-test"
    sent = json.loads(call["body"]["messages"][-1]["content"])
    assert sent["kind"] == "action"
    ev = sent["event"]
    assert ev["asset"] == {"asset_id": "PUMP-101", "asset_name": "Pump 101", "asset_type": "PUMP", "criticality": "HIGH"}
    assert ev["location"]["location_id"] == "WP07" and ev["battery_pct"] == 62 and ev["action_id"] == "A0136"
    assert ev["reading"] == {"measurement_type": "TEMPERATURE_C", "value": 83.5, "unit": "C", "quality": "GOOD"}
    assert out["system1"]["source"] == "gateway" and out["system1"]["model"] == "laya-ft"
    assert out["route"] == "system1_only"                                      # Laya says routine (B, P4)


def test_live_laya_answers_reach_system2(make_client, world):
    world.packet = copy.deepcopy(ESCALATED_PACKET)
    del world.packet["system1"]
    make_client().post("/v1/assess", json={"flag_id": 42})
    s1 = world.of("system2")[0]["body"]["context"]["system1"]
    assert {r["id"] for r in s1} == {"s1:live-action-escalate", "s1:live-action-priority"}
    assert s1[0]["p"] == 0.9 and s1[0]["meaning"].startswith("no, log only")


def test_gateway_failure_is_tolerated(make_client, world):
    world.packet = no_s1_packet()
    world.system1_status = 503
    out = make_client().post("/v1/assess", json={"flag_id": 42}).json()
    assert out["system1"]["source"] == "none"
    assert [t for t in out["trace"] if t["node"] == "system1"][0]["status"] == "error"
    assert out["route"] == "system1_only" and out["source"] == "system1"


def test_prefetched_context_skips_mcp(make_client, world):
    out = make_client().post("/v1/assess", json={"flag_id": 42, "context": routine_packet()}).json()
    assert world.of("mcp") == [] and out["context_source"] == "request" and out["route"] == "system1_only"


def test_bad_images_are_rejected(make_client):
    c = make_client(ORCH_MAX_IMAGE_B64=50)
    assert c.post("/v1/assess", json={"flag_id": 42, "image_b64": "!!!not base64!!!"}).status_code == 422
    assert c.post("/v1/assess", json={"flag_id": 42, "image_b64": "A" * 60}).status_code == 413
    assert c.post("/v1/assess", json={"flag_id": 0}).status_code == 422


def test_route_reasons_rule():
    p = routine_packet()
    assert route_reasons(p, p["system1"], False) == []
    assert route_reasons(p, [{"when": "action", "q": "escalate", "answer": "A"}], False) == ["laya_escalate"]
    assert route_reasons(p, [], True) == ["operator_image"]
    p["flag"]["reasons"].append({"rule": "battery_low", "detail": "battery 20 %"})
    assert route_reasons(p, [], False) == ["rules_fired"]
    # pre_action forecasts never route
    assert route_reasons(routine_packet(), [{"when": "pre_action", "q": "escalate", "answer": "A"}], False) == []


def test_canonical_mission_event():
    p = {"event": {"mission": {"id": "mission:M014", "configuration_version": "V1", "end_time": "2026-09-06T03:00",
                               "reported_status": "COMPLETED", "duration_min": 42, "start_battery_pct": 90,
                               "end_battery_pct": 30, "actions_total": 10, "actions_failed": 2,
                               "failure_types": {"PATH_BLOCKED": 2}, "anomalies_by_severity": {"LOW": 0, "MEDIUM": 1,
                                                                                               "HIGH": 0, "CRITICAL": 0}}}}
    kind, ev = canonical_event(p)
    assert kind == "mission" and ev["mission_id"] == "M014" and ev["failure_types"] == ["PATH_BLOCKED"]
    assert canonical_event({"event": {"mission": {"id": "mission:M1"}}}) is None
    assert canonical_event({}) is None
    p["event"]["mission"]["worst_anomaly"] = {"id": "anomaly:N1", "anomaly_type": "LEAK", "severity": "HIGH"}
    assert canonical_event(p) is None             # Laya needs the asset name + criticality: skip, don't misinform


def test_vision_rows_edge_cases():
    resp = {"kind": "gauge", "readings": [{"id": "bad", "value": float("nan"), "confidence": 7, "method": None},
                                          {"id": "V1", "value": 3, "confidence": 0.49}],
            "comparison": {"logged_id": "R1", "logged_value": 2, "delta": 1, "agrees": None}}
    rows = vision_rows(resp, "linked", 0.5, None)
    assert rows[0]["id"] == "V1" and rows[0]["confidence"] == 1.0 and "value" not in rows[0]
    assert rows[0]["tool"] == "vision" and rows[0]["logged_id"] == "R1" and "agrees" not in rows[0]
    assert rows[1]["id"] == "V2" and rows[1]["trust"] == "LOW"
    demo = vision_rows(resp, "demo", 0.5, "reading:R1")                       # A-1: never compared
    assert not any({"logged_id", "logged_value", "delta", "agrees"} & set(r) for r in demo)
