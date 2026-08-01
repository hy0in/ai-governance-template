#!/usr/bin/env python3
"""PostToolUse 훅: 판단 파일의 모든 evidence.quote가 source_location이 가리키는 원문에
실제로 존재하는지 문자열 대조 검사. 환각 인용을 구조적으로 차단하는 장치.
불량 시 exit code 2로 차단하고 수정을 요구한다."""
import json, sys, os, re

def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not re.search(r"runs/.*\.judgment\.json$", file_path.replace("\\", "/")):
        sys.exit(0)
    if not os.path.exists(file_path):
        sys.exit(0)

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        sys.exit(0)  # JSON 오류는 validate_schema가 잡는다

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    failures = []

    for i, ev in enumerate(data.get("evidence", [])):
        quote = ev.get("quote", "")
        loc = ev.get("source_location", "")
        src = loc.rsplit(":", 1)[0] if re.search(r":\d+$", loc) else loc
        src_path = src if os.path.isabs(src) else os.path.join(project_dir, src)

        # 검증/종합 역할의 판단 파일 인용은 파일 존재만 확인
        if data.get("agent_role") in ("verifier", "synthesizer") and src.endswith(".judgment.json"):
            if not os.path.exists(src_path):
                failures.append(f"evidence[{i}]: 참조 파일 없음 → {src}")
            continue

        if not os.path.exists(src_path):
            failures.append(f"evidence[{i}]: source_location 파일 없음 → {src}")
            continue
        # 인용 자격 검사: draft 문서·hypotheses 인용 금지
        norm_src = src.replace("\\", "/")
        if "knowledge/hypotheses/" in norm_src:
            failures.append(f"evidence[{i}]: hypotheses/ 문서는 인용 불가")
            continue
        try:
            with open(src_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            failures.append(f"evidence[{i}]: 원문 읽기 실패 ({e})")
            continue
        if "knowledge/precedents/" in norm_src and "status: approved" not in content:
            failures.append(f"evidence[{i}]: approved 아닌 판례 인용 → {src}")
            continue
        # 공백 정규화 후 부분 문자열 대조
        norm = lambda s: re.sub(r"\s+", " ", s).strip()
        if norm(quote) not in norm(content):
            failures.append(f"evidence[{i}]: 인용문이 원문({src})에 존재하지 않음 → \"{quote[:60]}...\"")

    if failures:
        print("[인용 검증 실패 — 근거 불량] 아래 인용을 원문에서 그대로 다시 복사하거나 해당 주장을 제거하라:", file=sys.stderr)
        for msg in failures:
            print("  - " + msg, file=sys.stderr)
        sys.exit(2)

    print(f"[인용 검증 통과] {file_path}: evidence {len(data.get('evidence', []))}건 원문 대조 완료")
    sys.exit(0)

if __name__ == "__main__":
    main()
