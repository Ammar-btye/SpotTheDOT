"""Flag workflows: context packet (MCP, else SQL), explanation (System 2, else template), operator ack.

Fallbacks (the demo path never 500s):
- MCP down          -> /context returns a SQL-built minimal packet (`source: "sql_fallback"`).
- SYSTEM2 unset/down -> /explain returns a templated Orbit-style explanation (`source: "template"`).
- embed down         -> the ack is stored; the operator_note RAG document is skipped (`rag_indexed: false`).
- Request deadline (REQUEST_DEADLINE_S, audit M4): /context and /explain each finish within it, whatever the
  per-call timeouts; past it they return the same fallbacks, with `fallback_reason: "deadline: ..."`.
- Template explanations are stored with state TEMPLATE (audit M10): not final, so /explain retries System 2 when
  SYSTEM2_URL is set, and they are never indexed as `explanation` RAG docs.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import psycopg

from ..db.pool import DatabaseUnavailable
from .embed import vec_literal
from .http import ServiceUnavailable, short_error
from .system2 import normalize_assessment, template_explanation
from .triage import T_policy as P

log = logging.getLogger("backend.flags")


class FlagNotFound(LookupError):
    pass


class RequestDeadlineExceeded(TimeoutError):
    """The flag row itself could not be read within REQUEST_DEADLINE_S (main.py -> 504)."""


EXPLAIN_CONTEXT_SHARE = 0.4      # /explain: the context step gets at most this share of the deadline
STATE_SYSTEM2, STATE_TEMPLATE = "DONE", "TEMPLATE"


class _Deadline:
    """An absolute deadline on the event loop clock."""

    def __init__(self, seconds: float):
        self.total = seconds
        self.at = asyncio.get_running_loop().time() + seconds

    def remaining(self, reserve: float = 0.0) -> float:
        return max(0.0, self.at - asyncio.get_running_loop().time() - reserve)

    def reserve(self) -> float:
        """Time kept back for building and storing the fallback."""
        return min(3.0, 0.1 * self.total)


def _compact(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v not in (None, [], {}, "")}


def battery_band(pct: Optional[float]) -> Optional[str]:
    if pct is None:
        return None
    return "<=25" if pct <= 25 else "26-40" if pct <= 40 else "41-60" if pct <= 60 else "61-80" if pct <= 80 else "81+"


def band_check(r: Dict[str, Any], status: Optional[str]) -> Dict[str, Any]:
    mt, v = r.get("measurement_type"), r.get("value")
    lo, hi = P.SAFE_BANDS.get(mt, (None, None))
    if v is None:
        return {"trust": "none", "safe_band": [lo, hi]}
    plo, phi = P.PLAUSIBLE.get(mt, (float("-inf"), float("inf")))
    if r.get("quality") != "GOOD" or status == "FAILED" or not (plo <= v <= phi):
        return {"trust": "untrusted", "safe_band": [lo, hi]}
    out = (lo is not None and v < lo) or (hi is not None and v > hi)
    return {"trust": "trusted", "in_safe_band": not out, "safe_band": [lo, hi]}


class FlagService:
    def __init__(self, repo, mcp, system2, embed, sink, deadline_s: float = 45.0):
        self.repo = repo
        self.mcp = mcp
        self.system2 = system2
        self.embed = embed
        self.sink = sink
        self.deadline_s = deadline_s

    async def load(self, flag_id: int, deadline: Optional[_Deadline] = None) -> Dict[str, Any]:
        if deadline is None:
            row = await self.repo.get_flag(flag_id)
        else:
            try:
                row = await asyncio.wait_for(self.repo.get_flag(flag_id), deadline.remaining())
            except asyncio.TimeoutError:
                raise RequestDeadlineExceeded("flag %s could not be read within REQUEST_DEADLINE_S=%gs"
                                              % (flag_id, deadline.total)) from None
        if row is None:
            raise FlagNotFound(flag_id)
        return row

    # ── context ─────────────────────────────────────────────────────────────────────────────────
    async def context(self, flag_id: int, request_id: Optional[str]) -> Dict[str, Any]:
        deadline = _Deadline(self.deadline_s)
        row = await self.load(flag_id, deadline)
        return await self._context(row, flag_id, request_id, deadline, deadline.remaining(deadline.reserve()))

    async def _context(self, row: Dict[str, Any], flag_id: int, request_id: Optional[str], deadline: _Deadline,
                       mcp_budget_s: float) -> Dict[str, Any]:
        """MCP packet within `mcp_budget_s`, else the SQL packet within what is left of `deadline`."""
        try:
            packet = await asyncio.wait_for(
                self.mcp.call_tool("get_flag_context", {"flag_id": flag_id}, request_id=request_id), mcp_budget_s)
            packet["source"] = "mcp"
            return packet
        except ServiceUnavailable as exc:
            gap = "MCP unavailable (%s): SQL-only packet, no RAG retrieval" % exc.reason
            reason = None
        except asyncio.TimeoutError:
            reason = "deadline: MCP did not answer within %.1fs (REQUEST_DEADLINE_S=%gs)" % (mcp_budget_s,
                                                                                              deadline.total)
            gap = reason + ": SQL-only packet, no RAG retrieval"
        packet = await self.minimal_packet(row, budget_s=max(0.5, deadline.remaining()))
        packet.setdefault("gaps", []).insert(0, gap)
        if reason:
            packet["fallback_reason"] = reason
        return packet

    async def minimal_packet(self, row: Dict[str, Any], budget_s: Optional[float] = None) -> Dict[str, Any]:
        """The SQL-built fallback packet: flag, event facts, System 1 answers, reliability, asset history.
        With `budget_s`, SQL lookups not finished in time are skipped and listed in `gaps`."""
        f = row["flag"]
        gaps: List[str] = []
        packet: Dict[str, Any] = {"packet_version": "1-min", "source": "sql_fallback"}
        reasons = [r for r in (f.get("reasons") or []) if isinstance(r, dict)]
        packet["flag"] = _compact({
            "id": "flag:%s" % f["flag_id"], "title": f.get("title"), "severity": f.get("severity"),
            "score": f.get("score"), "status": f.get("status"), "escalated": f.get("escalated"),
            "priority": f.get("priority"), "category": f.get("category"), "mission_id": f.get("mission_id"),
            "action_id": f.get("action_id"), "asset_id": f.get("asset_id"), "location_id": f.get("location_id"),
            "created_at": f.get("created_at"),
            "reasons": [_compact({"rule": r.get("rule"), "detail": r.get("detail")}) for r in reasons[:8]]})
        acks = row.get("acks") or []
        if acks:
            packet["flag"]["operator_acks"] = [_compact({"id": "note:%s" % k.get("ack_id"), "action": k.get("action"),
                                                         "note": k.get("note"), "operator": k.get("operator")})
                                               for k in acks[:5]]
        facts: List[str] = []
        action_id, mission_id = f.get("action_id"), f.get("mission_id")
        try:
            await asyncio.wait_for(self._sql_lookups(packet, f, facts, gaps), budget_s)
        except asyncio.TimeoutError:
            gaps.append("some SQL lookups did not finish within the request deadline")
        for r in reasons:
            if r.get("rule") not in ("laya_verdict", "rules_verdict", "laya_unavailable") and r.get("detail"):
                facts.insert(0, r["detail"])
        packet["facts"] = [{"id": "F%d" % (i + 1), "text": t} for i, t in enumerate(facts[:8])]
        packet["insufficient_context"] = "event" not in packet
        if gaps:
            packet["gaps"] = gaps
        if action_id:
            q = "Does %s need operator attention now, and what should the operator do?" % (
                ((packet.get("event") or {}).get("asset") or {}).get("name") or f.get("asset_id") or "this asset")
        else:
            q = "Did mission %s really complete cleanly, and what should the operator review?" % mission_id
        packet["question"] = q
        return packet

    async def _sql_lookups(self, packet: Dict[str, Any], f: Dict[str, Any], facts: List[str],
                           gaps: List[str]) -> None:
        """The SQL part of the fallback packet; fills `packet`, `facts` and `gaps` in place."""
        action_id, mission_id = f.get("action_id"), f.get("mission_id")
        try:
            if action_id:
                b = await self.repo.action_bundle(action_id)
                if b:
                    a, s, l = b["action"], b.get("asset") or {}, b.get("location") or {}
                    readings = [_compact({"id": "reading:%s" % r.get("reading_id"), "measurement_type":
                                          r.get("measurement_type"), "value": r.get("value"), "unit": r.get("unit"),
                                          "quality": r.get("quality"), **band_check(r, a.get("status"))})
                                for r in (b.get("readings") or [])[:3]]
                    anomalies = [_compact({"id": "anomaly:%s" % n.get("anomaly_id"), "anomaly_type":
                                           n.get("anomaly_type"), "severity": n.get("severity"),
                                           "description": n.get("description")}) for n in (b.get("anomalies") or [])[:3]]
                    packet["event"] = _compact({
                        "id": "action:%s" % action_id, "mission_id": a.get("mission_id"), "sequence": a.get("sequence"),
                        "timestamp": a.get("timestamp"), "action_type": a.get("action_type"), "status": a.get("status"),
                        "failure_type": a.get("failure_type"), "battery_pct": a.get("battery_pct"),
                        "configuration_version": a.get("configuration_version"),
                        "asset": _compact({"id": "asset:%s" % s.get("asset_id"), "name": s.get("asset_name"),
                                           "type": s.get("asset_type"), "criticality": s.get("criticality")}),
                        "location": _compact({"id": "location:%s" % l.get("location_id"), "name": l.get("location_name"),
                                              "zone": l.get("zone_type"), "environment": l.get("environment")}),
                        "readings": readings, "anomalies": anomalies})
                    rel = await self.repo.reliability(None, {"location_id": a.get("location_id"),
                                                             "action_type": a.get("action_type")})
                    if rel:
                        r0 = rel[0]
                        packet["reliability"] = {"scope": "%s at %s" % (a.get("action_type"), a.get("location_id")),
                                                 "n": r0["n"], "success_rate_pct": r0["success_rate_pct"],
                                                 "ci95_pct": r0["ci95_pct"]}
                        facts.append("%s at %s succeeds %s%% of the time (n=%d)" % (
                            a.get("action_type"), a.get("location_id"), r0["success_rate_pct"], r0["n"]))
                    band = battery_band(a.get("battery_pct"))
                    if band:
                        rb = await self.repo.reliability(None, {"battery_band": band})
                        if rb:
                            packet["battery_band"] = {"band": band, "n": rb[0]["n"],
                                                      "success_rate_pct": rb[0]["success_rate_pct"]}
                            facts.append("actions at battery %s succeed %s%% of the time" %
                                         (band, rb[0]["success_rate_pct"]))
                else:
                    gaps.append("action %s not found" % action_id)
            elif mission_id:
                m = await self.repo.mission(mission_id)
                if m:
                    packet["event"] = {"mission": _compact({"id": "mission:%s" % mission_id, **{
                        k: m.get(k) for k in ("mission_name", "configuration_version", "start_time", "end_time",
                                              "start_battery_pct", "end_battery_pct", "mission_status")}})}
                    packet["event"]["mission"]["failure_types"] = await self.repo.failure_type_counts(mission_id)
            if f.get("asset_id"):
                hist = await self.repo.asset_history(f["asset_id"], f["flag_id"])
                if hist.get("anomalies") or hist.get("prior_flags"):
                    packet["asset_history"] = _compact({"anomalies": hist.get("anomalies"),
                                                        "prior_flags": hist.get("prior_flags")})
            preds = await self.repo.predictions(action_id, mission_id)
            seen, s1 = set(), []
            for p in preds:
                key = (p["event_kind"], p["question"])
                if key in seen:
                    continue
                seen.add(key)
                s1.append({"id": "s1:%s" % p["prediction_id"], "when": p["event_kind"], "q": p["question"],
                           "answer": p["answer"], "p": (p.get("probs") or {}).get(p["answer"])})
            if s1:
                packet["system1"] = s1[:8]
        except (DatabaseUnavailable, psycopg.Error) as exc:
            gaps.append("some SQL lookups failed: %s" % short_error(exc))

    # ── explain ─────────────────────────────────────────────────────────────────────────────────
    async def explain(self, flag_id: int, request_id: Optional[str], refresh: bool = False) -> Dict[str, Any]:
        deadline = _Deadline(self.deadline_s)
        row = await self.load(flag_id, deadline)
        cached = row.get("assessment")
        if cached and not refresh:
            # A System 2 explanation (DONE, model not 'template') is final. A template (state TEMPLATE, or a
            # pre-M10 DONE row with model 'template') is reused only while System 2 is not configured.
            is_template = cached.get("state") == STATE_TEMPLATE or cached.get("model") in ("template", None)
            if cached.get("state") in (STATE_SYSTEM2, STATE_TEMPLATE) and not (is_template
                                                                             and self.system2.configured):
                return {**cached, "source": "template" if is_template else "system2", "cached": True}
        f = row["flag"]
        reserve = deadline.reserve()
        ctx_budget = min(deadline.remaining(reserve), EXPLAIN_CONTEXT_SHARE * deadline.total)
        context = await self._context(row, flag_id, request_id, deadline, ctx_budget)
        result: Dict[str, Any]
        s2_budget = deadline.remaining(reserve)
        try:
            body = {"flag_id": flag_id, "request_id": request_id, "flag": f, "event": row.get("event"),
                    "reasons": [r.get("detail") for r in (f.get("reasons") or []) if isinstance(r, dict)],
                    "context": context}
            out = await asyncio.wait_for(
                self.system2.assess(body, request_id=request_id, flag_id=flag_id, action_id=f.get("action_id")),
                s2_budget)
            result = normalize_assessment(out)
            if not result.get("answer"):
                raise ServiceUnavailable("system2", "response had no answer")
        except ServiceUnavailable as exc:
            result = template_explanation(f, row.get("event"), context)
            result["fallback_reason"] = exc.reason
        except asyncio.TimeoutError:
            result = template_explanation(f, row.get("event"), context)
            result["fallback_reason"] = "deadline: System 2 did not answer within %.1fs (REQUEST_DEADLINE_S=%gs)" % (
                s2_budget, deadline.total)
        result["context_source"] = context.get("source")
        state = STATE_SYSTEM2 if result.get("source") == "system2" else STATE_TEMPLATE
        try:
            stored = await asyncio.wait_for(self.repo.upsert_assessment(flag_id, result, state=state),
                                            max(0.5, deadline.remaining()))
            result["assessment_id"] = stored.get("assessment_id")
        except (DatabaseUnavailable, psycopg.Error) as exc:
            result["warning"] = "assessment not stored: %s" % short_error(exc)
        except asyncio.TimeoutError:
            result["warning"] = "assessment not stored: the request deadline passed"
        if result.get("assessment_id") and state == STATE_SYSTEM2:
            self.sink.spawn(self._index_explanation(result, f, request_id))
        result["cached"] = False
        return result

    async def _index_explanation(self, a: Dict[str, Any], f: Dict[str, Any], request_id: Optional[str]) -> None:
        content = "Q: %s A: %s Why: %s Action: %s" % (a.get("question"), a.get("answer"), a.get("reasoning"),
                                                     a.get("recommended_action"))
        await self._upsert_doc({"doc_id": "explanation:%s" % a["assessment_id"], "kind": "explanation",
                                "source_id": str(a["assessment_id"]), "mission_id": f.get("mission_id"),
                                "action_id": f.get("action_id"), "asset_id": f.get("asset_id"),
                                "location_id": f.get("location_id"), "severity": f.get("severity"),
                                "title": f.get("title"), "content": content,
                                "metadata": {"flag_id": f.get("flag_id"), "model": a.get("model")}}, request_id)

    # ── ack ─────────────────────────────────────────────────────────────────────────────────────
    async def ack(self, flag_id: int, action: str, note: Optional[str], operator: str,
                  request_id: Optional[str]) -> Dict[str, Any]:
        row = await self.load(flag_id)
        ack = await self.repo.insert_ack(flag_id, action, note, operator)
        out = {"ack": ack, "flag_status": {"ACKNOWLEDGE": "ACKNOWLEDGED", "RESOLVE": "RESOLVED",
                                           "ESCALATE": "OPEN"}.get(action, row["flag"].get("status")),
               "rag_indexed": False}
        if note and note.strip():
            f = row["flag"]
            doc = {"doc_id": "note:%s" % ack["ack_id"], "kind": "operator_note", "source_id": str(ack["ack_id"]),
                   "mission_id": f.get("mission_id"), "action_id": f.get("action_id"), "asset_id": f.get("asset_id"),
                   "location_id": f.get("location_id"), "severity": f.get("severity"),
                   "status": out["flag_status"], "ts": None,
                   "title": "Operator %s on: %s" % (action.lower(), f.get("title")),
                   "content": "Operator %s %s flag %s (%s, %s). Note: %s" % (
                       operator, {"ACKNOWLEDGE": "acknowledged", "RESOLVE": "resolved", "ESCALATE": "escalated",
                                  "NOTE": "commented on"}.get(action, action.lower()), flag_id, f.get("title"),
                       f.get("severity"), note.strip()),
                   "metadata": {"flag_id": flag_id, "ack_id": ack["ack_id"], "action": action, "operator": operator}}
            out["rag_indexed"], err = await self._upsert_doc(doc, request_id)
            out["doc_id"] = doc["doc_id"] if out["rag_indexed"] else None
            if err:
                out["rag_error"] = err
        else:
            out["rag_error"] = "no note: nothing to index"
        return out

    async def _upsert_doc(self, doc: Dict[str, Any], request_id: Optional[str]) -> tuple[bool, Optional[str]]:
        try:
            vec = (await self.embed.embed_documents([doc["content"]], request_id=request_id))[0]
        except ServiceUnavailable as exc:
            return False, "embedding service unavailable: %s" % exc.reason
        try:
            await self.repo.upsert_document(doc, vec_literal(vec), self.embed.model)
        except (DatabaseUnavailable, psycopg.Error) as exc:
            return False, "document not stored: %s" % short_error(exc)
        return True, None
