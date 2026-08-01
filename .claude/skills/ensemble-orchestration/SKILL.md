---
name: ensemble-orchestration
description: 앙상블 검증 파이프라인 실행 절차. 사용자가 데이터 분석·판정·검증을 요청하거나 "파이프라인 실행", "앙상블 분석"을 언급하면 이 절차를 따른다.
---
# 앙상블 오케스트레이션 절차

이 절차는 순서와 격리 규칙이 핵심이다. 순서를 바꾸거나 단계를 건너뛰지 않는다.

## 사전 준비
1. runs/current/를 비운다 (이전 실행 잔여물 제거).
2. 사용자에게 (a) 입력 데이터 경로, (b) 적용할 루브릭(normative/rubrics/)을 확인한다.

## 실행 순서
3. **analyst** 서브에이전트 실행: 입력 경로와 루브릭을 전달. → runs/current/analyst.judgment.json
4. **independent-analyst** 서브에이전트 실행: 같은 입력·루브릭 전달. **analyst의 결과를 언급하거나 전달하지 않는다.** 프롬프트에 "다른 분석이 존재한다"는 힌트도 넣지 않는다. → runs/current/independent.judgment.json
   (3과 4는 병렬 실행 가능. 격리가 목적이므로 순차 실행해도 서로의 산출물을 전달하지만 않으면 된다.)
5. **critic** 서브에이전트 실행: 두 판단 파일 경로를 전달. → runs/current/critic.judgment.json
6. **evidence-verifier** 서브에이전트 실행. → runs/current/verifier.judgment.json
7. **synthesizer** 서브에이전트 실행. → runs/current/synthesizer.judgment.json + (에스컬레이션 시) escalation/ 문서

## 사후 처리
8. synthesizer 결과를 사용자에게 보고한다: 최종 verdict 또는 에스컬레이션 사유, 에이전트별 판정 대조표, 근거 요약.
9. 훅이 각 단계에서 스키마·인용을 자동 검증하고 세션 종료 시 매니페스트를 기록한다. 훅이 차단(exit 2)하면 해당 에이전트가 지적 사항을 반영해 파일을 수정하게 한다.

## 금지사항
- 메인 세션이 직접 판단을 작성하는 것 (판단은 반드시 역할 에이전트를 통해).
- 훅 검증을 우회하기 위해 runs/ 밖에 판단 파일을 쓰는 것.
- 에이전트 간 격리 규칙 위반 (특히 4단계).
