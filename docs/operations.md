# 운영 가이드

빠른 시작은 [README](../README.md)를 보라. 이 문서는 설치 세부, Obsidian 설정, 회귀·매니페스트 내부 규약, 대시보드 상세, 규칙 졸업 절차를 다룬다.

## 1. 설치 (최초 1회)

```bash
# Claude Code 설치 (미설치 시) — 최신 방법은 https://code.claude.com/docs 확인
npm install -g @anthropic-ai/claude-code

# 저장소 초기화
cd ai-governance
git init && git add -A && git commit -m "거버넌스 저장소 초기화"

# 파이썬 가상환경 생성 + 훅의 전체 스키마 검증에 필요한 jsonschema 설치
# (전역에 설치하지 않는다. .venv가 없으면 훅이 필수 필드 검사로 폴백됨)
python3 -m venv .venv
.venv/bin/pip install jsonschema
```

## 2. Obsidian 설정 (선택이지만 권장)

이 저장소는 동시에 Obsidian 볼트다. `knowledge/`의 판례·결정 로그를 그래프로 탐색하려면:

1. Obsidian에서 "Open folder as vault" → 이 저장소 루트 선택.
2. Settings → Files & Links → **"Use [[Wikilinks]]" 끄기**, "New link format"을 **Relative path**로.
3. `.obsidian/`은 이미 gitignore 처리되어 있다. 동기화는 Git으로 한다 (Obsidian Sync로 `normative/`를 편집·전파하지 말 것 — 회귀 테스트 게이트를 우회하게 된다).
4. 편집 습관: `knowledge/`는 자유롭게, `normative/`는 읽기 전용으로 취급하고 수정은 Claude Code에서 브랜치·PR로.

## 3. 재현성 확인

```bash
.venv/bin/python3 golden/run_regression.py --dry        # 케이스 목록 확인
.venv/bin/python3 golden/run_regression.py              # 전체 1회 실행
.venv/bin/python3 golden/run_regression.py --repeat 3   # 자기 일관성 측정 (같은 입력 3회)
```

Phase 1 완료 기준: `--repeat 5`에서 **기대 verdict와 5/5 일치** (하네스가 `0/5 통과`가 아니라 `5/5 통과`를 출력할 것). 회차 간 verdict가 서로 같기만 한 것은 재현성 확인일 뿐 완료 기준이 아니다 — 기대값과 다른 값으로 안정적으로 수렴하는 경우가 실제로 있었다 (판례 [case-002](../knowledge/precedents/case-002.md)).

자기 일관성 비교는 `verdict`와 `escalate` 필드로만 한다. `escalation_reason`은 자유 서술이라 회차마다 문구가 달라지므로 비교에 쓰지 않는다.

> **파이프 주의.** 하네스는 실패 시 종료 코드 1을 반환하지만, `| tee` 같은 파이프로 넘기면 파이프라인 종료 코드가 마지막 명령(`tee`)의 것이 되어 **실패가 0으로 보고된다.** 로그를 남기려면:
> ```bash
> set -o pipefail   # zsh/bash
> .venv/bin/python3 golden/run_regression.py --repeat 5 2>&1 | tee regression.log
> ```

이 회귀는 로컬에서 `claude` CLI로 실제 앙상블을 여러 차례 실행하므로 실행마다 수 분~수십 분이 걸리고 API 사용량이 발생한다. **CI에서는 돌리지 않는다** — 이 저장소의 CI(`.github/workflows/`)는 훅 문법 검사와 `--dry` 케이스 목록 확인만 한다. 실제 회귀는 항상 로컬 담당이다.

## 4. 실제 업무 온보딩 순서

1. `normative/rubrics/_TEMPLATE.md`를 복사해 실제 업무 루브릭 작성 (판정값 폐쇄 목록이 핵심).
2. 실제 데이터의 익명화 사본으로 골든 케이스 20~50건 작성 (`golden/cases/`). 명백한 케이스 70%, 경계 케이스 30%. 경계 케이스는 `"allow_escalate": true`로.
3. 회귀 하네스 통과 확인 후 현업 데이터에 적용.
4. 에스컬레이션 발생 시: `escalation/` 문서를 사람이 검토·판정 → `knowledge/precedents/_TEMPLATE.md`로 판례 기록 → 검토 후 `status: approved`로 승격 → 필요 시 골든 케이스로 환류.
5. 루브릭·스키마·에이전트 수정은 항상: **브랜치 → 수정 → `run_regression.py` 통과 → `--no-ff` 병합 → 브랜치 삭제.** `main`에 직접 커밋하지 않는다.
   - `--no-ff`로 병합하는 이유: 규범 개정·하네스·훅처럼 성격이 다른 커밋의 **경계 자체가 감사 기록**이다. squash로 뭉개면 "무엇을 어떤 근거로 바꿨는지"가 한 덩어리가 되어 추적이 끊긴다.

## 5. 관제실 대시보드

파이프라인 실행을 실시간으로 지켜보는 로컬 모니터링 화면. 표준 라이브러리만 사용하며 외부 패키지·인터넷 의존이 없고, **저장소를 읽기만 한다** (127.0.0.1 바인딩).

```bash
python3 dashboard/serve.py          # http://127.0.0.1:8765
python3 dashboard/serve.py --port 9000
```

- **신경망 뷰**: 입력 → analyst/independent(병렬) → critic → verifier → synthesizer → 확정/에스컬레이션. 완료 노드는 글로우, 실행 중 노드는 맥박, 활성 엣지에는 데이터 펄스가 흐른다. 노드를 클릭하면 verdict·confidence·근거 인용이 우측 패널에 표시된다.
- **게이지 3종**: 자동확정률·에스컬레이션율·인용 검증 통과율. `manifests/`만 집계하며, run_id 해시 접미사가 중복인 기록과 구형식 `routing: incomplete` 기록은 제외한다 (아래 "매니페스트 집계 규칙" 참조).
- **진행 중 표시**: `.claude/hooks/agent_status.py`(PreToolUse/PostToolUse, `Task|Agent` 매처)가 서브에이전트 시작·종료를 `runs/current/status.json`에 기록한다. 이 훅은 판단·검증 로직과 무관하고 항상 exit 0이다. status.json이 없어도 judgment 파일 생성 감지만으로 동작한다 (비동기 서브에이전트 환경에서는 이 폴백이 `running?`으로 추정 표시한다).
- 데이터가 0건이어도 깨지지 않고 대기 화면을 보여준다. 2초 폴링.

## 6. 규칙 졸업 (분기별)

`manifests/`를 분석해 "N회 이상 만장일치 + 동일 근거 패턴"인 판정 유형을 찾고, 사람이 승인하면 해당 유형을 코드 규칙(전처리 단계의 자동 판정)으로 이관한다. Claude Code에게 "manifests/ 전체를 분석해 규칙 졸업 후보를 추출해줘"라고 요청하면 된다.

## 기록의 단일 원천: `manifests/`

**통계·대시보드·규칙 졸업 분석이 읽는 대상은 `manifests/`뿐이다.** 다른 디렉터리를 집계에 섞지 않는다.

| 경로 | 담는 것 | 집계 대상 |
|---|---|---|
| `manifests/` | **완주한 실행만.** synthesizer 산출물이 있는 실행 | **○ (유일한 원천)** |
| `runs/incomplete/` | 미완주 실행 로그. 어느 역할까지 진행됐는지 기록 | ✗ (진단용) |
| `runs/current/` | 진행 중인 실행의 작업 공간 (gitignore) | ✗ |
| `escalation/` | 사람 판단 대기 큐 | ✗ |

매니페스트의 해시 두 종류는 역할이 다르다.

- `input_hash` — 입력 데이터 **파일 내용**의 해시. 같은 입력이면 회차·판정 결과와 무관하게 같다.
- `outputs_hash` — **판정 결과**의 해시. 같은 입력이라도 판정이 다르면 달라진다.

재현성 대조는 **`input_hash`가 같은 매니페스트끼리** 한다. 무엇을 비교하느냐는 목적에 따라 다르다.

- **결론 수준 재현성** (이 저장소의 목표): `outputs[*].verdict`와 `outputs[*].escalate`를 비교한다.
- **산출물 완전 동일성**: `outputs_hash`를 비교한다. 단 이 값은 `confidence`·`evidence_count`까지 포함하므로 **결론이 같아도 거의 항상 달라진다.** `outputs_hash`를 결론 재현성 판정에 쓰면 안 된다.

`run_regression.py --repeat N`의 자기 일관성 출력이 결론 수준 비교에 해당한다.

## 매니페스트 집계 규칙

`manifests/`는 append-only다. 수정·삭제하지 않는다. 잘못 기록된 매니페스트도 지우지 않고, `knowledge/decisions/`에 결함을 문서화하면서 해당 파일을 링크로 지목한다 — 이 템플릿의 [decisions/0002](../knowledge/decisions/0002-매니페스트-기록-결함.md)가 실제 사례다.

집계 시 다음 두 종류는 제외한다:
- run_id 해시 접미사가 앞선 기록과 동일한 매니페스트 (동일 산출물의 중복 기록)
- 구형식 `routing: "incomplete"` 매니페스트 (현재는 `runs/incomplete/`로 분리되어 `manifests/`에 섞이지 않는다)

`runs/current/`는 실행마다 초기화되는 작업 공간이다. 보존 가치가 있는 것은 매니페스트와 판례로 남긴다.

## 버전 주의사항

훅 이벤트·설정 형식과 headless 실행 플래그는 Claude Code 버전에 따라 바뀔 수 있다. 문제가 생기면 https://code.claude.com/docs 에서 최신 사양을 확인하고, Claude Code에게 "이 저장소의 훅 설정을 현재 버전 사양에 맞게 점검해줘"라고 요청하라.
