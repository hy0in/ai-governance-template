#!/usr/bin/env python3
"""골든 셋 회귀 하네스.
각 골든 케이스에 대해 Claude Code를 headless로 실행해 앙상블 파이프라인을 돌리고
synthesizer의 verdict를 expected와 대조한다.

사용법:
  python3 golden/run_regression.py            # 전체 케이스 1회씩
  python3 golden/run_regression.py --repeat 3 # 자기 일관성 측정 (케이스당 3회)
  python3 golden/run_regression.py --dry      # claude 호출 없이 케이스 목록만 확인

주의: claude CLI가 설치되어 있고 이 저장소 루트에서 실행해야 한다.
headless 실행 플래그의 최신 사양은 공식 문서에서 확인: https://code.claude.com/docs

종료 코드: 전체 통과 0, 1건이라도 실패 1.
파이프(`| tee` 등)로 출력을 넘기면 파이프라인 종료 코드가 마지막 명령의 것이 되어
실패가 0으로 보고된다. CI에서는 `set -o pipefail`을 켜거나 파이프 없이 실행할 것.
"""
import json, os, sys, glob, subprocess, shutil, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_case(case_dir, dry=False):
    with open(os.path.join(case_dir, "expected.json"), encoding="utf-8") as f:
        exp = json.load(f)
    if dry:
        return {"case": exp["case_id"], "status": "dry", "expected": exp["expected_verdict"]}

    current = os.path.join(ROOT, "runs", "current")
    shutil.rmtree(current, ignore_errors=True)
    os.makedirs(current, exist_ok=True)

    prompt = (
        f"ensemble-orchestration 스킬의 절차에 따라 앙상블 파이프라인을 실행하라. "
        f"입력 데이터: {exp['input']} / 루브릭: {exp['rubric']} / "
        f"사용자 확인 단계는 생략하고 즉시 실행한다."
    )
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--permission-mode", "acceptEdits"],
            cwd=ROOT, capture_output=True, text=True, timeout=1200,
        )
    except FileNotFoundError:
        return {"case": exp["case_id"], "status": "error", "detail": "claude CLI를 찾을 수 없음"}
    except subprocess.TimeoutExpired:
        return {"case": exp["case_id"], "status": "error", "detail": "실행 시간 초과"}

    synth_path = os.path.join(current, "synthesizer.judgment.json")
    if not os.path.exists(synth_path):
        tail = ((proc.stderr or "").strip() or (proc.stdout or "").strip()).splitlines()
        hint = f" — claude 출력: {tail[-1][:160]}" if tail else ""
        return {"case": exp["case_id"], "status": "fail",
                "detail": "synthesizer 산출물 없음 (파이프라인 미완주)" + hint}
    with open(synth_path, encoding="utf-8") as f:
        synth = json.load(f)

    # 일치 비교는 verdict·escalate 필드로만 한다.
    # escalation_reason은 자유 서술이라 회차마다 문구가 달라지므로 비교 대상에서 제외한다
    # (이전 버전은 got에 사유 문구를 넣어 비교해 에스컬레이션이 항상 '불일치'로 집계됐다).
    res = {"case": exp["case_id"], "expected": exp["expected_verdict"],
           "got": synth.get("verdict"), "escalate": bool(synth.get("escalate", False))}
    if res["escalate"] and not exp.get("allow_escalate", False):
        reason = (synth.get("escalation_reason") or "").replace("\n", " ")
        res["status"] = "fail"
        res["detail"] = "에스컬레이션 불허 케이스 · 사유: " + (reason[:300] or "(사유 미기재)")
        return res
    ok = res["got"] == exp["expected_verdict"] or (res["escalate"] and exp.get("allow_escalate"))
    res["status"] = "pass" if ok else "fail"
    return res

def consistency_key(res):
    """자기 일관성 비교 키. 자유 서술 필드는 포함하지 않는다."""
    if "got" not in res:
        return None  # error/dry 등 판정에 도달하지 못한 회차
    return (res["got"], res["escalate"])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    cases = sorted(glob.glob(os.path.join(ROOT, "golden", "cases", "case-*")))
    if not cases:
        print("골든 케이스가 없습니다. golden/cases/에 케이스를 추가하세요.")
        sys.exit(1)

    results = []
    for case_dir in cases:
        keys = []
        for r in range(args.repeat):
            res = run_case(case_dir, dry=args.dry)
            results.append(res)
            keys.append(consistency_key(res))
            observed = (f" (기대 {res.get('expected')} / 실제 {res.get('got')}"
                        f", escalate={res.get('escalate')})") if "got" in res else ""
            print(f"  {res['case']} [{r+1}/{args.repeat}] → {res['status']}" + observed
                  + (f" · {res.get('detail')}" if res.get('detail') else ""))
        if args.repeat > 1 and not args.dry:
            measured = [k for k in keys if k is not None]
            uniq = sorted({f"{v}/escalate={e}" for v, e in measured})
            if not measured:
                verdict_line = "측정 불가 (판정에 도달한 회차 없음)"
            elif len(uniq) == 1:
                verdict_line = f"일치 — {uniq[0]} ({len(measured)}/{args.repeat}회 측정)"
            else:
                verdict_line = f"불일치 — {uniq} ({len(measured)}/{args.repeat}회 측정)"
            print(f"  └ 자기 일관성: {verdict_line}")

    if not args.dry:
        n_pass = sum(1 for r in results if r["status"] == "pass")
        print(f"\n결과: {n_pass}/{len(results)} 통과")
        sys.exit(0 if n_pass == len(results) else 1)

if __name__ == "__main__":
    main()
