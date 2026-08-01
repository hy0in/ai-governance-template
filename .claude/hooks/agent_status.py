#!/usr/bin/env python3
"""PreToolUse/PostToolUse(Task|Agent) 훅: 서브에이전트 시작·종료를 runs/current/status.json에 기록.

대시보드(dashboard/serve.py)의 '진행 중' 표시 전용이다. 판단·검증 로직과 완전히
무관하며, 어떤 경우에도 파이프라인을 차단하지 않는다 (항상 exit 0).
status.json이 없어도 대시보드는 judgment 파일 감지만으로 동작한다 (이 훅은 보강).
"""
import json
import os
import sys
import time

# 파이프라인 역할 에이전트만 기록한다. 그 외 서브에이전트는 잡음이므로 무시.
KNOWN_AGENTS = {"analyst", "independent-analyst", "critic", "evidence-verifier", "synthesizer"}
MAX_EVENTS = 200


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        return
    if hook_input.get("tool_name") not in ("Task", "Agent"):
        return
    agent = (hook_input.get("tool_input") or {}).get("subagent_type", "")
    if agent not in KNOWN_AGENTS:
        return
    event = "agent_start" if hook_input.get("hook_event_name") == "PreToolUse" else "agent_end"

    root = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    current = os.path.join(root, "runs", "current")
    path = os.path.join(current, "status.json")
    try:
        os.makedirs(current, exist_ok=True)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        events = [e for e in data.get("events", []) if isinstance(e, dict)][-(MAX_EVENTS - 1):]
        events.append({"ts": time.time(), "event": event, "agent": agent})
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"events": events}, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        pass  # 상태 기록 실패가 파이프라인을 막아서는 안 된다


if __name__ == "__main__":
    main()
    sys.exit(0)
