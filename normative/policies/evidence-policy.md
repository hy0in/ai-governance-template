# 증거 정책 (v1.0)

이 정책은 모든 에이전트의 판단 산출물에 적용되는 규범이다.

## 인용 규칙

1. `evidence.quote`는 원문에서 **그대로 복사**한다. 요약·의역·재구성 금지. 훅이 원문 대조 검사를 수행하며, 원문에 없는 인용은 근거 불량으로 판정된다.
2. 모든 주장(verdict를 지지하는 논거)에는 최소 1개의 인용을 첨부한다.
3. `source_location`은 저장소 루트 기준 상대 경로로 쓴다. 행 번호가 있으면 `경로:행번호`.
4. 원문에서 직접 확인되는 사실은 `directness: direct`, 여러 사실의 조합·추론으로 도출한 주장은 `directness: inferred`로 표시한다.

## 인용 가능한 출처

- 해당 실행의 입력 데이터
- `normative/` 아래 문서 (루브릭·정책)
- `knowledge/precedents/` 중 frontmatter `status: approved`인 문서

인용 불가: `status: draft` 문서, `knowledge/hypotheses/` 전체, 에이전트 자신의 사전 지식.

## 판단 불가 시 행동

근거가 부족하거나 루브릭의 판정값 어디에도 해당하지 않으면 억지로 결론 내리지 말고 `escalate: true`와 사유를 기록한다. "사람에게 넘기는 것"도 정답이다.
