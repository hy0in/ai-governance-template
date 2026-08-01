#!/usr/bin/env python3
"""관제실(mission control) 대시보드 — 읽기 전용 로컬 서버.

파이썬 표준 라이브러리만 사용하며 외부 패키지·인터넷 의존이 없다.
runs/current/, runs/incomplete/, manifests/, escalation/을 읽어 JSON API로 제공한다.
저장소에는 어떤 파일도 쓰지 않는다 (읽기 전용).

사용법:
  python3 dashboard/serve.py            # http://127.0.0.1:8765
  python3 dashboard/serve.py --port 9000

경로는 이 파일의 위치 기준(저장소 루트 = dashboard/의 부모)으로만 잡으므로
어디에 클론해도 그대로 동작한다.

집계 규칙 (knowledge/decisions/0002 참조):
- manifests/만 통계 원천이다. runs/incomplete/는 이벤트 로그에만 표시한다.
- run_id 해시 접미사가 같은 매니페스트는 동일 산출물의 중복 기록이므로
  가장 이른 1건만 집계한다 (구형식 오염 기록 대응).
- routing: incomplete인 구형식 매니페스트는 집계에서 제외한다.
"""
import argparse
import datetime
import glob
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DASH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DASH_DIR)

PIPELINE = ("analyst", "independent", "critic", "verifier", "synthesizer")
# .claude/agents/의 서브에이전트 이름 → judgment 파일의 역할명
AGENT_TO_ROLE = {
    "analyst": "analyst",
    "independent-analyst": "independent",
    "critic": "critic",
    "evidence-verifier": "verifier",
    "synthesizer": "synthesizer",
}
RECENT_ACTIVITY_S = 900  # 마지막 활동이 이보다 오래됐으면 '실행 중'으로 보지 않는다


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def safe_mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def parse_run_ts(run_id):
    """run_id의 '2026-08-01T125305Z' 접두사를 unix time으로. 실패 시 None."""
    try:
        dt = datetime.datetime.strptime(run_id.split("_")[0], "%Y-%m-%dT%H%M%SZ")
        return dt.replace(tzinfo=datetime.timezone.utc).timestamp()
    except Exception:
        return None


def build_run(now):
    current = os.path.join(ROOT, "runs", "current")
    roles, mtimes = {}, []
    for role in PIPELINE:
        p = os.path.join(current, f"{role}.judgment.json")
        d = read_json(p)
        if d is None:
            roles[role] = {"state": "pending"}
            continue
        mt = safe_mtime(p)
        if mt:
            mtimes.append(mt)
        roles[role] = {
            "state": "done",
            "verdict": d.get("verdict"),
            "confidence": d.get("confidence"),
            "escalate": bool(d.get("escalate")),
            "escalation_reason": d.get("escalation_reason"),
            "evidence": d.get("evidence", [])[:40],
            "alternative_hypotheses": d.get("alternative_hypotheses", [])[:20],
            "ts": mt,
        }

    status = read_json(os.path.join(current, "status.json")) or {}
    events = [e for e in status.get("events", []) if isinstance(e, dict)]

    # 훅 이벤트 기반 '실행 중' 판정: start만 있고 end가 없는 에이전트
    open_starts = {}
    for ev in events:
        role = AGENT_TO_ROLE.get(ev.get("agent", ""))
        if not role:
            continue
        if ev.get("event") == "agent_start":
            open_starts[role] = ev.get("ts", 0)
        elif ev.get("event") == "agent_end":
            open_starts.pop(role, None)
    for role, ts in open_starts.items():
        if roles[role]["state"] == "pending" and now - ts < RECENT_ACTIVITY_S:
            roles[role]["state"] = "running"

    # 폴백: 훅 이벤트가 없어도 judgment 파일 진행 상황으로 '실행 중'을 추정
    done_roles = [r for r in PIPELINE if roles[r]["state"] == "done"]
    last_activity = max(
        mtimes + [e.get("ts", 0) for e in events] + [0]
    )
    if (done_roles and roles["synthesizer"]["state"] == "pending"
            and not any(roles[r]["state"] == "running" for r in PIPELINE)
            and now - last_activity < RECENT_ACTIVITY_S):
        for r in PIPELINE:
            if roles[r]["state"] == "pending":
                roles[r]["state"] = "running"
                roles[r]["inferred"] = True  # 파일 감지 기반 추정임을 표시
                break

    # 실행 상태
    synth = roles["synthesizer"]
    if synth["state"] == "done":
        run_status = "escalated" if synth.get("escalate") else "confirmed"
    elif any(roles[r]["state"] == "running" for r in PIPELINE):
        run_status = "running"
    elif done_roles:
        run_status = "stale"  # 산출물은 있으나 활동이 끊김
    else:
        run_status = "idle"

    started = min(mtimes + [e.get("ts") for e in events if e.get("ts")] or [0]) or None
    ended = synth.get("ts") if synth["state"] == "done" else None

    marker = read_json(os.path.join(current, ".manifested")) or {}
    return {
        "status": run_status,
        "run_id": marker.get("last_run_id"),
        "started_at": started,
        "ended_at": ended,
        "roles": roles,
        "events": events[-60:],
    }


def build_stats():
    entries = []
    for p in sorted(glob.glob(os.path.join(ROOT, "manifests", "*.json"))):
        d = read_json(p)
        if not isinstance(d, dict):
            continue
        rid = d.get("run_id") or os.path.basename(p)[:-5]
        synth = (d.get("outputs") or {}).get("synthesizer") or {}
        entries.append({
            "run_id": rid,
            "suffix": rid.rsplit("_", 1)[-1],
            "ts": parse_run_ts(rid) or safe_mtime(p),
            "routing": d.get("routing"),
            "verdict": synth.get("verdict"),
            "citations_pass": (d.get("verification") or {}).get("citations_pass"),
            "input_hash": d.get("input_hash"),
            "input_files": [f.get("path") for f in d.get("input_files", [])],
        })

    seen, counted, dup_excluded, incomplete_excluded = set(), [], 0, 0
    for e in entries:  # 파일명 오름차순 = 시간순이므로 첫 등장이 가장 이른 기록
        if e["suffix"] in seen:
            dup_excluded += 1
            continue
        seen.add(e["suffix"])
        if e["routing"] == "incomplete":
            incomplete_excluded += 1
            continue
        counted.append(e)

    n = len(counted)
    auto = sum(1 for e in counted if e["routing"] == "auto_confirmed")
    esc = sum(1 for e in counted if e["routing"] == "escalated")
    cit = sum(1 for e in counted if e["citations_pass"])
    pct = lambda k: round(100.0 * k / n, 1) if n else None
    stats = {
        "total_files": len(entries),
        "counted": n,
        "dup_excluded": dup_excluded,
        "incomplete_excluded": incomplete_excluded,
        "auto_confirm_rate": pct(auto),
        "escalation_rate": pct(esc),
        "citations_pass_rate": pct(cit),
    }
    recent = sorted(counted, key=lambda e: e["ts"] or 0, reverse=True)[:8]
    return stats, counted, recent


def build_escalations():
    docs = []
    for p in sorted(glob.glob(os.path.join(ROOT, "escalation", "*.md"))):
        docs.append({"name": os.path.basename(p), "ts": safe_mtime(p)})
    docs.sort(key=lambda d: d["ts"] or 0, reverse=True)
    return docs


def build_events(run, counted, escalations):
    """콘솔 로그 스트림용 통합 이벤트 목록 (ts 오름차순)."""
    out = []
    for ev in run["events"]:
        role = AGENT_TO_ROLE.get(ev.get("agent", ""), ev.get("agent", "?"))
        kind = "start" if ev.get("event") == "agent_start" else "end"
        out.append({"ts": ev.get("ts"), "level": "info" if kind == "start" else "ok",
                    "text": f"{role.upper()} agent {kind}"})
    for role in PIPELINE:
        r = run["roles"][role]
        if r["state"] == "done" and r.get("ts"):
            esc = " ⚠ escalate" if r.get("escalate") else ""
            out.append({"ts": r["ts"], "level": "ok",
                        "text": f"{role.upper()} judgment — {r.get('verdict')} ({r.get('confidence')}){esc}"})
    for e in counted[-10:]:
        lv = "warn" if e["routing"] == "escalated" else "ok"
        out.append({"ts": e["ts"], "level": lv,
                    "text": f"MANIFEST {e['run_id']} → {e['routing']}"})
    for p in sorted(glob.glob(os.path.join(ROOT, "runs", "incomplete", "*.json")))[-5:]:
        d = read_json(p) or {}
        out.append({"ts": safe_mtime(p), "level": "warn",
                    "text": f"INCOMPLETE run logged — last: {d.get('last_role')}"})
    for doc in escalations[:5]:
        out.append({"ts": doc["ts"], "level": "warn", "text": f"ESCALATION doc: {doc['name']}"})
    out = [e for e in out if e.get("ts")]
    out.sort(key=lambda e: e["ts"])
    return out[-120:]


def build_state():
    now = time.time()
    run = build_run(now)
    stats, counted, recent = build_stats()
    escalations = build_escalations()
    empty = (stats["total_files"] == 0 and run["status"] == "idle"
             and not run["events"] and not escalations)
    return {
        "generated_at": now,
        "repo": os.path.basename(ROOT),
        "empty": empty,
        "run": run,
        "stats": stats,
        "manifests_recent": recent,
        "escalations": {"count": len(escalations), "docs": escalations[:20]},
        "events": build_events(run, counted, escalations),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "GovDash/1.0"

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(DASH_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(500, b"index.html not found", "text/plain")
        elif path == "/api/state":
            body = json.dumps(build_state(), ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def log_message(self, *args):  # 요청 로그로 콘솔을 어지럽히지 않는다
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[관제실] http://{args.host}:{args.port}  (root: {ROOT}, 읽기 전용, Ctrl-C로 종료)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
