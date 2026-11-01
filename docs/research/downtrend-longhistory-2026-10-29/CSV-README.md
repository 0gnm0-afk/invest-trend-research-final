# CSV 안내

primary-summary.csv는 81조건 × 2시장의 15년 주 결과다. 비율 필드는 0~1, 비율 차이에 100을 곱하면 %p다.
evaluate-metrics.csv의 period=all은 종목별 최초 저장 이력, reconciliation은 이전 연구의 최근 창 대조다.
classification-yearly/eras는 연도/고정5년 구간, equal-stock은 종목 동일가중이다.
matched-summary는 3/6개월 블록의 넓은 신뢰구간으로 합친 상태 비교다. scheme3이 가장 엄격하다.
path-distributions는 고정18조건의 정확한 분포, all81-path-summary는 전체81조건의 평균/접촉률이다.
coverage-stocks/input-manifest에서 자료 분모·출처를 확인할 수 있다. 그림마다 -data.csv가 있다.
KR/US-signal-definitions에는 조건과 event/daily_pattern 구분이 있다. 후속6조건은 실제 확인일에 센다.
미래 저점까지의 낙폭은 실현 수익이나 피할 수 있었던 손실이 아니다. 상세 산식과 해석은 methods.md 및 보고서를 읽어야 한다.
원자료와 코드는 보존되어 재계산 가능하다. 저장 공간 확보를 위해 검증 완료된 이번 분류 NPZ 캐시를 해제했으며 cache-release.json에 근거를 남겼다.

가격경로 추론 완료 후 필요한 여유 공간을 확보할 만큼 월별 중간 배열을 해제했다. path-cache-release.json에 파일 수와 해시를 보존했다. 정리한 파일의 정확한 신호별 원장은 ledgers, 나머지는 기존 paths에 남아 전체 종목을 계속 읽을 수 있다. 재현 순서는 연구 코드 README를 따른다.
