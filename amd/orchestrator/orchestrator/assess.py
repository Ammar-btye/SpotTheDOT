"""The assessment graph (POST /v1/assess): MCP context -> System 1 -> route -> vision -> System 2 -> finalize.

docs/orchestrator-contract.md is the spec. Rules this module keeps:
- Every node is bounded by min(its budget, the time left on the global deadline minus a reserve); a node with no time
  left is `skipped`, so the request always ends in `finalize` with at least the template. Dependency failures never
  raise out of a node: they become a trace entry with status error/timeout and, at the end, `fallback_reason`.
- The model never calls tools here and never adds numbers: System 2 enforces grounding and its reply passes through
  unchanged; vision numbers come from the vision service's code readers; the template uses packet values only.
- The routing rule (System 1 -> System 2) is `route_reasons()`; each reason that fired is returned to the caller.
- A demo image (DEMO_IMAGES=1, a kit sample chosen by action type) is not a reading of this asset: it is never
  compared with the logged reading, its alert is moved to `demo_alert`, and its rows carry no comparison fields.
- Only vision rows produced here reach System 2: `vision`/`ocr` already in the packet or the caller's context are
  dropped, so a caller cannot inject citable V# rows.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import copy
import logging
import math
import operator
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Tuple, TypedDict

from langgraph.graph import END, START, StateGraph

from .clients import GatewayClient, MCPClient, ServiceUnavailable, System2Client, VisionClient
from .config import CONTRACT_VERSION, Settings
from .template import VERDICT_RULES, normalize_system2, reasons, system1_answer, system2_problem, template_answer, \
    validator_of

log = logging.getLogger("orchestrator.assess")

CONTEXT_SHARE = 0.4                      # load_context gets at most this share of the deadline (backend parity)
MIN_NODE_S = 0.5                         # below this a node is skipped rather than started
S2_MAX_IMAGE_BYTES = 2 * 1024 * 1024     # System 2 accepts JPEG/PNG up to 2 MiB (amd/system2/analyst/packet.py)
MAX_VISION_ROWS = 16
V_ID = re.compile(r"^V[1-9][0-9]{0,2}$")
FLAG_TOKEN = re.compile(r"^[A-Z][A-Z_]{0,31}$")    # System 2 accepts only these (no digits), at most 8 per row
MAX_ROW_FLAGS = 8
FORCE_LOW_FLAGS = frozenset({"AMBIGUOUS_NEEDLE", "DEFAULT_SWEEP"})   # the reader is unsure which value it saw
VISION_FLOOR_S = 3.0                     # vision keeps at least this much when System 2's image budget is reserved
SYSTEM2_TEMPLATE_PATHS = ("fallback", "insufficient_context")   # System 2 paths that are not a model answer
DATA_URL = re.compile(r"^data:image/[A-Za-z0-9.+-]+;base64,", re.IGNORECASE)

# action_type -> (kit sample image, vision kind). kind None = let the vision router decide (acoustic: spectrogram
# vs acoustic imager). No kit CSV row links to an image, so these are always pairing "demo".
DEMO_IMAGES = {
    "THERMAL_INSPECTION": ("thermal_pump_bearing_01.jpg", "thermal"),
    "GAUGE_READING": ("gauge_pressure_01.jpg", "gauge"),
    "ACOUSTIC_INSPECTION": ("acoustic_valve_01.jpg", None),
    "VISUAL_INSPECTION": ("visual_pump_motor_01.jpg", "visual"),
}

# Plain-language meaning of System 1 answers (amd/system1/triage/questions.py criteria), for gateway-fetched rows.
MEANINGS = {
    "escalate": {"A": "yes, escalate: it needs operator attention", "B": "no, log only: it is routine"},
    "reading_trust": {"A": "yes, the reading can be trusted", "B": "no, the reading should not be trusted",
                      "C": "no reading was reported"},
    "mission_misleading": {"A": "yes, the status looks fine but hides problems",
                           "B": "no, the status reflects what happened"},
}


class Deadline:
    """An absolute deadline on the event-loop clock."""

    def __init__(self, seconds: float):
        self.total = seconds
        self.at = asyncio.get_running_loop().time() + seconds

    def remaining(self, reserve: float = 0.0) -> float:
        return max(0.0, self.at - asyncio.get_running_loop().time() - reserve)

    def reserve(self) -> float:
        """Time kept back for finalize (template + response)."""
        return min(3.0, 0.1 * self.total)

    def budget(self, node_budget: float) -> float:
        return min(node_budget, self.remaining(self.reserve()))


@dataclass
class Deps:
    settings: Settings
    mcp: MCPClient
    gateway: GatewayClient
    vision: VisionClient
    system2: System2Client


class AssessState(TypedDict, total=False):
    # request
    flag_id: int
    request_id: Optional[str]
    image_b64: Optional[str]
    image_kind: Optional[str]
    action_type: Optional[str]
    prefetched: Optional[Dict[str, Any]]
    deadline: Deadline
    # nodes
    packet: Optional[Dict[str, Any]]
    context_source: str
    context_error: Optional[str]
    system1: Optional[Dict[str, Any]]
    route: str
    route_reasons: List[str]
    vision: Optional[Dict[str, Any]]
    s2_image: Optional[str]
    system2_raw: Optional[Dict[str, Any]]
    system2_error: Optional[str]
    result: Dict[str, Any]
    trace: Annotated[List[Dict[str, Any]], operator.add]


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _step(node: str, t0: float, status: str, detail: str = "") -> Dict[str, Any]:
    return {"trace": [{"node": node, "ms": _ms(t0), "status": status, "detail": detail[:300]}]}


def _finite(v: Any) -> Optional[float]:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v if math.isfinite(v) else None


def _int(v: Any) -> Optional[int]:
    f = _finite(v)
    return int(round(f)) if f is not None else None


def _strip(identifier: Any, prefix: str) -> Optional[str]:
    if not isinstance(identifier, str) or not identifier:
        return None
    return identifier[len(prefix):] if identifier.startswith(prefix) else identifier


def _compact(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None and v != "" and v != []}


# ── System 1 ─────────────────────────────────────────────────────────────────────────────────────
def canonical_event(packet: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """(kind, canonical event) rebuilt from the MCP packet (amd/system1/triage/events.py shapes), or None when the
    packet lacks a field Laya needs. Best effort: System 1 rejects (422) anything malformed, which is tolerated."""
    ev = packet.get("event") or {}
    m = ev.get("mission")
    if isinstance(m, dict):
        ft = m.get("failure_types")
        out = {
            "kind": "mission", "source": "orchestrator", "mission_id": _strip(m.get("id"), "mission:"),
            "configuration_version": m.get("configuration_version"), "timestamp": m.get("end_time"),
            "reported_status": m.get("reported_status"), "duration_min": _int(m.get("duration_min")),
            "start_battery_pct": _int(m.get("start_battery_pct")), "end_battery_pct": _int(m.get("end_battery_pct")),
            "actions_total": _int(m.get("actions_total")), "actions_failed": _int(m.get("actions_failed")),
            "failure_types": sorted(ft) if isinstance(ft, (dict, list)) else [],
            "anomalies_by_severity": m.get("anomalies_by_severity"),
        }
        if any(out[k] is None for k in out):
            return None
        out["timestamp"] = str(out["timestamp"])
        out["event_id"] = "mis-%s" % out["mission_id"]
        w = m.get("worst_anomaly")
        if isinstance(w, dict):
            # Laya's state needs the worst anomaly's asset name and criticality, which the packet's mission view
            # does not carry; dropping the anomaly would misinform Laya, so no canonical event (System 1 skipped).
            if not (w.get("asset_name") and w.get("asset_criticality")):
                return None
            out["worst_anomaly"] = {k: w.get(k) for k in ("anomaly_type", "severity", "asset_name",
                                                          "asset_criticality")}
        else:
            out["worst_anomaly"] = None
        return "mission", out
    if not str(ev.get("id") or "").startswith("action:"):
        return None
    loc, asset = ev.get("location") or {}, ev.get("asset") or {}
    out = {
        "kind": "action", "source": "orchestrator", "action_id": _strip(ev.get("id"), "action:"),
        "mission_id": ev.get("mission_id"), "configuration_version": ev.get("configuration_version"),
        "timestamp": str(ev["timestamp"]) if ev.get("timestamp") is not None else None,
        "sequence": _int(ev.get("sequence")), "action_type": ev.get("action_type"), "status": ev.get("status"),
        "battery_pct": _int(ev.get("battery_pct")),
        "location": {"location_id": _strip(loc.get("id"), "location:"), "location_name": loc.get("name"),
                     "zone_type": loc.get("zone"), "environment": loc.get("environment")},
        "asset": {"asset_id": _strip(asset.get("id"), "asset:"), "asset_name": asset.get("name"),
                  "asset_type": asset.get("type"), "criticality": asset.get("criticality")},
    }
    if any(v is None for v in out.values()) or any(v is None for v in out["location"].values()) \
            or any(v is None for v in out["asset"].values()) or out["status"] not in ("SUCCESS", "FAILED"):
        return None
    out["event_id"] = "act-%s" % out["action_id"]
    out["failure_type"] = ev.get("failure_type")
    out["duration_sec"] = _int(ev.get("duration_sec"))
    rd = (ev.get("readings") or [None])[0]
    out["reading"] = ({"measurement_type": rd["measurement_type"], "value": rd["value"], "unit": rd.get("unit") or "",
                       "quality": rd.get("quality") or "GOOD"}
                      if isinstance(rd, dict) and rd.get("measurement_type") and _finite(rd.get("value")) is not None
                      else None)
    an = (ev.get("anomalies") or [None])[0]
    out["anomaly"] = ({"anomaly_type": an["anomaly_type"], "severity": an["severity"],
                       "description": an.get("description") or ""}
                      if isinstance(an, dict) and an.get("anomaly_type") and an.get("severity") else None)
    return "action", out


def system1_rows(kind: str, answers: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gateway /v1/predict answers -> the MCP packet's system1 row shape (citable ids s1:live-<kind>-<q>)."""
    rows = []
    for q, a in answers.items():
        if not isinstance(a, dict) or not isinstance(a.get("answer"), str):
            continue
        p = _finite(a.get("confidence"))
        if p is None and isinstance(a.get("probs"), dict):
            p = _finite(a["probs"].get(a["answer"]))
        rows.append(_compact({"id": "s1:live-%s-%s" % (kind, q), "when": kind, "q": q, "answer": a["answer"],
                              "meaning": MEANINGS.get(q, {}).get(a["answer"]), "p": p}))
    return rows


# ── routing ──────────────────────────────────────────────────────────────────────────────────────
def route_reasons(packet: Dict[str, Any], answers: List[Dict[str, Any]], operator_image: bool) -> List[str]:
    """The System 1 -> System 2 routing rule (contract "Routing rule"). Non-empty -> full path."""
    out: List[str] = []
    latest: Dict[str, Dict[str, Any]] = {}
    for a in answers:
        if a.get("when") in ("action", "mission") and a.get("q"):
            latest[a["q"]] = a
    if (latest.get("escalate") or {}).get("answer") == "A":
        out.append("laya_escalate")
    if (latest.get("priority") or {}).get("answer") in ("P1", "P2"):
        out.append("laya_priority")
    flag = packet.get("flag") or {}
    if flag.get("escalated") is True:
        out.append("flag_escalated")
    if flag.get("priority") in ("P1", "P2"):
        out.append("flag_priority")
    v = validator_of(packet)
    if v.get("escalate") == "A" or v.get("priority") in ("P1", "P2"):
        out.append("validator")
    if any(r.get("rule") and r.get("rule") not in VERDICT_RULES for r in reasons(flag)):
        out.append("rules_fired")
    if operator_image:
        out.append("operator_image")
    return out


# ── vision ───────────────────────────────────────────────────────────────────────────────────────
def clean_b64(raw: str) -> str:
    """Strip a data: URL prefix and whitespace; ValueError if the rest is not base64."""
    text = DATA_URL.sub("", raw.strip(), count=1)
    text = "".join(text.split())
    try:
        if not base64.b64decode(text, validate=True):
            raise ValueError("image_b64 is empty")
    except (binascii.Error, ValueError) as exc:
        raise ValueError("image_b64 is not valid base64") from exc
    return text


def system2_image(b64: Optional[str]) -> Tuple[Optional[str], str]:
    """(image for System 2, note): only a JPEG/PNG of at most 2 MiB is sent, else None (System 2 would 422)."""
    if not b64:
        return None, "no image"
    try:
        data = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        return None, "image not base64; not sent to System 2"
    if len(data) > S2_MAX_IMAGE_BYTES:
        return None, "image over 2 MiB; not sent to System 2"
    if not (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n")):
        return None, "image not JPEG/PNG; not sent to System 2"
    return b64, "image sent"


def demo_image(action_type: Optional[str], folder: str) -> Optional[Tuple[str, Optional[str], str]]:
    """(base64, vision kind, media id) of the kit sample for this action type, or None."""
    entry = DEMO_IMAGES.get(action_type or "")
    if not entry:
        return None
    path = Path(folder) / entry[0]
    try:
        data = path.read_bytes()
    except OSError:
        log.warning("demo image %s not readable", path)
        return None
    return base64.b64encode(data).decode("ascii"), entry[1], path.stem


def logged_reading(packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The packet's first reading as the vision service's `logged` block (plus its packet id)."""
    rd = ((packet.get("event") or {}).get("readings") or [None])[0]
    if not isinstance(rd, dict) or _finite(rd.get("value")) is None or not rd.get("measurement_type"):
        return None
    return {"packet_id": rd.get("id"), "reading_id": _strip(rd.get("id"), "reading:"),
            "measurement_type": rd["measurement_type"], "value": rd["value"], "unit": rd.get("unit")}


def _flags(*lists: Any) -> List[str]:
    out: List[str] = []
    for lst in lists:
        for f in lst if isinstance(lst, list) else []:
            if isinstance(f, str) and FLAG_TOKEN.match(f) and f not in out:
                out.append(f)
    return out[:MAX_ROW_FLAGS]


def vision_rows(resp: Dict[str, Any], pairing: str, trust_min: float,
                logged_id: Optional[str]) -> List[Dict[str, Any]]:
    """Vision readings -> V# rows for System 2.

    trust HIGH iff confidence >= trust_min and no AMBIGUOUS_NEEDLE/DEFAULT_SWEEP flag; reading flags (plus the
    comparison's on the compared reading) are forwarded, CLIPPED adds bound=lower; the comparison is attached to its
    reading for linked images only (a demo image is never compared with this asset's log)."""
    kind = resp.get("kind") if isinstance(resp.get("kind"), str) else None
    comp = resp.get("comparison") if isinstance(resp.get("comparison"), dict) and pairing != "demo" else None
    readings = [r for r in resp.get("readings") or [] if isinstance(r, dict)][:MAX_VISION_ROWS]
    ids = []
    for i, r in enumerate(readings):
        rid = r.get("id") if isinstance(r.get("id"), str) and V_ID.match(r["id"]) else "V%d" % (i + 1)
        ids.append(rid if rid not in ids else "V%d" % (i + 1))
    target = None
    if comp:
        target = comp.get("vision_id") if comp.get("vision_id") in ids else (ids[0] if ids else None)
    rows = []
    for rid, r in zip(ids, readings):
        conf = _finite(r.get("confidence"))
        conf = min(1.0, max(0.0, float(conf))) if conf is not None else None
        flags = _flags(r.get("flags"), comp.get("flags") if comp and rid == target else None)
        high = conf is not None and conf >= trust_min and not FORCE_LOW_FLAGS & set(flags)
        row: Dict[str, Any] = {
            "id": rid, "tool": str(r.get("method") or "vision")[:64], "kind": kind,
            "quantity": str(r["quantity"])[:64] if r.get("quantity") is not None else None,
            "value": _finite(r.get("value")), "unit": str(r["unit"])[:64] if r.get("unit") else None,
            "confidence": conf, "trust": "HIGH" if high else "LOW", "flags": flags,
            "bound": "lower" if "CLIPPED" in flags else None, "pairing": pairing,
        }
        if comp and rid == target:
            row["logged_id"] = logged_id or (str(comp["logged_id"]) if comp.get("logged_id") else None)
            row["logged_value"] = _finite(comp.get("logged_value"))
            row["delta"] = _finite(comp.get("delta"))
            row["agrees"] = comp.get("agrees") if isinstance(comp.get("agrees"), bool) else None
        rows.append(_compact(row))
    return rows


def ocr_lines(resp: Dict[str, Any], top_n: int) -> List[Dict[str, Any]]:
    lines = []
    for o in resp.get("ocr") or []:
        if isinstance(o, dict) and isinstance(o.get("text"), str) and o["text"].strip():
            conf = _finite(o.get("conf"))
            lines.append({"text": o["text"].strip()[:80], "conf": min(1.0, max(0.0, float(conf))) if conf is not None
                          else None})
    lines.sort(key=lambda x: -(x["conf"] or 0.0))
    return lines[:max(0, top_n)]


# ── graph ────────────────────────────────────────────────────────────────────────────────────────
def build_assess_graph(deps: Deps):
    s = deps.settings

    async def load_context(state: AssessState) -> Dict[str, Any]:
        t0 = time.perf_counter()
        if isinstance(state.get("prefetched"), dict):
            p = copy.deepcopy(state["prefetched"])
            return {"packet": p, "context_source": "request",
                    **_step("load_context", t0, "ok", "caller-supplied packet")}
        dl: Deadline = state["deadline"]
        budget = min(dl.budget(s.context_budget_s), CONTEXT_SHARE * dl.total)
        if budget < MIN_NODE_S:
            return {"packet": None, "context_source": "none", "context_error": "deadline: no time for MCP",
                    **_step("load_context", t0, "skipped", "deadline")}
        try:
            p = await asyncio.wait_for(deps.mcp.call_tool("get_flag_context", {"flag_id": state["flag_id"]},
                                                          request_id=state.get("request_id")), budget)
        except ServiceUnavailable as exc:
            return {"packet": None, "context_source": "none", "context_error": "MCP unavailable: %s" % exc.reason,
                    **_step("load_context", t0, "error", exc.reason)}
        except asyncio.TimeoutError:
            why = "deadline: MCP did not answer within %.1fs" % budget
            return {"packet": None, "context_source": "none", "context_error": why,
                    **_step("load_context", t0, "timeout", why)}
        p.pop("_latency_ms", None)
        return {"packet": p, "context_source": "mcp",
                **_step("load_context", t0, "ok", "mcp packet, %d citation ids" % len(p.get("citation_ids") or []))}

    async def system1(state: AssessState) -> Dict[str, Any]:
        t0 = time.perf_counter()
        packet = state.get("packet")
        if not packet:
            return {"system1": None, **_step("system1", t0, "skipped", "no context packet")}
        rows = [a for a in packet.get("system1") or [] if isinstance(a, dict)]
        if any(a.get("when") in ("action", "mission") for a in rows):
            return {"system1": {"source": "packet", "model": None, "answers": rows, "live": []},
                    **_step("system1", t0, "ok", "%d answers from the packet" % len(rows))}
        ce = canonical_event(packet)
        if ce is None:
            return {"system1": {"source": "none", "model": None, "answers": rows, "live": []},
                    **_step("system1", t0, "skipped", "packet has no Laya answers and no complete event")}
        if not deps.gateway.configured:
            return {"system1": {"source": "none", "model": None, "answers": rows, "live": []},
                    **_step("system1", t0, "skipped", "GATEWAY_URL is not set")}
        budget = state["deadline"].budget(s.system1_budget_s)
        if budget < MIN_NODE_S:
            return {"system1": {"source": "none", "model": None, "answers": rows, "live": []},
                    **_step("system1", t0, "skipped", "deadline")}
        kind, event = ce
        try:
            out = await asyncio.wait_for(deps.gateway.system1_predict(kind, event, state.get("request_id"), budget),
                                         budget)
        except ServiceUnavailable as exc:
            return {"system1": {"source": "none", "model": None, "answers": rows, "live": [], "error": exc.reason},
                    **_step("system1", t0, "error", exc.reason)}
        except asyncio.TimeoutError:
            return {"system1": {"source": "none", "model": None, "answers": rows, "live": [], "error": "timeout"},
                    **_step("system1", t0, "timeout", "gateway system1 did not answer within %.1fs" % budget)}
        live = system1_rows(kind, out["answers"])
        return {"system1": {"source": "gateway", "model": out.get("model"), "answers": rows + live, "live": live},
                **_step("system1", t0, "ok", "%d live %s answers via gateway" % (len(live), kind))}

    async def route(state: AssessState) -> Dict[str, Any]:
        t0 = time.perf_counter()
        packet = state.get("packet")
        if not packet:
            return {"route": "no_context", "route_reasons": [], **_step("route", t0, "ok", "no_context")}
        answers = (state.get("system1") or {}).get("answers") or []
        why = route_reasons(packet, answers, bool(state.get("image_b64")))
        r = "full" if why else "system1_only"
        return {"route": r, "route_reasons": why,
                **_step("route", t0, "ok", "%s (%s)" % (r, ", ".join(why) or "no escalation signal"))}

    async def vision(state: AssessState) -> Dict[str, Any]:
        t0 = time.perf_counter()
        packet = state.get("packet") or {}
        action_type = state.get("action_type") or (packet.get("event") or {}).get("action_type")
        image, kind, media_id, pairing = state.get("image_b64"), state.get("image_kind"), None, "linked"
        if not image and s.demo_images:
            demo = demo_image(action_type, s.demo_images_dir)
            if demo:
                image, demo_kind, media_id = demo
                kind, pairing = kind or demo_kind, "demo"
        if not image:
            return {"vision": None, "s2_image": None, **_step("vision", t0, "skipped", "no image")}
        original, note = system2_image(image)
        if not deps.vision.configured:
            return {"vision": None, "s2_image": original,
                    **_step("vision", t0, "skipped", "VISION_URL is not set; original image -> System 2 (%s)" % note)}
        dl: Deadline = state["deadline"]
        budget = dl.budget(s.vision_budget_s)
        if deps.system2.configured:     # keep System 2's image budget (contract "Timeout chain"), vision >= 3 s
            budget = min(budget, max(VISION_FLOOR_S, dl.remaining(dl.reserve()) - s.system2_image_budget_s))
        if budget < MIN_NODE_S:
            return {"vision": None, "s2_image": original, **_step("vision", t0, "skipped", "deadline")}
        # A demo image is a kit sample picked by action type, not a reading of this asset: never send `logged`, so
        # the vision service makes no comparison (no agrees=false, no vision.compare alert) for it.
        logged = logged_reading(packet) if pairing == "linked" else None
        body = _compact({"request_id": state.get("request_id"), "media_id": media_id, "kind": kind or "auto",
                         "action_type": action_type, "image_b64": image, "annotate": True,
                         "logged": {k: v for k, v in (logged or {}).items() if k != "packet_id"} or None})
        try:
            resp = await asyncio.wait_for(deps.vision.analyze(body, state.get("request_id"), budget), budget)
        except ServiceUnavailable as exc:
            return {"vision": None, "s2_image": original,
                    **_step("vision", t0, "error", "%s; original image -> System 2" % exc.reason)}
        except asyncio.TimeoutError:
            return {"vision": None, "s2_image": original,
                    **_step("vision", t0, "timeout", "vision did not answer within %.1fs" % budget)}
        rows = vision_rows(resp, pairing, s.vision_trust_min, (logged or {}).get("packet_id"))
        annotated = resp.get("annotated_image_b64") if isinstance(resp.get("annotated_image_b64"), str) else None
        s2_img, note = system2_image(annotated) if annotated else (original, note)
        if annotated and s2_img is None:
            s2_img, note = original, "annotated image unusable; original sent"
        alert = resp.get("alert") if isinstance(resp.get("alert"), dict) else None
        demo = pairing == "demo"
        v = {"pairing": pairing, "kind": resp.get("kind"), "router": resp.get("router"), "rows": rows,
             "ocr": ocr_lines(resp, s.ocr_top_n), "key_results": resp.get("key_results") or [],
             # a demo image's alert describes the sample image, not this asset: shown as demo_alert only
             "alert": None if demo else alert, "comparison": None if demo else resp.get("comparison"),
             "latency_ms": resp.get("latency_ms"), "version": resp.get("version"),
             "media_id": media_id or resp.get("media_id"), "annotated_image_b64": annotated}
        if demo:
            v["demo_alert"] = alert
        return {"vision": v, "s2_image": s2_img,
                **_step("vision", t0, "ok", "%s %s: %d rows (%d HIGH), %d OCR lines; %s" % (
                    pairing, resp.get("kind"), len(rows), sum(r.get("trust") == "HIGH" for r in rows),
                    len(v["ocr"]), "annotated image" if annotated else note))}

    async def system2(state: AssessState) -> Dict[str, Any]:
        t0 = time.perf_counter()
        if not deps.system2.configured:
            return {"system2_raw": None, "system2_error": "SYSTEM2_URL is not set",
                    **_step("system2", t0, "skipped", "SYSTEM2_URL is not set")}
        # an image makes System 2 use its longer SYSTEM2_IMAGE_DEADLINE_S, so the node gets the image budget
        budget = state["deadline"].budget(s.system2_image_budget_s if state.get("s2_image") else s.system2_budget_s)
        if budget < MIN_NODE_S:
            why = "deadline: no time left for System 2"
            return {"system2_raw": None, "system2_error": why, **_step("system2", t0, "skipped", why)}
        packet = state.get("packet") or {}
        ctx = copy.deepcopy(packet)
        ctx.pop("vision", None)      # only rows the vision service produced in this request are citable
        ctx.pop("ocr", None)
        s1 = state.get("system1") or {}
        if s1.get("live"):
            ctx["system1"] = list(ctx.get("system1") or []) + s1["live"]
        v = state.get("vision") or {}
        if v.get("rows"):
            ctx["vision"] = v["rows"]
        if v.get("ocr"):
            ctx["ocr"] = v["ocr"]
        flag = packet.get("flag") or {"id": "flag:%s" % state["flag_id"]}
        body: Dict[str, Any] = {
            "flag_id": state["flag_id"], "request_id": state.get("request_id"), "flag": flag, "event": None,
            "reasons": [r.get("detail") if isinstance(r.get("detail"), str) else None for r in reasons(flag)],
            "context": ctx}
        if state.get("s2_image"):
            body["image_b64"] = state["s2_image"]
        try:
            out = await asyncio.wait_for(deps.system2.assess(body, state.get("request_id"), budget), budget)
        except ServiceUnavailable as exc:
            return {"system2_raw": None, "system2_error": exc.reason, **_step("system2", t0, "error", exc.reason)}
        except asyncio.TimeoutError:
            why = "deadline: System 2 did not answer within %.1fs (ORCH_DEADLINE_S=%gs)" % (budget,
                                                                                           state["deadline"].total)
            return {"system2_raw": None, "system2_error": why, **_step("system2", t0, "timeout", why)}
        problem = system2_problem(out)
        if problem:
            return {"system2_raw": out, "system2_error": "invalid System 2 response: %s" % problem,
                    **_step("system2", t0, "error", problem)}
        return {"system2_raw": out, "system2_error": None,
                **_step("system2", t0, "ok", "path %s, model %s%s" % (out.get("path"), out.get("model"),
                                                                       ", with image" if "image_b64" in body else ""))}

    async def system1_only(state: AssessState) -> Dict[str, Any]:
        t0 = time.perf_counter()
        s1 = state.get("system1") or {}
        res = system1_answer(state.get("packet") or {}, state["flag_id"], s1.get("answers") or [], s1.get("model"),
                             "no escalation signal from System 1, the flag, the validator or the policy rules")
        res["fallback_reason"] = None
        return {"result": res, **_step("system1_only", t0, "ok", "short System 1 answer; System 2 not called")}

    async def finalize(state: AssessState) -> Dict[str, Any]:
        t0 = time.perf_counter()
        packet = state.get("packet") or {}
        fid = state["flag_id"]
        answers = (state.get("system1") or {}).get("answers") or []
        rows = (state.get("vision") or {}).get("rows") or []
        if state.get("route") == "no_context":
            res = template_answer({}, fid)
            res["fallback_reason"] = state.get("context_error") or "no context packet"
            status = "fallback"
        elif state.get("system2_raw") is not None and not state.get("system2_error"):
            raw = state["system2_raw"]
            res = normalize_system2(raw)
            res["fallback_reason"] = None
            status = "ok"
            if raw.get("path") in SYSTEM2_TEMPLATE_PATHS or raw.get("model") == "template":
                # System 2 answered with its own checked template, not a model answer: say so (backend: template)
                res["source"] = "system2_template"
                res["fallback_reason"] = "System 2 answered with its checked template (path %s, model %s)" % (
                    raw.get("path"), raw.get("model"))
                status = "fallback"
        else:
            res = template_answer(packet, fid, answers, rows)
            res["fallback_reason"] = state.get("system2_error") or "System 2 was not called"
            status = "fallback"
        return {"result": res, **_step("finalize", t0, status, "source %s" % res["source"])}

    g = StateGraph(AssessState)
    for name, fn in (("load_context", load_context), ("system1", system1), ("route", route), ("vision", vision),
                     ("system2", system2), ("system1_only", system1_only), ("finalize", finalize)):
        g.add_node(name, fn)
    g.add_edge(START, "load_context")
    g.add_edge("load_context", "system1")
    g.add_edge("system1", "route")
    g.add_conditional_edges("route", lambda st: st.get("route") or "no_context",
                            {"full": "vision", "system1_only": "system1_only", "no_context": "finalize"})
    g.add_edge("vision", "system2")
    g.add_edge("system2", "finalize")
    g.add_edge("system1_only", END)
    g.add_edge("finalize", END)
    return g.compile()


async def run_assess(graph, deps: Deps, req: Dict[str, Any]) -> Dict[str, Any]:
    """Run the graph within the global deadline and shape the response (contract "Response")."""
    s = deps.settings
    t0 = time.perf_counter()
    deadline = Deadline(s.deadline_s)
    state: AssessState = {"flag_id": req["flag_id"], "request_id": req.get("request_id"),
                          "image_b64": req.get("image_b64"), "image_kind": req.get("image_kind"),
                          "action_type": req.get("action_type"), "prefetched": req.get("context"),
                          "deadline": deadline, "trace": []}
    try:
        # Safety net only: every node is already bounded by the deadline.
        out = await asyncio.wait_for(graph.ainvoke(state), s.deadline_s + 2.0)
    except asyncio.TimeoutError:
        out = {"route": "no_context", "trace": [{"node": "graph", "ms": _ms(t0), "status": "timeout",
                                                 "detail": "graph did not finish within the deadline"}],
               "result": {**template_answer({}, req["flag_id"]),
                          "fallback_reason": "deadline: graph did not finish within %gs" % s.deadline_s},
               "context_source": "none"}
    vis = out.get("vision")
    if vis is not None and not req.get("return_image"):
        vis = {k: v for k, v in vis.items() if k != "annotated_image_b64"}
    s1 = out.get("system1")
    if s1 is not None:
        s1 = {k: v for k, v in s1.items() if k != "live"}
    return {
        "flag_id": req["flag_id"], "request_id": req.get("request_id"), "route": out.get("route"),
        "route_reasons": out.get("route_reasons") or [], **out["result"],
        "system2": out.get("system2_raw"), "system1": s1, "vision": vis,
        "context_source": out.get("context_source", "none"), "graph": "assess", "contract_version": CONTRACT_VERSION,
        "deadline_s": s.deadline_s, "elapsed_ms": _ms(t0), "trace": out.get("trace") or [],
    }
