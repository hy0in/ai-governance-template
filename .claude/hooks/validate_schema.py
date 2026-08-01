#!/usr/bin/env python3
"""PostToolUse 훅: runs/current/*.judgment.json 파일이 judgment 스키마를 따르는지 결정적으로 검사.
위반 시 exit code 2로 차단하고 stderr로 에이전트에게 오류를 피드백한다."""
import json, sys, os, re

def fail(msg):
    print(f"[스키마 검증 실패] {msg} — normative/schemas/judgment.schema.json을 다시 확인하고 파일을 수정하라.", file=sys.stderr)
    sys.exit(2)

def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # 훅 입력이 없으면 통과 (다른 도구 호출)

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not re.search(r"runs/.*\.judgment\.json$", file_path.replace("\\", "/")):
        sys.exit(0)  # 판단 파일이 아니면 검사 대상 아님

    if not os.path.exists(file_path):
        sys.exit(0)

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"{file_path}가 유효한 JSON이 아님: {e}")

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    schema_path = os.path.join(project_dir, "normative", "schemas", "judgment.schema.json")

    # jsonschema 라이브러리가 있으면 전체 검증, 없으면 필수 필드 검사로 폴백
    try:
        import jsonschema
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            fail(f"{file_path}: {e.message} (경로: {'/'.join(map(str, e.absolute_path))})")
    except ImportError:
        required = ["agent_role", "verdict", "confidence", "evidence", "escalate"]
        missing = [k for k in required if k not in data]
        if missing:
            fail(f"{file_path}: 필수 필드 누락 {missing}")
        if not isinstance(data.get("evidence"), list) or len(data["evidence"]) == 0:
            fail(f"{file_path}: evidence는 최소 1개 항목의 배열이어야 함")
        for i, ev in enumerate(data["evidence"]):
            for k in ["quote", "source_location", "directness"]:
                if k not in ev:
                    fail(f"{file_path}: evidence[{i}]에 {k} 누락")

    print(f"[스키마 검증 통과] {file_path}")
    sys.exit(0)

if __name__ == "__main__":
    main()
