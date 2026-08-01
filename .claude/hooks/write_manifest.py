#!/usr/bin/env python3
"""Stop 훅: 세션 종료 시 runs/current/의 판단들을 모아 manifests/에 append-only 매니페스트로 기록."""
import json, sys, os, glob, hashlib, datetime

# 판단 근거로 인용되지만 '입력 데이터'가 아닌 경로. input_hash 계산에서 제외한다.
NON_INPUT_PREFIXES = ("normative/", "knowledge/", "runs/", "escalation/", "manifests/", ".claude/")

# 완주한 파이프라인이 남겨야 하는 역할 산출물 (normative/schemas/judgment.schema.json의 agent_role)
PIPELINE_ROLES = ("analyst", "independent", "critic", "verifier", "synthesizer")

MARKER_NAME = ".manifested"


def read_marker(current):
    """이미 기록한 outputs_hash 집합. 마커가 없거나 깨졌으면 빈 집합."""
    try:
        with open(os.path.join(current, MARKER_NAME), encoding="utf-8") as f:
            return set(json.load(f).get("recorded", []))
    except Exception:
        return set()


def write_marker(current, outputs_hash, run_id):
    recorded = read_marker(current)
    recorded.add(outputs_hash)
    payload = {"recorded": sorted(recorded), "last_run_id": run_id}
    with open(os.path.join(current, MARKER_NAME), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_input_files(judgments, project_dir):
    """판단들의 evidence.source_location에서 입력 데이터 파일만 추려 (경로, 내용해시) 목록을 만든다.

    루브릭·정책·판례·판단 파일은 입력 데이터가 아니므로 제외한다. 기대 정답이 담긴
    expected.json도 제외한다 (입력이 아니며, 포함하면 정답 파일 변경이 입력 변경으로 보인다).
    """
    rels = set()
    for d in judgments:
        for ev in d.get("evidence", []):
            loc = str(ev.get("source_location", "")).replace("\\", "/").strip()
            if not loc:
                continue
            head, sep, tail = loc.rpartition(":")
            if sep and tail.isdigit():  # "경로:행번호" 형태면 행번호 제거
                loc = head
            if loc.startswith(NON_INPUT_PREFIXES) or os.path.basename(loc) == "expected.json":
                continue
            rels.add(loc)

    files = []
    for rel in sorted(rels):
        abs_path = os.path.join(project_dir, rel)
        if os.path.isfile(abs_path):
            files.append({"path": rel, "sha256": sha256_file(abs_path)})
    return files

def main():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    current = os.path.join(project_dir, "runs", "current")
    files = sorted(glob.glob(os.path.join(current, "*.judgment.json")))
    if not files:
        sys.exit(0)  # 이번 세션에 판단 실행 없음

    outputs, all_pass, judgments = {}, True, []
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                d = json.load(f)
            judgments.append(d)
            role = d.get("agent_role", os.path.basename(fp))
            outputs[role] = {"verdict": d.get("verdict"), "confidence": d.get("confidence"),
                             "escalate": d.get("escalate"), "evidence_count": len(d.get("evidence", []))}
        except Exception:
            all_pass = False

    synth_judgment = next((d for d in judgments if d.get("agent_role") == "synthesizer"), None)
    synth = outputs.get("synthesizer", {})
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")

    # outputs_hash: 판정 결과의 해시. 같은 입력이라도 판정이 다르면 달라진다.
    # (이전 버전은 이 값을 input_hash라는 이름으로 기록해, 같은 입력의 회차마다 값이
    #  달라졌다. 그 상태로는 "같은 데이터 → 같은 verdict" 재현성 대조에 쓸 수 없었다.)
    blob = json.dumps(outputs, sort_keys=True, ensure_ascii=False).encode()
    outputs_hash = hashlib.sha256(blob).hexdigest()
    run_id = f"{ts}_{outputs_hash[:8]}"

    # input_hash: 입력 데이터 파일 '내용'의 해시. 같은 입력이면 회차·판정과 무관하게 같다.
    input_files = collect_input_files(judgments, project_dir)
    if input_files:
        canon = json.dumps([[f["path"], f["sha256"]] for f in input_files], sort_keys=True).encode()
        input_hash = "sha256:" + hashlib.sha256(canon).hexdigest()
    else:
        input_hash = "unresolved:evidence에서 입력 파일을 특정하지 못함"

    # 중복 기록 차단: 이미 기록한 산출물 해시는 다시 쓰지 않는다.
    # 마커를 '존재 여부'가 아니라 '해시 일치'로 판정하는 이유 — 훅은 세션 턴이 끝날 때마다
    # 발동하므로, 파이프라인 진행 중에 다른 세션의 훅이 마커를 남기면 정작 그 실행의
    # 정식 매니페스트가 스킵될 수 있다. 해시로 비교하면 산출물이 늘어난 시점에는 반드시 기록된다.
    if outputs_hash in read_marker(current):
        print(f"[기록 생략] 동일 산출물이 이미 기록됨 (outputs_hash {outputs_hash[:8]})")
        sys.exit(0)

    # 완료 판별: synthesizer 산출물이 없으면 파이프라인 미완주다.
    # 미완주 실행은 manifests/에 넣지 않는다 — manifests/는 완주한 실행만 담는 통계 원천이다.
    if synth_judgment is None:
        # 파이프라인 순서로 정렬한다 (알파벳 순으로 두면 '어디까지 진행됐는지'가 틀리게 보인다).
        # 알 수 없는 역할명은 뒤에 붙인다.
        done = [r for r in PIPELINE_ROLES if r in outputs] + \
               sorted(r for r in outputs if r not in PIPELINE_ROLES)
        log = {
            "logged_at": ts, "reason": "synthesizer 산출물 없음 (파이프라인 미완주)",
            "outputs_hash": "sha256:" + outputs_hash,
            "input_hash": input_hash, "input_files": input_files,
            "roles_completed": done,
            "roles_missing": [r for r in PIPELINE_ROLES if r not in outputs],
            "last_role": done[-1] if done else None,
            "outputs": outputs,
        }
        inc_dir = os.path.join(project_dir, "runs", "incomplete")
        os.makedirs(inc_dir, exist_ok=True)
        inc_path = os.path.join(inc_dir, f"{ts}_{outputs_hash[:8]}.json")
        with open(inc_path, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        write_marker(current, outputs_hash, run_id)
        print(f"[미완주 로그] {inc_path} (진행: {', '.join(done) or '없음'})")
        sys.exit(0)

    routing = "escalated" if synth.get("escalate") else "auto_confirmed"
    manifest = {
        "run_id": run_id, "timestamp": ts,
        "input_hash": input_hash,
        "input_files": input_files,
        "outputs_hash": "sha256:" + outputs_hash,
        "schema_version": "judgment@1.0.0",
        "outputs": outputs,
        "verification": {"schema_pass": all_pass, "citations_pass": all_pass},
        "routing": routing,
        "escalation_reason": synth_judgment.get("escalation_reason") if routing == "escalated" else None,
    }
    out_dir = os.path.join(project_dir, "manifests")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{run_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    write_marker(current, outputs_hash, run_id)
    print(f"[매니페스트 기록] {out_path} (routing: {routing})")
    sys.exit(0)

if __name__ == "__main__":
    main()
