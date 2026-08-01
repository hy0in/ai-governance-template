---
status: approved
case_id: case-001
date: 2026-08-01
rubric: ../../normative/rubrics/expense-review.md
verdict_human: approve
verdict_ai_majority: approve
---
# 판례: 경비 신청서 기재는 영수증 기재 요건을 갈음한다

## 상황

골든 케이스 case-000-sample의 입력 [expense-001.md](../../golden/cases/case-000-sample/input/expense-001.md)는 제목이 "경비 신청서"인 문서로, 날짜·금액·용도가 모두 기재되어 있으나 영수증 첨부 여부는 원문에 나타나지 않는다. 루브릭 v0.1의 기재 요건 문구가 "**영수증** 항목에 날짜·금액·용도가 모두 기재"였기 때문에, 신청서 기재를 영수증 기재와 동일시할 수 있는지가 실행마다 갈리는 반론 지점이 되었다.

- 1차 실행: critic이 이 간극을 반론(영수증 미확인 가설)으로 세웠고, 기존 근거로 기각 불가하여 synthesizer가 에스컬레이션. 원본 위치 링크: [매니페스트](../../manifests/2026-08-01T014248Z_60d0ab74.json), [에스컬레이션 문서](../../escalation/2026-08-01_case-000-sample-expense-001.md)
- 2차 실행(같은 입력·같은 규범): critic이 같은 간극을 대안 가설로만 기록하고 no_valid_objection 판정, synthesizer가 approve 자동 확정. [매니페스트](../../manifests/2026-08-01T015133Z_5df3560c.json)

같은 데이터에서 결론이 갈린 것은 루브릭 문구의 모호성이 원인이며, 이 판례는 그 모호성에 대한 사람 판정을 기록한다.

## AI 판단 대조

1차 실행(에스컬레이션된 실행) 기준:

| 에이전트 | verdict | confidence | 핵심 근거 |
|---|---|---|---|
| analyst | approve | high | 금액 48,000원 ≤ 식비 한도 50,000원, 날짜·금액·용도 모두 기재, 용도 "고객 미팅"은 허용 목록 포함 (direct 7건) |
| independent | approve | high | analyst와 동일한 7개 인용 집합으로 동일 결론 (독립성 할인로 approve 합산 1표) |
| critic | objection_raised | medium | 입력은 "경비 신청서"인데 루브릭은 "영수증 항목에" 기재를 요구 — 신청서 기재 = 영수증 기재라는 등치는 원문 무근거 추론 (direct 4건) |

## 사람의 판정과 이유

**판정: approve.** 경비 신청서에 날짜·금액·용도가 기재되어 있으면 영수증 기재 요건을 갈음하는 것으로 결정한다 (판정일 2026-08-01, 판정자: 저장소 소유자).

이유: 루브릭 v0.1의 "영수증 항목에" 문구는 "제출 서류에"의 의미로 작성된 것이며, 별도의 영수증 원본 대조를 요구하려던 의도가 아니다. critic이 요구한 기각 조건 (b) — "경비 신청서 기재가 영수증 기재를 갈음한다고 명시한 normative/ 문서" — 를 이 판정으로 충족시키고, 루브릭 v0.2에서 문구를 "제출 문서(경비 신청서 또는 영수증)"로 명문화한다.

## 후속 조치

- [x] 골든 케이스로 추가 (golden/cases/) — 이미 case-000-sample로 존재
- [x] 루브릭 개정 필요 여부: 필요 — [expense-review.md](../../normative/rubrics/expense-review.md) v0.2에서 기재 요건 문구 개정
- [ ] 관련 판례: 없음 (최초 판례)
