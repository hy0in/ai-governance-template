# AI 거버넌스 저장소

이 저장소는 인간-AI 협업 검증 체계의 단일 진실 원천이다. 이 저장소는 동시에 Obsidian 볼트다.

## 핵심 원칙

1. 판단은 AI가, 검증은 코드가 한다. 스키마 준수·인용 실재성·계산은 훅이 결정적으로 검사한다.
2. 결론 수준 재현성을 목표로 한다: 같은 데이터 → 같은 verdict.
3. 권한 분리: critic은 결론을 수정하지 못하고, synthesizer는 새 분석을 하지 못한다.
4. 불일치는 오류가 아니라 사람에게 라우팅하는 신호다.
5. 프롬프트 = 코드. normative/ 아래 파일 변경은 반드시 golden/run_regression.py 통과 후 커밋한다.

## 규범과 지식의 구분 (중요)

- `normative/` — **규범 자산.** 스키마, 루브릭, 증거 정책. 에이전트가 판단 시 따라야 하는 유일한 기준. PR + 회귀 테스트 없이 수정 금지.
- `knowledge/` — **지식 자산.** 판례(precedents), 설계 결정(decisions), 가설(hypotheses). 사람이 Obsidian에서 자유롭게 편집한다. **위키 페이지는 참고 맥락이지 규범이 아니다.**

에이전트 읽기 범위 규칙:
- analyst, independent-analyst: 입력 데이터 + `normative/`만 읽는다. `knowledge/`를 읽지 않는다.
- critic, synthesizer: `knowledge/precedents/` 중 frontmatter `status: approved`인 문서만 참고할 수 있다.
- `status: draft` 문서를 판단 근거로 인용하는 것은 근거 불량이다.

## 링크 규칙 (Obsidian 호환)

- 위키링크 `[[...]]` 금지. 항상 상대 경로 마크다운 링크를 쓴다: `[case-012](../precedents/case-012.md)`
- Obsidian 설정에서 "Use [[Wikilinks]]"를 꺼야 한다 (README 참조).
- 그래프 뷰·Dataview 전용 정보에 의존하지 않는다. 색인이 필요하면 스크립트로 index.md를 생성한다.

## 실행 규약

- 앙상블 실행 절차는 `.claude/skills/ensemble-orchestration/SKILL.md`를 따른다.
- 모든 판단 산출물은 `runs/current/<역할>.judgment.json`에 기록한다. 훅이 자동 검증한다.
- 판정 출력 형식은 `normative/schemas/judgment.schema.json`을 따른다. 스키마 위반 출력은 훅이 차단한다.
- 인용(evidence.quote)은 원문에서 그대로 복사한다. 의역하면 인용 실재성 검사에서 탈락한다.

## 디렉토리 안내

```
normative/schemas/    판정·매니페스트 JSON 스키마
normative/rubrics/    업무별 판단 루브릭 (판정값 폐쇄 목록)
normative/policies/   증거 정책
knowledge/precedents/ 사람 판정 기록 (판례)
knowledge/decisions/  설계 결정 로그
knowledge/hypotheses/ 탐색 트랙 가설 (미검증)
golden/               골든 케이스 + 회귀 하네스
runs/current/         진행 중인 실행의 판단 산출물
manifests/            실행 기록 (append-only, 수정 금지)
escalation/           사람 판단 대기 큐
```
