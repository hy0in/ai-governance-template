<p align="right"><b>한국어</b> | <a href="README.md">English</a></p>

# AI Governance Template

**Claude Code로 AI 판단을 검증 가능하게 만드는 저장소 템플릿.** "판단은 AI가, 검증은 코드가 한다"는 원칙으로, 분석·반론·근거검증·종합을 맡는 5개 역할 에이전트와 그 결과를 결정적으로 검사하는 훅, 그리고 실시간 관제 대시보드를 갖춘 앙상블 파이프라인을 제공한다.

![관제실 대시보드](docs/dashboard.png)

## 이 템플릿이 푸는 문제

LLM에게 "이 지출을 승인해도 될까?", "이 콘텐츠가 정책을 위반했나?" 같은 판단을 맡기기 시작하면 곧 세 가지 질문에 부딪힌다.

- **재현성** — 같은 데이터를 다시 넣으면 같은 결론이 나오는가? 아니면 그때그때 다른가?
- **근거** — verdict가 실제로 원문에 있는 내용에 근거하는가, 아니면 그럴듯한 서술인가?
- **검증** — 결론이 이상해 보일 때, 그것이 모델의 오류인지 규범(루브릭) 자체의 공백인지 구분할 수 있는가?

이 템플릿은 세 질문 모두에 **코드로 답한다.** 스키마 준수와 인용 실재성은 훅이 결정적으로 검사하고, 재현성은 골든 셋 회귀로 측정하며, 판단이 갈리는 지점은 자동으로 사람에게 에스컬레이션되어 판례로 축적된다.

## 핵심 개념

| 개념 | 위치 | 역할 |
|---|---|---|
| **루브릭** | `normative/rubrics/` | 판정값의 폐쇄 목록과 판단 기준. "무엇을 approve/reject/needs_review로 볼 것인가"를 사람이 문서로 정의한다. |
| **훅** | `.claude/hooks/` | 판단 산출물이 스키마를 지켰는지, 인용이 원문에 실제로 존재하는지를 결정적으로 검사한다. 위반 시 exit 2로 차단. |
| **골든 셋** | `golden/cases/`, `golden/run_regression.py` | 정답이 알려진 케이스 모음. 같은 입력을 반복 실행해 결론이 안정적으로 재현되는지 측정한다. |
| **판례** | `knowledge/precedents/` | 에이전트들의 결론이 갈렸을 때 사람이 내린 판정과 그 이유의 기록. `status: approved`만 이후 판단의 근거로 인용 가능. |

**규범(normative/)과 지식(knowledge/)은 분리되어 있다.** 스키마·루브릭·증거 정책은 PR과 회귀 테스트 없이 수정할 수 없는 규범 자산이고, 판례·설계 결정·가설은 사람이 자유롭게 편집하는 지식 자산이다. analyst류 에이전트는 `knowledge/`를 아예 읽지 않는다 — 판단이 과거 판례에 오염되지 않도록.

## 파이프라인

```
입력 데이터
  ├─→ analyst ─────┐
  └─→ independent ─┴─→ critic ─→ verifier ─→ synthesizer ─→ 자동 확정
                                                          └─→ 사람 에스컬레이션
```

analyst와 independent는 서로의 결과를 모른 채 같은 데이터를 독립적으로 판단한다. critic은 두 결론에서 반론 가능성을 찾고, verifier는 모든 판단의 근거 인용을 검증하며, synthesizer는 검증을 통과한 판단만 결합해 합치 여부를 판정한다 — 불일치는 오류가 아니라 사람에게 라우팅하는 신호로 취급된다. 권한은 역할별로 분리되어 있다: critic은 결론을 수정할 수 없고, synthesizer는 새 분석을 할 수 없다.

## 빠른 시작

```bash
git clone https://github.com/hy0in/ai-governance-template ai-governance
cd ai-governance
python3 -m venv .venv && .venv/bin/pip install jsonschema

claude
```

Claude Code 세션에서:

> ensemble-orchestration 스킬에 따라 앙상블 파이프라인을 실행해줘.
> 입력: golden/cases/case-000-sample/input/expense-001.md
> 루브릭: normative/rubrics/expense-review.md

analyst·independent가 격리 상태로 판정 → critic 반론 → verifier 검증 → synthesizer가 합치 판정을 내리고, `manifests/`에 실행 기록이 남는다. 다른 터미널에서 아래를 띄우면 위 스크린샷처럼 실시간으로 지켜볼 수 있다.

```bash
python3 dashboard/serve.py   # http://127.0.0.1:8765
```

## 작동 실례

이 템플릿에는 실제로 갈렸던 판단과 그 해소 과정이 예제로 남아 있다. [판례 case-001](knowledge/precedents/case-001.md)은 루브릭 문구의 모호성 때문에 같은 입력에서 결론이 갈린 사례이고, [판례 case-002](knowledge/precedents/case-002.md)는 규범 공백(루브릭 소급 적용, 판례 부재, 독립성 할인 기준) 때문에 명백한 케이스가 5회 연속 에스컬레이션된 사례다. 둘 다 사람의 판정이 규범 개정으로 이어진 전체 경로 — 매니페스트, 에스컬레이션 문서, 최종 판례 — 가 링크로 연결되어 있다.

## 실제 업무에 적용하기

1. `normative/rubrics/_TEMPLATE.md`를 복사해 실제 업무 루브릭을 작성한다.
2. 실제 데이터의 익명화 사본으로 골든 케이스를 20~50건 작성한다.
3. 회귀 하네스(`golden/run_regression.py --repeat 5`)로 재현성을 확인한다.
4. 에스컬레이션이 발생하면 사람이 판정하고 판례로 기록한 뒤, 필요하면 루브릭을 개정한다.

상세 절차·회귀 기준·대시보드 내부 동작·매니페스트 집계 규칙은 [docs/operations.md](docs/operations.md)를 보라.

## 요구 사항

- [Claude Code](https://code.claude.com/docs) CLI
- Python 3.9+ (`dashboard/serve.py`, `golden/run_regression.py`, 훅 전부 표준 라이브러리만 사용 — `jsonschema`는 훅의 전체 스키마 검증에만 필요하고 없으면 필수 필드 검사로 폴백)

## CI

`.github/workflows/`는 `normative/`·`.claude/` 변경 PR에서 훅 문법 검사와 골든 셋 `--dry` 확인만 수행한다. **실제 회귀(`run_regression.py --repeat 5`)는 CI에서 돌리지 않는다** — `claude` CLI 인증과 실행 시간이 필요하므로 항상 로컬에서 브랜치 병합 전에 사람이 실행한다.

## 라이선스

[MIT](LICENSE)
