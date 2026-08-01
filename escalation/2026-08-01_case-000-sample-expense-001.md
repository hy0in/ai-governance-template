# 에스컬레이션: case-000-sample / 경비 신청서 EXP-001

- 생성일: 2026-08-01
- 생성자: synthesizer
- 상태: 사람 판단 대기
- 사유: 기각 불가한 대안 가설 존재 + 독립성 할인으로 유효 표 부족

## 판단 대조표

| 역할 | verdict | confidence | 근거 유형 | verifier 판정 | 투표권 |
|---|---|---|---|---|---|
| analyst | approve | high | direct 7건 | valid | 있음 (독립성 할인 적용) |
| independent | approve | high | direct 7건 | valid | 있음 (독립성 할인 적용) |
| critic | objection_raised | medium | direct 4건 | valid | 있음 |
| verifier | verification_complete | high | direct 6건 | — | (검증 역할, 투표 없음) |

**독립성 할인:** analyst와 independent는 완전히 동일한 7개 source_location 집합에만 의존한다 (verifier 확인: "analyst와 동일한 7개 인용 집합(순서만 상이)"). 결합 규칙에 따라 approve는 2표가 아닌 **1표**로 합산된다.

## 반론 요약 (critic)

### 가설 1 — 영수증 미확인 가설 (기각 불가, 에스컬레이션의 직접 원인)

루브릭은 "영수증 항목에 날짜·금액·용도가 모두 기재되어 있어야 한다"를 요구하지만, 입력 문서 제목은 "# 경비 신청서 EXP-001"로 영수증이 아닌 신청서이며, 원문 어디에도 영수증이라는 단어나 영수증 첨부 사실이 나타나지 않는다. analyst·independent 모두 신청서 기재를 영수증 기재와 동일시했으나 이 등치는 원문에 근거가 없는 추론이다.

critic이 제시한 기각 조건:
> "이 가설을 기각하려면 (a) 영수증 원본이 첨부되어 있고 그 안에 날짜·금액·용도가 기재되어 있다는 증거, 또는 (b) '경비 신청서 기재가 영수증 기재를 갈음한다'고 명시한 normative/ 문서가 필요하다."

현재 네 판단의 evidence 어디에도 (a) 또는 (b)에 해당하는 근거가 없다. 따라서 이 가설은 **기존 근거로 기각할 수 없다** → 합치 조건 불충족.

### 가설 2 — 인당 한도 해석 가설 (기존 근거로 기각 가능)

비고에 "참석 3인"이 있으나 현행 루브릭은 "건당 한도: 식비 50,000원"만 규정하므로 48,000원은 충족. critic 스스로 "이 가설만으로는 approve를 뒤집을 수 없고, 루브릭 개정 검토 신호로만 남긴다"고 명시. 판정에 영향 없음. 루브릭 개정 검토 신호로만 기록.

### 부수 관찰 — rubric_version 표기 불일치

analyst는 "v0.1", independent는 "expense-review v0.1"로 표기 상이. verifier 확인 결과 투표권에는 영향 없음. 재현성 대조를 위한 표기 정규화 필요.

## 근거 파일 링크

- 판단 산출물
  - [analyst.judgment.json](../runs/current/analyst.judgment.json)
  - [independent.judgment.json](../runs/current/independent.judgment.json)
  - [critic.judgment.json](../runs/current/critic.judgment.json)
  - [verifier.judgment.json](../runs/current/verifier.judgment.json)
  - [synthesizer.judgment.json](../runs/current/synthesizer.judgment.json)
- 원본 입력 및 규범 (판단들이 인용한 경로, synthesizer는 직접 읽지 않음)
  - [expense-001.md](../golden/cases/case-000-sample/input/expense-001.md)
  - [expense-review.md](../normative/rubrics/expense-review.md)

## 사람이 확인해야 할 질문

1. EXP-001 건에 실제 영수증이 첨부되어 있는가? 첨부되어 있다면 영수증에 날짜·금액·용도가 기재되어 있는가?
2. 조직 정책상 경비 신청서의 기재가 영수증 기재를 갈음할 수 있는가? 그렇다면 이를 normative/ (증거 정책 또는 루브릭)에 명문화할 것인가?
3. 루브릭의 "영수증 항목에" 문구가 실제 의도인가, 아니면 "신청 서류에"의 의미인가? 문구 개정이 필요한가? (개정 시 golden/run_regression.py 통과 필요)
4. 식비 한도를 건당 기준으로 유지할 것인가, 인당 기준 도입을 검토할 것인가? (critic 가설 2 — 현 판정에는 영향 없음)
5. rubric_version 표기 형식을 하나로 정규화할 것인가? (예: "expense-review v0.1")
